import os
import re
from datetime import datetime
from typing import Dict, Set, Optional
import pypdf
import docx
import bs4

MONTH_MAP = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6,
    "jul": 7, "aug": 8, "sep": 9, "oct": 10, "nov": 11, "dec": 12
}

def parse_date_str(text: str, default_year: int = 2026) -> Optional[str]:
    text = text.strip()
    m = re.search(r"\b(\d{1,2})\s+([A-Za-z]+)(?:\s+(\d{4}))?\b", text)
    if m:
        day = int(m.group(1))
        month_name = m.group(2).lower()
        year = int(m.group(3)) if m.group(3) else default_year
        if month_name in MONTH_MAP:
            month = MONTH_MAP[month_name]
            try:
                return f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                pass
    m2 = re.search(r"\b(\d{4})-(\d{2})-(\d{2})\b", text)
    if m2:
        return f"{m2.group(1)}-{m2.group(2)}-{m2.group(3)}"
    return None

class HolidayStore:
    def __init__(self):
        self.holidays: Dict[str, Set[str]] = {
            "IN": set(),
            "DE": set(),
            "US": set()
        }

    def load_from_corpus(self, corpus_dir: str):
        # 1. India Calendar
        in_pdf = os.path.join(corpus_dir, "holiday_calendar_india_2026.pdf")
        if os.path.exists(in_pdf):
            try:
                reader = pypdf.PdfReader(in_pdf)
                full_text = "\n".join(p.extract_text() or "" for p in reader.pages)
                # Split specifically between "1. Public holidays 2026" and "2. Restricted holidays 2026"
                if "1. Public holidays" in full_text:
                    parts = full_text.split("1. Public holidays")
                    after_header = parts[1]
                    if "2. Restricted holidays" in after_header:
                        pub_sec = after_header.split("2. Restricted holidays")[0]
                    else:
                        pub_sec = after_header
                    for line in pub_sec.split("\n"):
                        # Skip column headers
                        if any(k in line.lower() for k in ["date", "day", "holiday", "effective"]):
                            continue
                        d = parse_date_str(line, 2026)
                        if d and "2026-" in d:
                            self.holidays["IN"].add(d)
            except Exception as e:
                print(f"Error parsing India holidays: {e}")

        # 2. Germany Calendar
        de_docx = os.path.join(corpus_dir, "holiday_calendar_germany_2026.docx")
        if os.path.exists(de_docx):
            try:
                doc = docx.Document(de_docx)
                # In Germany, table 1 is metadata, table 2 is the holidays table
                for t in doc.tables:
                    for row in t.rows:
                        cells = [c.text.strip() for c in row.cells]
                        # Check if this row looks like a holiday row (has a date, day, holiday name)
                        if len(cells) >= 3 and cells[0] not in ["Document ID", "Date", "Version", "Effective date", "Applies to", "Owner", "Classification"]:
                            d = parse_date_str(cells[0], 2026)
                            if d and "2026-" in d:
                                self.holidays["DE"].add(d)
            except Exception as e:
                print(f"Error parsing Germany holidays: {e}")

        # 3. US Calendar
        us_html = os.path.join(corpus_dir, "holiday_calendar_us_2026.html")
        if os.path.exists(us_html):
            try:
                with open(us_html, "r", encoding="utf-8") as f:
                    soup = bs4.BeautifulSoup(f, "html.parser")
                tables = soup.find_all("table")
                # Table 2 is the holidays table
                for table in tables:
                    for tr in table.find_all("tr"):
                        tds = tr.find_all("td")
                        if len(tds) >= 3:
                            first_col = tds[0].get_text(strip=True)
                            if first_col not in ["Date", "Document ID"]:
                                d = parse_date_str(first_col, 2026)
                                if d and "2026-" in d:
                                    self.holidays["US"].add(d)
            except Exception as e:
                print(f"Error parsing US holidays: {e}")

holiday_store = HolidayStore()
