import pytest
from src.tools.working_days import get_working_days
from src.ingestion.holidays import holiday_store

def test_working_days_weekend_exclusion():
    # 2026-10-09 is Friday, 2026-10-10 is Saturday, 2026-10-11 is Sunday, 2026-10-12 is Monday
    # Total days = 4, working days = 2 (Fri, Mon)
    holidays = set()
    count, days = get_working_days("2026-10-09", "2026-10-12", "US", holidays=holidays)
    assert count == 2
    assert days == ["2026-10-09", "2026-10-12"]

def test_working_days_holiday_exclusion():
    # US Thanksgiving 2026: 2026-11-26 (Thu) and 2026-11-27 (Fri) are public holidays
    # 2026-11-23 (Mon) to 2026-11-27 (Fri): 5 weekdays, 2 are holidays -> 3 working days
    us_holidays = {"2026-11-26", "2026-11-27"}
    count, days = get_working_days("2026-11-23", "2026-11-27", "US", holidays=us_holidays)
    assert count == 3
    assert days == ["2026-11-23", "2026-11-24", "2026-11-25"]

def test_working_days_spanning_holidays_and_weekends():
    # Germany: 2026-04-03 (Good Friday) and 2026-04-06 (Easter Monday)
    # Range: 2026-04-02 (Thu) to 2026-04-07 (Tue)
    # Thu (work), Fri (holiday), Sat (weekend), Sun (weekend), Mon (holiday), Tue (work) -> 2 working days
    de_holidays = {"2026-04-03", "2026-04-06"}
    count, days = get_working_days("2026-04-02", "2026-04-07", "DE", holidays=de_holidays)
    assert count == 2
    assert days == ["2026-04-02", "2026-04-07"]

def test_working_days_zero():
    # Range entirely over a weekend: Saturday to Sunday
    count, days = get_working_days("2026-10-10", "2026-10-11", "IN", holidays=set())
    assert count == 0
    assert days == []
