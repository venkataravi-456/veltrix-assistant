from typing import List, Dict, Any, Optional, Tuple

# Authority ranks (lower number = higher authority)
AUTHORITY_RANKS = {
    "policy": 1,
    "addendum": 1,
    "memo": 1,
    "handbook": 1,
    "calendar": 1,
    "faq": 2,
    "wiki": 2
}

def is_role_authorized(role: str, access_level: str) -> bool:
    role = role.lower()
    access = access_level.lower()
    if access == "all":
        return True
    if access == "managers":
        return role in ("manager", "hr")
    if access == "hr":
        return role == "hr"
    return False

def is_document_eligible(doc: Dict[str, Any], role: str, region: str, reference_date: str) -> bool:
    # 1. Role access
    if not is_role_authorized(role, doc.get("access_level", "all")):
        return False
    # 2. Region match
    doc_regions = doc.get("regions", [])
    if region not in doc_regions and "GLOBAL" not in doc_regions:
        return False
    # 3. Effective date <= reference_date
    effective = doc.get("effective_date", "1970-01-01")
    if effective > reference_date:
        return False
    return True

def compare_precedence(doc_a: Dict[str, Any], doc_b: Dict[str, Any], user_region: str) -> int:
    """
    Returns:
       1 if doc_a outranks doc_b
      -1 if doc_b outranks doc_a
       0 if unresolved tie
    """
    # Test 1: Authority
    auth_a = AUTHORITY_RANKS.get(doc_a.get("doc_type", "wiki"), 3)
    auth_b = AUTHORITY_RANKS.get(doc_b.get("doc_type", "wiki"), 3)
    if auth_a < auth_b:
        return 1
    elif auth_a > auth_b:
        return -1
        
    # Test 2: Scope
    # Specific region outranks GLOBAL
    a_is_specific = (user_region in doc_a.get("regions", []))
    b_is_specific = (user_region in doc_b.get("regions", []))
    if a_is_specific and not b_is_specific:
        return 1
    elif b_is_specific and not a_is_specific:
        return -1
        
    # Test 3: Recency
    eff_a = doc_a.get("effective_date", "")
    eff_b = doc_b.get("effective_date", "")
    if eff_a > eff_b:
        return 1
    elif eff_a < eff_b:
        return -1
        
    return 0

def rank_documents(docs: List[Dict[str, Any]], user_region: str) -> List[Dict[str, Any]]:
    """
    Sorts eligible documents by precedence (highest precedence first).
    """
    from functools import cmp_to_key
    def cmp_func(a, b):
        # We want descending order (higher precedence first), so compare b to a
        return compare_precedence(b, a, user_region)
    return sorted(docs, key=cmp_to_key(cmp_func))

def find_upcoming_changes(
    all_manifest_docs: List[Dict[str, Any]],
    role: str,
    region: str,
    reference_date: str,
    current_winning_doc: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Finds documents whose effective_date > reference_date, readable by requester,
    for their region, and would outrank current winning doc on their effective date.
    """
    upcoming = []
    for doc in all_manifest_docs:
        if not is_role_authorized(role, doc.get("access_level", "all")):
            continue
        doc_regions = doc.get("regions", [])
        if region not in doc_regions and "GLOBAL" not in doc_regions:
            continue
        eff = doc.get("effective_date", "")
        if eff <= reference_date:
            continue
            
        # Would it outrank current winning doc?
        if current_winning_doc:
            cmp = compare_precedence(doc, current_winning_doc, region)
            if cmp > 0:
                upcoming.append(doc)
        else:
            upcoming.append(doc)
            
    return upcoming
