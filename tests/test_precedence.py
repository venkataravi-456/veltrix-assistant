import pytest
from src.retrieval.precedence import (
    is_document_eligible,
    compare_precedence,
    rank_documents,
    find_upcoming_changes
)

DOCS = [
    {"doc_id": "v1", "doc_type": "policy", "regions": ["GLOBAL"], "effective_date": "2025-01-01", "access_level": "all"},
    {"doc_id": "v2", "doc_type": "policy", "regions": ["GLOBAL"], "effective_date": "2026-04-01", "access_level": "all"},
    {"doc_id": "faq", "doc_type": "faq", "regions": ["GLOBAL"], "effective_date": "2026-05-01", "access_level": "all"},
    {"doc_id": "de_addendum", "doc_type": "addendum", "regions": ["DE"], "effective_date": "2025-06-01", "access_level": "all"},
    {"doc_id": "v3", "doc_type": "policy", "regions": ["GLOBAL"], "effective_date": "2027-01-01", "access_level": "all"}
]

def test_worked_example_india_employee_2026():
    # India employee on 2026-09-15
    ref_date = "2026-09-15"
    region = "IN"
    role = "employee"
    
    # Filter eligible
    eligible = [d for d in DOCS if is_document_eligible(d, role, region, ref_date)]
    # de_addendum is excluded (region mismatch)
    # v3 is excluded (effective 2027-01-01)
    assert set(d["doc_id"] for d in eligible) == {"v1", "v2", "faq"}
    
    # Rank by precedence: v2 outranks v1 on recency, and both outrank faq on authority
    ranked = rank_documents(eligible, region)
    assert ranked[0]["doc_id"] == "v2"
    
    # Upcoming changes: v3 is readable, applies to IN via GLOBAL, and takes effect 2027-01-01
    upcoming = find_upcoming_changes(DOCS, role, region, ref_date, ranked[0])
    assert len(upcoming) == 1
    assert upcoming[0]["doc_id"] == "v3"

def test_worked_example_germany_employee_2026():
    # Germany employee on 2026-09-15
    ref_date = "2026-09-15"
    region = "DE"
    role = "employee"
    
    eligible = [d for d in DOCS if is_document_eligible(d, role, region, ref_date)]
    assert set(d["doc_id"] for d in eligible) == {"v1", "v2", "faq", "de_addendum"}
    
    # de_addendum outranks GLOBAL documents on scope
    ranked = rank_documents(eligible, region)
    assert ranked[0]["doc_id"] == "de_addendum"
    
    # In 2027, de_addendum still outranks v3 on scope! So v3 is NOT an upcoming change
    upcoming = find_upcoming_changes(DOCS, role, region, ref_date, ranked[0])
    assert len(upcoming) == 0

def test_worked_example_past_reference_date():
    # India employee asking about 2025-08-01
    ref_date = "2025-08-01"
    region = "IN"
    role = "employee"
    
    eligible = [d for d in DOCS if is_document_eligible(d, role, region, ref_date)]
    assert len(eligible) == 1
    assert eligible[0]["doc_id"] == "v1"
