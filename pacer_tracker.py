"""
PACER/ECF Case Tracker & e-Filing Helper
Tracks federal court cases and manages filing deadlines.
Note: Actual PACER login requires credentials - this module manages case data
and provides links/tools for filing workflow.
"""
from datetime import datetime, date


# Federal Court Districts
FEDERAL_DISTRICTS = {
    "ILND": "Northern District of Illinois",
    "ILCD": "Central District of Illinois",
    "ILSD": "Southern District of Illinois",
    "7CIR": "Seventh Circuit Court of Appeals",
    "USSC": "United States Supreme Court",
}

# Common filing types
FILING_TYPES = [
    "Complaint",
    "Answer",
    "Motion to Dismiss",
    "Motion for Summary Judgment",
    "Motion to Compel",
    "Motion for Extension of Time",
    "Response/Opposition",
    "Reply Brief",
    "Notice of Appeal",
    "Petition for Review",
    "Memorandum of Law",
    "Discovery Request",
    "Interrogatories",
    "Request for Production",
    "Subpoena",
    "Settlement Agreement",
    "Stipulation",
    "Status Report",
    "Other",
]

# PACER URLs
PACER_URLS = {
    "login": "https://pacer.login.uscourts.gov/csologin/login.jsf",
    "case_search": "https://pcl.uscourts.gov/pcl/index.jsf",
    "ILND": "https://ecf.ilnd.uscourts.gov/",
    "ILCD": "https://ecf.ilcd.uscourts.gov/",
    "ILSD": "https://ecf.ilsd.uscourts.gov/",
    "7CIR": "https://ecf.ca7.uscourts.gov/",
}


def get_pacer_url(district="ILND"):
    """Get PACER/ECF URL for a district."""
    return PACER_URLS.get(district, PACER_URLS["case_search"])


def format_case_number(case_number):
    """Format and validate a federal case number. e.g., 1:24-cv-01234"""
    case_number = case_number.strip()
    # Common format: 1:24-cv-01234 or 24-cv-01234
    return case_number


def calculate_deadline(filed_date_str, days, business_days=False):
    """Calculate a deadline from a filing date."""
    from datetime import timedelta
    try:
        if isinstance(filed_date_str, str):
            filed_date = datetime.strptime(filed_date_str, "%Y-%m-%d").date()
        else:
            filed_date = filed_date_str

        if business_days:
            current = filed_date
            added = 0
            while added < days:
                current += timedelta(days=1)
                if current.weekday() < 5:  # Monday=0, Friday=4
                    added += 1
            return current
        else:
            return filed_date + timedelta(days=days)
    except Exception:
        return None


# Common federal court deadlines (in days)
FEDERAL_DEADLINES = {
    "Answer to Complaint": {"days": 21, "business_days": False},
    "Response to Motion": {"days": 14, "business_days": False},
    "Reply to Response": {"days": 7, "business_days": False},
    "Notice of Appeal": {"days": 30, "business_days": False},
    "Discovery Responses": {"days": 30, "business_days": False},
    "Rule 26(f) Conference": {"days": 21, "business_days": False},
    "Initial Disclosures": {"days": 14, "business_days": False},
    "Motion to Dismiss": {"days": 21, "business_days": False},
    "Petition for Review (Immigration)": {"days": 30, "business_days": False},
    "Petition for Review (7th Cir)": {"days": 30, "business_days": False},
}


def get_auto_deadlines(event_type, event_date_str):
    """Calculate automatic deadlines based on an event type."""
    deadlines = []

    if event_type == "Complaint Filed":
        deadlines.append({
            "name": "Answer to Complaint",
            "date": calculate_deadline(event_date_str, 21),
            "priority": "high",
        })
        deadlines.append({
            "name": "Motion to Dismiss Deadline",
            "date": calculate_deadline(event_date_str, 21),
            "priority": "high",
        })
    elif event_type == "Motion Filed Against":
        deadlines.append({
            "name": "Response to Motion",
            "date": calculate_deadline(event_date_str, 14),
            "priority": "high",
        })
    elif event_type == "Response Filed":
        deadlines.append({
            "name": "Reply Brief",
            "date": calculate_deadline(event_date_str, 7),
            "priority": "medium",
        })
    elif event_type == "Order/Judgment Entered":
        deadlines.append({
            "name": "Notice of Appeal",
            "date": calculate_deadline(event_date_str, 30),
            "priority": "high",
        })
        deadlines.append({
            "name": "Motion for Reconsideration",
            "date": calculate_deadline(event_date_str, 28),
            "priority": "medium",
        })
    elif event_type == "Discovery Request Received":
        deadlines.append({
            "name": "Discovery Responses Due",
            "date": calculate_deadline(event_date_str, 30),
            "priority": "high",
        })
    elif event_type == "Immigration Order":
        deadlines.append({
            "name": "Petition for Review (30 days)",
            "date": calculate_deadline(event_date_str, 30),
            "priority": "critical",
        })

    return deadlines


# === Google Sheets integration ===

def save_court_case(case_data, sheets_service=None, spreadsheet_id=None):
    """Save a court case to Google Sheets Court_Cases sheet."""
    if not sheets_service or not spreadsheet_id:
        return None

    sheet_name = "Court_Cases"

    # Ensure sheet exists
    try:
        sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1"
        ).execute()
    except Exception:
        try:
            body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body
            ).execute()
            headers = [["case_number", "case_name", "court", "district", "judge",
                       "client_name", "case_type", "status", "filed_date",
                       "next_deadline", "next_deadline_desc", "pacer_link", "notes", "updated_at"]]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:N1",
                valueInputOption="RAW", body={"values": headers}
            ).execute()
        except Exception:
            return None

    row_data = [
        case_data.get("case_number", ""),
        case_data.get("case_name", ""),
        case_data.get("court", ""),
        case_data.get("district", "ILND"),
        case_data.get("judge", ""),
        case_data.get("client_name", ""),
        case_data.get("case_type", ""),
        case_data.get("status", "Active"),
        case_data.get("filed_date", ""),
        case_data.get("next_deadline", ""),
        case_data.get("next_deadline_desc", ""),
        case_data.get("pacer_link", ""),
        case_data.get("notes", ""),
        datetime.now().isoformat(),
    ]

    try:
        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:N",
            valueInputOption="RAW", body={"values": [row_data]}
        ).execute()
        return True
    except Exception:
        return None


def get_all_court_cases(sheets_service=None, spreadsheet_id=None):
    """Get all court cases from Google Sheets."""
    if not sheets_service or not spreadsheet_id:
        return []
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="Court_Cases!A:N"
        ).execute()
        values = result.get("values", [])
        if len(values) <= 1:
            return []
        headers = values[0]
        cases = []
        for row in values[1:]:
            case = {}
            for i, h in enumerate(headers):
                case[h] = row[i] if i < len(row) else ""
            cases.append(case)
        return cases
    except Exception:
        return []
