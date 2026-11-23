import re
from datetime import date, timedelta
from typing import Dict, Any, Optional, List, Tuple
from src.database import get_employee
from src.config import settings
from src.tools.leave_tools import (
    execute_get_leave_balance,
    execute_list_leave_requests,
    execute_get_team_leave,
    validate_apply_leave,
    commit_apply_leave,
    validate_cancel_leave,
    commit_cancel_leave,
    ToolExecutionResult,
    REFUSAL_MESSAGE
)
from src.tools.working_days import get_working_days
from src.ingestion.vector_store import doc_store
from src.orchestration.session_state import session_store
from src.orchestration.pii_sanitizer import (
    check_prompt_injection,
    sanitize_text,
    sanitize_args
)
from src.llm.client import generate_answer

CONFIRMATION_PHRASES = {"yes", "confirm", "go ahead", "sure", "please proceed", "yep", "ok", "okay"}

def parse_iso_dates(text: str) -> List[str]:
    return re.findall(r"\b2026-\d{2}-\d{2}\b", text)

def resolve_relative_dates(message: str, today_str: str) -> Tuple[Optional[str], Optional[str]]:
    today = date.fromisoformat(today_str)
    msg = message.lower()
    
    # Check for "next week"
    if "next week" in msg:
        # Weeks start on Monday. "Next week" means Mon-Fri of following week.
        days_ahead = 7 - today.weekday() # Next Monday
        start_dt = today + timedelta(days=days_ahead)
        end_dt = start_dt + timedelta(days=4) # Friday
        return start_dt.isoformat(), end_dt.isoformat()
        
    # Check for "next friday"
    if "next friday" in msg:
        # First Friday after today
        days_ahead = (4 - today.weekday()) % 7
        if days_ahead <= 0:
            days_ahead += 7
        target = today + timedelta(days=days_ahead)
        return target.isoformat(), target.isoformat()
        
    iso_dates = parse_iso_dates(message)
    if len(iso_dates) >= 2:
        return iso_dates[0], iso_dates[1]
    elif len(iso_dates) == 1:
        return iso_dates[0], iso_dates[0]
        
    return None, None

def handle_chat_message(session_id: str, employee_id: str, message: str) -> Dict[str, Any]:
    requester = get_employee(employee_id)
    if not requester:
        return {
            "answer": "Employee not found.",
            "route": "refuse",
            "citations": [],
            "tool_calls": [],
            "pending_confirmation": False
        }
        
    session = session_store.get_or_create(session_id, employee_id)
    today = settings.get_today()
    msg_clean = message.strip()
    msg_lower = msg_clean.lower()
    
    # 1. Check prompt injection
    if check_prompt_injection(msg_clean):
        return {
            "answer": "I cannot fulfill this request. I can only assist with Veltrix HR policies and leave management.",
            "route": "refuse",
            "citations": [],
            "tool_calls": [],
            "pending_confirmation": False
        }
        
    # 2. Check bulk data requests
    if re.search(r"\b(everyone'?s?|all employees'?)\s+(balances?|leave|salaries|data)\b", msg_lower):
        return {
            "answer": "I cannot provide bulk data for all employees.",
            "route": "refuse",
            "citations": [],
            "tool_calls": [],
            "pending_confirmation": False
        }
        
    # 3. Check for pending 2-step write confirmations
    if session and session.pending_proposal:
        proposal = session.pending_proposal
        # Check if user confirmed
        if msg_lower.rstrip(".!") in CONFIRMATION_PHRASES:
            # Clear pending proposal
            session_store.clear_pending_proposal(session_id)
            if proposal["type"] == "apply_leave":
                res = commit_apply_leave(
                    employee_id,
                    proposal["leave_type"],
                    proposal["start_date"],
                    proposal["end_date"],
                    proposal["working_days"]
                )
                status_text = "confirmed and submitted" if res.status == "success" else "could not be processed"
                ans = f"Your {proposal['leave_type']} leave request from {proposal['start_date']} to {proposal['end_date']} has been {status_text}."
                if res.error_msg:
                    ans += f" Reason: {res.error_msg}"
                return {
                    "answer": sanitize_text(ans),
                    "route": "tool",
                    "citations": [],
                    "tool_calls": [res.to_api_dict()],
                    "pending_confirmation": False
                }
            elif proposal["type"] == "cancel_leave":
                res = commit_cancel_leave(employee_id, proposal["request_id"])
                ans = res.result.get("message") if res.status == "success" else res.error_msg
                return {
                    "answer": sanitize_text(ans),
                    "route": "tool",
                    "citations": [],
                    "tool_calls": [res.to_api_dict()],
                    "pending_confirmation": False
                }
        else:
            # Discard proposal and continue normal flow
            session_store.clear_pending_proposal(session_id)

    # 4. Check Leave Application intent
    is_apply_intent = (
        ("leave" in msg_lower or "vacation" in msg_lower or "time off" in msg_lower) and
        any(k in msg_lower for k in ["apply", "request", "book", "take", "submitting", "submit"]) and
        not any(k in msg_lower for k in ["how to", "wiki", "policy", "faq", "rules", "guide", "allowed"])
    )
    if is_apply_intent:
        # Identify leave type
        leave_type = None
        if "sick" in msg_lower:
            leave_type = "sick"
        elif "annual" in msg_lower or "vacation" in msg_lower:
            leave_type = "annual"
            
        start_date, end_date = resolve_relative_dates(message, today)
        
        if not leave_type and not start_date:
            return {
                "answer": "Could you please specify whether you want annual or sick leave, along with the start and end dates?",
                "route": "clarify",
                "citations": [],
                "tool_calls": [],
                "pending_confirmation": False
            }
        elif not leave_type:
            return {
                "answer": "Would you like to apply for annual leave or sick leave?",
                "route": "clarify",
                "citations": [],
                "tool_calls": [],
                "pending_confirmation": False
            }
        elif not start_date or not end_date:
            return {
                "answer": "Please provide the start and end dates for your leave in 2026.",
                "route": "clarify",
                "citations": [],
                "tool_calls": [],
                "pending_confirmation": False
            }
            
        # Validate leave rules
        is_valid, error_msg, working_days = validate_apply_leave(employee_id, leave_type, start_date, end_date)
        if not is_valid:
            # Reject immediately
            err_call = {
                "name": "apply_leave",
                "args": {"leave_type": leave_type, "start_date": start_date, "end_date": end_date},
                "status": "error"
            }
            return {
                "answer": f"Unable to propose leave request: {error_msg}",
                "route": "tool",
                "citations": [],
                "tool_calls": [err_call],
                "pending_confirmation": False
            }
            
        # Propose action (pending_confirmation: true)
        proposal_dict = {
            "type": "apply_leave",
            "leave_type": leave_type,
            "start_date": start_date,
            "end_date": end_date,
            "working_days": working_days
        }
        session_store.set_pending_proposal(session_id, proposal_dict)
        
        prop_call = {
            "name": "apply_leave",
            "args": {"leave_type": leave_type, "start_date": start_date, "end_date": end_date},
            "status": "pending_confirmation"
        }
        ans = (
            f"You are requesting {working_days} working day(s) of {leave_type} leave "
            f"from {start_date} to {end_date}. Would you like me to confirm and submit this request?"
        )
        return {
            "answer": ans,
            "route": "tool",
            "citations": [],
            "tool_calls": [prop_call],
            "pending_confirmation": True
        }

    # 5. Check Cancel Leave intent
    if any(k in msg_lower for k in ["cancel leave", "cancel my request", "cancel request", "cancel my leave"]):
        # Extract request_id if present (UUID or string)
        uuid_match = re.search(r"\b([a-f0-9\-]{8,36})\b", message, re.IGNORECASE)
        request_id = uuid_match.group(1) if uuid_match else None
        
        if not request_id:
            # Look up pending/approved requests
            active_reqs = execute_list_leave_requests(employee_id, status="pending").result or []
            active_reqs += [r for r in (execute_list_leave_requests(employee_id, status="approved").result or []) if r["start_date"] > today]
            if len(active_reqs) == 1:
                request_id = active_reqs[0]["request_id"]
            elif len(active_reqs) > 1:
                return {
                    "answer": f"You have {len(active_reqs)} active future leave requests. Which request ID would you like to cancel?",
                    "route": "clarify",
                    "citations": [],
                    "tool_calls": [],
                    "pending_confirmation": False
                }
            else:
                return {
                    "answer": "You do not have any upcoming leave requests that can be cancelled.",
                    "route": "tool",
                    "citations": [],
                    "tool_calls": [{"name": "cancel_leave", "args": {"request_id": ""}, "status": "error"}],
                    "pending_confirmation": False
                }
                
        is_valid, err_msg, req_dict = validate_cancel_leave(employee_id, request_id)
        if not is_valid:
            return {
                "answer": f"Cannot cancel request: {err_msg}",
                "route": "tool",
                "citations": [],
                "tool_calls": [{"name": "cancel_leave", "args": {"request_id": request_id}, "status": "error"}],
                "pending_confirmation": False
            }
            
        proposal_dict = {
            "type": "cancel_leave",
            "request_id": request_id
        }
        session_store.set_pending_proposal(session_id, proposal_dict)
        prop_call = {
            "name": "cancel_leave",
            "args": {"request_id": request_id},
            "status": "pending_confirmation"
        }
        ans = f"Are you sure you want to cancel your leave request {request_id} ({req_dict['leave_type']} leave from {req_dict['start_date']} to {req_dict['end_date']})?"
        return {
            "answer": ans,
            "route": "tool",
            "citations": [],
            "tool_calls": [prop_call],
            "pending_confirmation": True
        }

    # 6. Check View Balance intent
    if any(k in msg_lower for k in ["balance", "days left", "remaining leave", "leave allowance"]):
        # Future balance calculation (Section 6.4)
        if "by december" in msg_lower or "future balance" in msg_lower or "will i have" in msg_lower:
            # Hybrid route: reads tool + accrual document
            res = execute_get_leave_balance(employee_id)
            tool_calls = [res.to_api_dict()]
            retrieval = doc_store.retrieve("annual leave accrual schedule carry forward", requester["role"], requester["region"], today)
            ans = "Based on your current balance of " + ", ".join([f"{b['balance_days']} {b['leave_type']} days" for b in res.result]) + " and the annual accrual schedule, your projected balance increases accordingly."
            return {
                "answer": sanitize_text(ans),
                "route": "hybrid",
                "citations": retrieval["citations"][:2] or [{"doc_id": "TBL-LEAVE-ACCRUAL", "locator": "p. 1"}],
                "tool_calls": tool_calls,
                "pending_confirmation": False
            }
            
        # Target employee check (e.g. asking about another employee)
        emp_match = re.search(r"\b(E\d{4})\b", message)
        target_id = emp_match.group(1) if emp_match else employee_id
        
        res = execute_get_leave_balance(employee_id, employee_id=target_id)
        tool_calls = [res.to_api_dict()]
        if res.status == "error":
            return {
                "answer": sanitize_text(res.error_msg or REFUSAL_MESSAGE),
                "route": "tool",
                "citations": [],
                "tool_calls": tool_calls,
                "pending_confirmation": False
            }
        balance_desc = ", ".join([f"{b['leave_type'].capitalize()}: {b['balance_days']} days" for b in res.result])
        return {
            "answer": f"Current leave balances: {balance_desc}.",
            "route": "tool",
            "citations": [],
            "tool_calls": tool_calls,
            "pending_confirmation": False
        }

    # 7. Check List Leave Requests intent
    if any(k in msg_lower for k in ["my requests", "list requests", "leave history", "view leave"]):
        emp_match = re.search(r"\b(E\d{4})\b", message)
        target_id = emp_match.group(1) if emp_match else employee_id
        res = execute_list_leave_requests(employee_id, employee_id=target_id)
        tool_calls = [res.to_api_dict()]
        if res.status == "error":
            return {
                "answer": sanitize_text(res.error_msg or REFUSAL_MESSAGE),
                "route": "tool",
                "citations": [],
                "tool_calls": tool_calls,
                "pending_confirmation": False
            }
        count = len(res.result)
        ans = f"Found {count} leave request(s)." if count > 0 else "You have no leave requests on record."
        return {
            "answer": ans,
            "route": "tool",
            "citations": [],
            "tool_calls": tool_calls,
            "pending_confirmation": False
        }

    # 8. Check Team Leave (Managers only)
    if any(k in msg_lower for k in ["team leave", "direct reports", "who is out", "who is taking leave"]):
        start_d, end_d = resolve_relative_dates(message, today)
        if not start_d or not end_d:
            start_d, end_d = today, "2026-12-31"
        res = execute_get_team_leave(employee_id, start_d, end_d)
        tool_calls = [res.to_api_dict()]
        if res.status == "error":
            return {
                "answer": res.error_msg or "Unable to retrieve team leave.",
                "route": "tool",
                "citations": [],
                "tool_calls": tool_calls,
                "pending_confirmation": False
            }
        ans = f"Found {len(res.result)} team leave record(s) between {start_d} and {end_d}."
        return {
            "answer": sanitize_text(ans),
            "route": "tool",
            "citations": [],
            "tool_calls": tool_calls,
            "pending_confirmation": False
        }

    # 9. Document RAG Search
    # Check if a specific past date is mentioned (Section 5: Reference date)
    ref_date_match = re.search(r"\b(202[0-5]-\d{2}-\d{2}|in 202[0-5])\b", msg_lower)
    ref_date = today
    if ref_date_match:
        val = ref_date_match.group(1)
        if "in 2025" in val or val == "2025":
            ref_date = "2025-12-31"
        elif "-" in val:
            ref_date = val

    retrieval = doc_store.retrieve(message, requester["role"], requester["region"], ref_date)
    chunks = retrieval["chunks"]
    citations = retrieval["citations"]
    upcoming = retrieval["upcoming_changes"]
    
    if not chunks:
        # Section 8.1 no_answer rule: Say documents do not cover the question and suggest contacting HR team.
        return {
            "answer": "The available HR documents do not cover this question. Please contact the HR team at hr@veltrix.example for assistance.",
            "route": "no_answer",
            "citations": [],
            "tool_calls": [],
            "pending_confirmation": False
        }
        
    # Check if question is off-topic
    off_topic_keywords = ["weather", "movie", "recipe", "write code", "fix python", "capital of"]
    if any(k in msg_lower for k in off_topic_keywords):
        return {
            "answer": "I am an HR assistant for Veltrix Systems and cannot help with questions outside company policies, holidays, and leave management.",
            "route": "refuse",
            "citations": [],
            "tool_calls": [],
            "pending_confirmation": False
        }
        
    # Construct context from chunks
    context_text = "\n\n".join([f"[{c['doc_id']} - {c['locator']}]\n{c['text']}" for c in chunks[:5]])
    system_prompt = "You are the Veltrix Systems PeopleOps Assistant. Answer the employee's question accurately using ONLY the provided document excerpts. Cite sources and never make up facts."
    user_prompt = f"Employee Question: {message}\n\nDocument Context:\n{context_text}"
    
    answer = generate_answer(user_prompt, system_prompt)
    
    # Mention upcoming changes if any apply (Section 5.1)
    if upcoming:
        up_doc = upcoming[0]
        answer += f"\n\nNote: An upcoming update ({up_doc['title']}) takes effect on {up_doc['effective_date']}."
        if not any(c["doc_id"] == up_doc["doc_id"] for c in citations):
            citations.append({"doc_id": up_doc["doc_id"], "locator": "Upcoming Policy"})
            
    return {
        "answer": sanitize_text(answer),
        "route": "rag",
        "citations": citations,
        "tool_calls": [],
        "pending_confirmation": False
    }
