from typing import Dict, Any, Optional, Tuple, List
from src.database import (
    get_employee,
    check_can_view_leave,
    get_leave_balance as db_get_balance,
    list_leave_requests as db_list_requests,
    get_team_leave_requests as db_get_team_leave,
    get_overlapping_requests,
    apply_leave_tx,
    cancel_leave_tx,
)
from src.tools.working_days import get_working_days
from src.config import settings

REFUSAL_MESSAGE = "I can't share information about that employee."

def mask_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"{local}***@{domain}"
    return f"{local[0]}***@{domain}"

class ToolExecutionResult:
    def __init__(self, name: str, args: Dict[str, Any], status: str, result: Any, error_msg: Optional[str] = None):
        self.name = name
        self.args = args
        self.status = status  # 'success' | 'error' | 'pending_confirmation'
        self.result = result
        self.error_msg = error_msg

    def to_api_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "args": self.args,
            "status": self.status
        }

def execute_get_leave_balance(
    requester_id: str,
    employee_id: Optional[str] = None,
    leave_type: Optional[str] = None
) -> ToolExecutionResult:
    target_id = employee_id if employee_id else requester_id
    args = {"employee_id": target_id}
    if leave_type:
        args["leave_type"] = leave_type
        
    if not check_can_view_leave(requester_id, target_id):
        return ToolExecutionResult("get_leave_balance", args, "error", None, REFUSAL_MESSAGE)
    
    target_emp = get_employee(target_id)
    if not target_emp:
        return ToolExecutionResult("get_leave_balance", args, "error", None, REFUSAL_MESSAGE)
        
    balances = db_get_balance(target_id, leave_type)
    return ToolExecutionResult("get_leave_balance", args, "success", balances)

def execute_list_leave_requests(
    requester_id: str,
    employee_id: Optional[str] = None,
    status: Optional[str] = None
) -> ToolExecutionResult:
    target_id = employee_id if employee_id else requester_id
    args = {"employee_id": target_id}
    if status:
        args["status"] = status
        
    if not check_can_view_leave(requester_id, target_id):
        return ToolExecutionResult("list_leave_requests", args, "error", None, REFUSAL_MESSAGE)
        
    target_emp = get_employee(target_id)
    if not target_emp:
        return ToolExecutionResult("list_leave_requests", args, "error", None, REFUSAL_MESSAGE)
        
    requests = db_list_requests(target_id, status)
    return ToolExecutionResult("list_leave_requests", args, "success", requests)

def execute_get_team_leave(
    requester_id: str,
    start_date: str,
    end_date: str
) -> ToolExecutionResult:
    args = {"start_date": start_date, "end_date": end_date}
    requester = get_employee(requester_id)
    if not requester or requester["role"] != "manager":
        return ToolExecutionResult(
            "get_team_leave",
            args,
            "error",
            None,
            "Only managers can view team leave."
        )
        
    team_leave = db_get_team_leave(requester_id, start_date, end_date)
    return ToolExecutionResult("get_team_leave", args, "success", team_leave)

def validate_apply_leave(
    requester_id: str,
    leave_type: str,
    start_date: str,
    end_date: str
) -> Tuple[bool, str, int]:
    """
    Validates leave rules according to Section 6.2.
    Returns (is_valid, reason/error_msg, working_days_count).
    """
    requester = get_employee(requester_id)
    if not requester:
        return False, "Requester not found.", 0
        
    leave_type = leave_type.lower()
    if leave_type not in ("annual", "sick"):
        return False, "Leave type must be 'annual' or 'sick'.", 0
        
    today = settings.get_today()
    
    # Dates must be in 2026
    if not (start_date.startswith("2026-") and end_date.startswith("2026-")):
        return False, "Leave dates must be in the 2026 calendar year.", 0
        
    if start_date < today:
        return False, f"Start date ({start_date}) must be on or after today ({today}).", 0
        
    if end_date < start_date:
        return False, f"End date ({end_date}) must be on or after start date ({start_date}).", 0
        
    # Calculate working days
    region = requester["region"]
    working_days, _ = get_working_days(start_date, end_date, region)
    
    if working_days == 0:
        return False, "The requested leave period contains zero working days (weekends or public holidays).", 0
        
    # Check overlapping requests first
    overlaps = get_overlapping_requests(requester_id, start_date, end_date)
    if overlaps:
        return False, "The requested dates overlap with an existing pending or approved leave request.", 0

    # Check balance
    balances = db_get_balance(requester_id, leave_type)
    if not balances:
        return False, f"No balance record found for leave type '{leave_type}'.", 0
    balance_days = balances[0]["balance_days"]
    
    if working_days > balance_days:
        return False, f"Requested working days ({working_days}) exceed your current balance of {balance_days} {leave_type} day(s).", 0
        
    return True, "", working_days

def commit_apply_leave(
    requester_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    working_days: int
) -> ToolExecutionResult:
    args = {
        "leave_type": leave_type,
        "start_date": start_date,
        "end_date": end_date
    }
    success, msg, req_id = apply_leave_tx(requester_id, leave_type, start_date, end_date, working_days)
    if success:
        return ToolExecutionResult("apply_leave", args, "success", {"request_id": req_id, "message": msg, "working_days": working_days})
    else:
        return ToolExecutionResult("apply_leave", args, "error", None, msg)

def validate_cancel_leave(
    requester_id: str,
    request_id: str
) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
    """
    Validates cancel leave rules according to Section 6.3.
    Returns (is_valid, error_msg, request_dict).
    """
    reqs = db_list_requests(requester_id)
    target_req = next((r for r in reqs if r["request_id"] == request_id), None)
    if not target_req:
        return False, f"Leave request '{request_id}' not found among your requests.", None
        
    if target_req["status"] not in ("pending", "approved"):
        return False, f"Cannot cancel a request with status '{target_req['status']}'.", None
        
    today = settings.get_today()
    if target_req["start_date"] <= today:
        return False, "Only pending or approved requests whose start date is after today can be cancelled.", None
        
    return True, "", target_req

def commit_cancel_leave(
    requester_id: str,
    request_id: str
) -> ToolExecutionResult:
    args = {"request_id": request_id}
    today = settings.get_today()
    success, msg = cancel_leave_tx(requester_id, request_id, today)
    if success:
        return ToolExecutionResult("cancel_leave", args, "success", {"message": msg})
    else:
        return ToolExecutionResult("cancel_leave", args, "error", None, msg)
