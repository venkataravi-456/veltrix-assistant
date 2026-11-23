import pytest
from src.retrieval.precedence import is_role_authorized, is_document_eligible
from src.database import check_can_view_leave
from src.tools.leave_tools import execute_get_leave_balance, REFUSAL_MESSAGE

def test_document_access_by_role():
    doc_all = {"doc_id": "D1", "access_level": "all", "regions": ["GLOBAL"], "effective_date": "2026-01-01"}
    doc_mgr = {"doc_id": "D2", "access_level": "managers", "regions": ["GLOBAL"], "effective_date": "2026-01-01"}
    doc_hr = {"doc_id": "D3", "access_level": "hr", "regions": ["GLOBAL"], "effective_date": "2026-01-01"}
    
    # Employee
    assert is_role_authorized("employee", "all") is True
    assert is_role_authorized("employee", "managers") is False
    assert is_role_authorized("employee", "hr") is False
    
    # Manager
    assert is_role_authorized("manager", "all") is True
    assert is_role_authorized("manager", "managers") is True
    assert is_role_authorized("manager", "hr") is False
    
    # HR
    assert is_role_authorized("hr", "all") is True
    assert is_role_authorized("hr", "managers") is True
    assert is_role_authorized("hr", "hr") is True

def test_leave_data_access_employee_self_only():
    # E2004 is employee, E2005 is peer employee
    assert check_can_view_leave("E2004", "E2004") is True
    assert check_can_view_leave("E2004", "E2005") is False
    
    # Attempting to fetch peer data returns error with standard refusal message
    res = execute_get_leave_balance("E2004", employee_id="E2005")
    assert res.status == "error"
    assert res.error_msg == REFUSAL_MESSAGE

def test_leave_data_access_manager_direct_reports():
    # E2002 is manager of E2004, but NOT manager of E2008
    assert check_can_view_leave("E2002", "E2002") is True
    assert check_can_view_leave("E2002", "E2004") is True
    assert check_can_view_leave("E2002", "E2008") is False
    
    res = execute_get_leave_balance("E2002", employee_id="E2008")
    assert res.status == "error"
    assert res.error_msg == REFUSAL_MESSAGE

def test_leave_data_access_hr_any_employee():
    # E1001 is HR
    assert check_can_view_leave("E1001", "E2004") is True
    assert check_can_view_leave("E1001", "E2008") is True
    
    res = execute_get_leave_balance("E1001", employee_id="E2004")
    assert res.status == "success"
