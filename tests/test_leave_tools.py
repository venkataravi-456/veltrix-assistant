import pytest
from src.tools.leave_tools import (
    validate_apply_leave,
    commit_apply_leave,
    validate_cancel_leave,
    commit_cancel_leave,
    execute_get_leave_balance
)
from src.config import settings

def test_apply_leave_invalid_year():
    valid, msg, _ = validate_apply_leave("E2004", "annual", "2027-01-05", "2027-01-07")
    assert valid is False
    assert "2026" in msg

def test_apply_leave_past_start_date():
    today = settings.get_today() # "2026-09-15"
    valid, msg, _ = validate_apply_leave("E2004", "annual", "2026-08-01", "2026-08-05")
    assert valid is False
    assert "on or after today" in msg

def test_apply_leave_zero_working_days():
    # 2026-10-10 (Sat) to 2026-10-11 (Sun)
    valid, msg, _ = validate_apply_leave("E2004", "annual", "2026-10-10", "2026-10-11")
    assert valid is False
    assert "zero working days" in msg

def test_apply_leave_exceeds_balance():
    # E2004 asking for 30 working days (2026-09-21 to 2026-10-30), which exceeds their small balance without overlapping Nov
    valid, msg, _ = validate_apply_leave("E2004", "annual", "2026-09-21", "2026-10-30")
    assert valid is False
    assert "exceed" in msg.lower()

def test_apply_and_cancel_leave_atomic_flow():
    # Get initial balance
    init_b = execute_get_leave_balance("E2004", leave_type="annual").result[0]["balance_days"]
    
    # 1. Propose & Commit 1 day leave: 2026-10-13 (Tuesday)
    valid, _, working_days = validate_apply_leave("E2004", "annual", "2026-10-13", "2026-10-13")
    assert valid is True
    assert working_days == 1
    
    res = commit_apply_leave("E2004", "annual", "2026-10-13", "2026-10-13", working_days)
    assert res.status == "success"
    req_id = res.result["request_id"]
    
    # Verify balance was decremented by 1
    new_b = execute_get_leave_balance("E2004", leave_type="annual").result[0]["balance_days"]
    assert new_b == init_b - 1
    
    # Verify overlapping request rejection
    valid_overlap, msg, _ = validate_apply_leave("E2004", "annual", "2026-10-13", "2026-10-13")
    assert valid_overlap is False
    assert "overlap" in msg.lower()
    
    # 2. Cancel the request
    val_c, _, _ = validate_cancel_leave("E2004", req_id)
    assert val_c is True
    
    cancel_res = commit_cancel_leave("E2004", req_id)
    assert cancel_res.status == "success"
    
    # Verify balance restored
    restored_b = execute_get_leave_balance("E2004", leave_type="annual").result[0]["balance_days"]
    assert restored_b == init_b
