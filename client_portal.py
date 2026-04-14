"""
Client Portal - Secure client-facing view
Allows clients to view their case status, invoices, payments, and documents.
Each client gets a unique access code.
"""
import hashlib
import secrets
import string
from datetime import datetime


def generate_portal_code(length=8):
    """Generate a random alphanumeric portal access code."""
    alphabet = string.ascii_uppercase + string.digits
    # Remove confusing characters
    alphabet = alphabet.replace("O", "").replace("0", "").replace("I", "").replace("1", "")
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def hash_code(code):
    """Hash a portal code for secure storage."""
    return hashlib.sha256(code.encode()).hexdigest()


# === Google Sheets integration ===

def setup_portal_sheet(sheets_service, spreadsheet_id):
    """Create Client_Portal sheet if it doesn't exist."""
    sheet_name = "Client_Portal"
    try:
        sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1"
        ).execute()
        return True
    except Exception:
        try:
            body = {"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]}
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id, body=body
            ).execute()
            headers = [["client_id", "client_name", "access_code_hash", "email",
                       "portal_enabled", "created_at", "last_login", "language"]]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:H1",
                valueInputOption="RAW", body={"values": headers}
            ).execute()
            return True
        except Exception:
            return False


def create_portal_access(client_id, client_name, email, sheets_service=None, spreadsheet_id=None):
    """Create portal access for a client. Returns the plain-text access code."""
    code = generate_portal_code()
    code_hash = hash_code(code)

    if sheets_service and spreadsheet_id:
        setup_portal_sheet(sheets_service, spreadsheet_id)
        row_data = [
            client_id, client_name, code_hash, email,
            "TRUE", datetime.now().isoformat(), "", "en"
        ]
        try:
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id, range="Client_Portal!A:H",
                valueInputOption="RAW", body={"values": [row_data]}
            ).execute()
        except Exception:
            pass

    return code


def verify_portal_access(access_code, sheets_service=None, spreadsheet_id=None):
    """Verify a client portal access code. Returns client info if valid."""
    if not sheets_service or not spreadsheet_id:
        return None

    code_hash = hash_code(access_code.strip().upper())

    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="Client_Portal!A:H"
        ).execute()
        values = result.get("values", [])
        if len(values) <= 1:
            return None

        headers = values[0]
        for i, row in enumerate(values[1:], start=2):
            row_dict = {}
            for j, h in enumerate(headers):
                row_dict[h] = row[j] if j < len(row) else ""

            if row_dict.get("access_code_hash") == code_hash and row_dict.get("portal_enabled") == "TRUE":
                # Update last login
                try:
                    sheets_service.spreadsheets().values().update(
                        spreadsheetId=spreadsheet_id,
                        range=f"Client_Portal!G{i}",
                        valueInputOption="RAW",
                        body={"values": [[datetime.now().isoformat()]]}
                    ).execute()
                except Exception:
                    pass
                return row_dict
        return None
    except Exception:
        return None


def get_client_invoices(client_id, sheets_service=None, spreadsheet_id=None):
    """Get invoices for a specific client (portal view)."""
    if not sheets_service or not spreadsheet_id:
        return []
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="Invoices!A:L"
        ).execute()
        values = result.get("values", [])
        if len(values) <= 1:
            return []
        headers = values[0]
        invoices = []
        for row in values[1:]:
            inv = {}
            for i, h in enumerate(headers):
                inv[h] = row[i] if i < len(row) else ""
            if inv.get("client_id") == client_id:
                # Only expose safe fields
                invoices.append({
                    "invoice_number": inv.get("invoice_number", ""),
                    "date": inv.get("date", ""),
                    "due_date": inv.get("due_date", ""),
                    "amount": inv.get("amount", "0"),
                    "status": inv.get("status", ""),
                    "description": inv.get("description", ""),
                })
        return invoices
    except Exception:
        return []


def get_client_payments(client_id, sheets_service=None, spreadsheet_id=None):
    """Get payments for a specific client (portal view)."""
    if not sheets_service or not spreadsheet_id:
        return []
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="Payments!A:J"
        ).execute()
        values = result.get("values", [])
        if len(values) <= 1:
            return []
        headers = values[0]
        payments = []
        for row in values[1:]:
            pmt = {}
            for i, h in enumerate(headers):
                pmt[h] = row[i] if i < len(row) else ""
            if pmt.get("client_id") == client_id:
                payments.append({
                    "date": pmt.get("date", ""),
                    "amount": pmt.get("amount", "0"),
                    "method": pmt.get("method", ""),
                    "reference": pmt.get("reference", ""),
                })
        return payments
    except Exception:
        return []


def get_client_deadlines(client_id, sheets_service=None, spreadsheet_id=None):
    """Get upcoming deadlines for a specific client (portal view)."""
    if not sheets_service or not spreadsheet_id:
        return []
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id, range="Deadlines!A:H"
        ).execute()
        values = result.get("values", [])
        if len(values) <= 1:
            return []
        headers = values[0]
        deadlines = []
        for row in values[1:]:
            dl = {}
            for i, h in enumerate(headers):
                dl[h] = row[i] if i < len(row) else ""
            if dl.get("client_id") == client_id and dl.get("status", "") != "completed":
                deadlines.append({
                    "date": dl.get("date", ""),
                    "description": dl.get("description", ""),
                    "category": dl.get("category", ""),
                })
        return deadlines
    except Exception:
        return []
