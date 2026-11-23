import sqlite3
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any, Tuple
from src.config import settings

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(settings.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def get_employee(employee_id: str) -> Optional[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM employees WHERE employee_id = ?", (employee_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        conn.close()

def is_direct_report(manager_id: str, employee_id: str) -> bool:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT 1 FROM employees WHERE employee_id = ? AND manager_id = ?", (employee_id, manager_id))
        return cur.fetchone() is not None
    finally:
        conn.close()

def check_can_view_leave(requester_id: str, target_id: str) -> bool:
    if requester_id == target_id:
        return True
    requester = get_employee(requester_id)
    if not requester:
        return False
    role = requester["role"]
    if role == "hr":
        return True
    if role == "manager":
        return is_direct_report(requester_id, target_id)
    return False

def get_leave_balance(employee_id: str, leave_type: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if leave_type:
            cur.execute(
                "SELECT employee_id, leave_type, balance_days FROM leave_balances WHERE employee_id = ? AND leave_type = ?",
                (employee_id, leave_type.lower())
            )
        else:
            cur.execute(
                "SELECT employee_id, leave_type, balance_days FROM leave_balances WHERE employee_id = ?",
                (employee_id,)
            )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def list_leave_requests(employee_id: str, status: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        if status:
            cur.execute(
                "SELECT * FROM leave_requests WHERE employee_id = ? AND status = ? ORDER BY start_date DESC",
                (employee_id, status.lower())
            )
        else:
            cur.execute(
                "SELECT * FROM leave_requests WHERE employee_id = ? ORDER BY start_date DESC",
                (employee_id,)
            )
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_team_leave_requests(manager_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        # Direct reports whose pending or approved leave overlaps [start_date, end_date]
        # Overlap condition: req.start_date <= end_date AND req.end_date >= start_date
        query = """
            SELECT lr.*, e.full_name
            FROM leave_requests lr
            JOIN employees e ON lr.employee_id = e.employee_id
            WHERE e.manager_id = ?
              AND lr.status IN ('pending', 'approved')
              AND lr.start_date <= ?
              AND lr.end_date >= ?
            ORDER BY lr.start_date ASC
        """
        cur.execute(query, (manager_id, end_date, start_date))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def get_overlapping_requests(employee_id: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        query = """
            SELECT * FROM leave_requests
            WHERE employee_id = ?
              AND status IN ('pending', 'approved')
              AND start_date <= ?
              AND end_date >= ?
        """
        cur.execute(query, (employee_id, end_date, start_date))
        return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()

def apply_leave_tx(employee_id: str, leave_type: str, start_date: str, end_date: str, working_days: int) -> Tuple[bool, str, Optional[str]]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        conn.execute("BEGIN IMMEDIATE")
        
        # 1. Check current balance
        cur.execute(
            "SELECT balance_days FROM leave_balances WHERE employee_id = ? AND leave_type = ?",
            (employee_id, leave_type)
        )
        row = cur.fetchone()
        if not row:
            conn.rollback()
            return False, f"No balance found for leave type '{leave_type}'.", None
        
        current_balance = row["balance_days"]
        if working_days > current_balance:
            conn.rollback()
            return False, f"Working days ({working_days}) exceed current balance ({current_balance}).", None
        
        # 2. Check overlap with pending or approved
        cur.execute(
            """
            SELECT request_id FROM leave_requests
            WHERE employee_id = ?
              AND status IN ('pending', 'approved')
              AND start_date <= ?
              AND end_date >= ?
            """,
            (employee_id, end_date, start_date)
        )
        if cur.fetchone():
            conn.rollback()
            return False, "The requested dates overlap with an existing pending or approved leave request.", None
        
        # 3. Create request
        request_id = str(uuid.uuid4())
        created_at = datetime.utcnow().isoformat() + "Z"
        cur.execute(
            """
            INSERT INTO leave_requests (request_id, employee_id, leave_type, start_date, end_date, working_days, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)
            """,
            (request_id, employee_id, leave_type, start_date, end_date, working_days, created_at)
        )
        
        # 4. Subtract working_days from balance
        new_balance = current_balance - working_days
        cur.execute(
            "UPDATE leave_balances SET balance_days = ? WHERE employee_id = ? AND leave_type = ?",
            (new_balance, employee_id, leave_type)
        )
        
        conn.commit()
        return True, "Leave request created successfully.", request_id
    except Exception as e:
        conn.rollback()
        return False, f"Database transaction failed: {str(e)}", None
    finally:
        conn.close()

def cancel_leave_tx(employee_id: str, request_id: str, today: str) -> Tuple[bool, str]:
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        conn.execute("BEGIN IMMEDIATE")
        
        cur.execute("SELECT * FROM leave_requests WHERE request_id = ?", (request_id,))
        req = cur.fetchone()
        if not req:
            conn.rollback()
            return False, f"Leave request '{request_id}' not found."
        
        req = dict(req)
        if req["employee_id"] != employee_id:
            conn.rollback()
            return False, "You can only cancel your own leave requests."
        
        if req["status"] not in ("pending", "approved"):
            conn.rollback()
            return False, f"Cannot cancel a request with status '{req['status']}'."
        
        if req["start_date"] <= today:
            conn.rollback()
            return False, "Only requests whose start date is after today can be cancelled."
        
        working_days = req["working_days"]
        leave_type = req["leave_type"]
        
        # Update request status to cancelled
        cur.execute("UPDATE leave_requests SET status = 'cancelled' WHERE request_id = ?", (request_id,))
        
        # Add working_days back to balance
        cur.execute(
            "UPDATE leave_balances SET balance_days = balance_days + ? WHERE employee_id = ? AND leave_type = ?",
            (working_days, employee_id, leave_type)
        )
        
        conn.commit()
        return True, f"Leave request '{request_id}' has been cancelled and {working_days} day(s) restored to your {leave_type} balance."
    except Exception as e:
        conn.rollback()
        return False, f"Database transaction failed: {str(e)}"
    finally:
        conn.close()
