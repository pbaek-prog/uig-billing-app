"""
USCIS Case Status Tracker
Automatically checks case status from USCIS website and stores history.
"""
import requests
import re
import json
from datetime import datetime


USCIS_STATUS_URL = "https://egov.uscis.gov/casestatus/mycasestatus.do"

# Status categories for color coding
STATUS_CATEGORIES = {
    "approved": ["approved", "welcome notice", "card was delivered", "card was picked up",
                 "card is being returned", "case was approved", "new card is being produced"],
    "pending": ["received", "case was received", "fingerprint fee was received",
                "case is ready to be scheduled", "interview was scheduled",
                "case was updated", "request for evidence was sent"],
    "action_required": ["request for evidence", "rfe", "response to rfe",
                        "must appear", "deficiency notice"],
    "denied": ["denied", "case was denied", "terminated", "withdrawn", "closed"],
    "transferred": ["transferred", "case was transferred"],
}


def check_case_status(receipt_number):
    """
    Check USCIS case status by receipt number.
    Receipt format: ABC1234567890 (3 letters + 10 digits)
    Returns dict with status info or error.
    """
    receipt_number = receipt_number.strip().upper()

    # Validate format
    if not re.match(r'^[A-Z]{3}\d{10}$', receipt_number):
        return {
            "success": False,
            "error": f"Invalid receipt number format: {receipt_number}. Expected: 3 letters + 10 digits (e.g., EAC2190012345)"
        }

    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "appReceiptNum": receipt_number,
            "caseStatusSearchBtn": "CHECK+STATUS",
        }

        response = requests.post(USCIS_STATUS_URL, data=data, headers=headers, timeout=15)

        if response.status_code != 200:
            return {"success": False, "error": f"USCIS returned status code {response.status_code}"}

        html = response.text

        # Extract status title
        title_match = re.search(r'<h1>(.*?)</h1>', html)
        status_title = title_match.group(1).strip() if title_match else "Unknown"

        # Extract status description
        desc_match = re.search(r'<p>(.*?)</p>', html, re.DOTALL)
        status_desc = ""
        if desc_match:
            status_desc = re.sub(r'<[^>]+>', '', desc_match.group(1)).strip()

        # Categorize status
        category = "unknown"
        title_lower = status_title.lower()
        for cat, keywords in STATUS_CATEGORIES.items():
            if any(kw in title_lower for kw in keywords):
                category = cat
                break

        return {
            "success": True,
            "receipt_number": receipt_number,
            "status_title": status_title,
            "status_description": status_desc[:500],
            "category": category,
            "checked_at": datetime.now().isoformat(),
        }

    except requests.Timeout:
        return {"success": False, "error": "USCIS website timed out. Try again later."}
    except requests.ConnectionError:
        return {"success": False, "error": "Cannot connect to USCIS website."}
    except Exception as e:
        return {"success": False, "error": f"Error checking status: {str(e)[:100]}"}


def check_multiple_cases(receipt_numbers):
    """Check status for multiple receipt numbers. Returns list of results."""
    results = []
    for rn in receipt_numbers:
        if rn and rn.strip():
            result = check_case_status(rn.strip())
            results.append(result)
    return results


def get_status_color(category):
    """Return color for status category."""
    colors = {
        "approved": "#28a745",      # Green
        "pending": "#ffc107",       # Yellow/Gold
        "action_required": "#dc3545",  # Red
        "denied": "#6c757d",        # Gray
        "transferred": "#17a2b8",   # Blue
        "unknown": "#999999",       # Light gray
    }
    return colors.get(category, "#999999")


def get_status_emoji(category):
    """Return emoji for status category."""
    emojis = {
        "approved": "✅",
        "pending": "⏳",
        "action_required": "🚨",
        "denied": "❌",
        "transferred": "🔄",
        "unknown": "❓",
    }
    return emojis.get(category, "❓")


# === Google Sheets integration for tracking ===

def save_case_to_sheets(case_data, sheets_service=None, spreadsheet_id=None):
    """Save or update a USCIS case in Google Sheets USCIS_Cases sheet."""
    if not sheets_service or not spreadsheet_id:
        return None

    sheet_name = "USCIS_Cases"

    # Check if case already exists
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=f"{sheet_name}!A:A"
        ).execute()
        values = result.get("values", [])

        row_index = None
        for i, row in enumerate(values):
            if row and row[0] == case_data.get("receipt_number"):
                row_index = i + 1
                break
    except Exception:
        # Sheet might not exist, create it
        try:
            body = {
                "requests": [{
                    "addSheet": {
                        "properties": {"title": sheet_name}
                    }
                }]
            }
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body
            ).execute()
            # Add headers
            headers = [["receipt_number", "client_name", "case_type", "status_title",
                       "status_description", "category", "last_checked", "filed_date", "notes"]]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A1:I1",
                valueInputOption="RAW",
                body={"values": headers}
            ).execute()
        except Exception:
            pass
        row_index = None

    row_data = [
        case_data.get("receipt_number", ""),
        case_data.get("client_name", ""),
        case_data.get("case_type", ""),
        case_data.get("status_title", ""),
        case_data.get("status_description", "")[:200],
        case_data.get("category", ""),
        case_data.get("checked_at", datetime.now().isoformat()),
        case_data.get("filed_date", ""),
        case_data.get("notes", ""),
    ]

    try:
        if row_index:
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A{row_index}:I{row_index}",
                valueInputOption="RAW",
                body={"values": [row_data]}
            ).execute()
        else:
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=f"{sheet_name}!A:I",
                valueInputOption="RAW",
                body={"values": [row_data]}
            ).execute()
        return True
    except Exception:
        return False


def get_all_tracked_cases(sheets_service=None, spreadsheet_id=None):
    """Get all tracked USCIS cases from Google Sheets."""
    if not sheets_service or not spreadsheet_id:
        return []
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="USCIS_Cases!A:I"
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
