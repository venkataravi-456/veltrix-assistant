from datetime import date, timedelta
from typing import Tuple, List, Set, Optional
from src.ingestion.holidays import holiday_store

def parse_date(date_str: str) -> date:
    return date.fromisoformat(date_str)

def get_working_days(
    start_date_str: str,
    end_date_str: str,
    region: str,
    holidays: Optional[Set[str]] = None
) -> Tuple[int, List[str]]:
    """
    Computes working days between start_date and end_date (inclusive).
    Working days are Monday to Friday (weekday 0-4) and not in the region's public holidays.
    Returns (count, list of working day strings).
    """
    start_dt = parse_date(start_date_str)
    end_dt = parse_date(end_date_str)
    
    if holidays is None:
        holidays = holiday_store.holidays.get(region, set())
        
    working_days_list = []
    curr = start_dt
    while curr <= end_dt:
        iso_str = curr.isoformat()
        # weekday(): Monday is 0 and Sunday is 6
        if curr.weekday() < 5 and iso_str not in holidays:
            working_days_list.append(iso_str)
        curr += timedelta(days=1)
        
    return len(working_days_list), working_days_list
