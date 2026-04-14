"""
US Immigration Group - Google Sheets Database Layer
Replaces SQLite with Google Sheets as the primary data store.
Uses google-api-python-client (Sheets API v4).
"""
import os
import json
import csv
import io
from datetime import datetime, date, timedelta
import hashlib
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

from config import (
    SPREADSHEET_ID, SCOPES, CREDENTIALS_FILE, TOKEN_FILE,
    SHEET_CLIENTS, SHEET_INVOICES, SHEET_PAYMENTS,
    SHEET_TRUST, SHEET_EXPENSES, SHEET_DEADLINES, SHEET_EMAIL_LOG,
    SHEET_AUDIT_LOG,
)

# =====================================================
# AUTH & SERVICE (cached singletons)
# =====================================================
_cached_creds = None
_cached_sheets_service = None
_cached_drive_service = None


def _load_secrets_credentials():
    """Load credentials from Streamlit Cloud secrets (st.secrets)."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "google_credentials" in st.secrets:
            sec = st.secrets["google_credentials"]
            token_data = sec.get("token_json", "")
            if token_data:
                token_info = json.loads(token_data)
                creds = Credentials.from_authorized_user_info(token_info, SCOPES)
                if creds and creds.expired and creds.refresh_token:
                    creds.refresh(Request())
                    # Update secrets is not possible, but token refreshes in memory
                return creds
    except Exception:
        pass
    return None


def get_credentials():
    """Get or refresh OAuth2 credentials (cached). Supports local files + Streamlit Cloud secrets."""
    global _cached_creds
    if _cached_creds and _cached_creds.valid:
        return _cached_creds

    creds = None

    # 1) Try local token file first
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

    # 2) If no local file, try Streamlit Cloud secrets
    if not creds:
        creds = _load_secrets_credentials()

    # 3) Refresh if expired
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists(CREDENTIALS_FILE):
                # Last resort: try secrets
                creds = _load_secrets_credentials()
                if creds:
                    _cached_creds = creds
                    return creds
                return None
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8504, open_browser=True)
        # Save refreshed token locally if possible
        try:
            with open(TOKEN_FILE, "w") as f:
                f.write(creds.to_json())
        except Exception:
            pass  # Streamlit Cloud: read-only filesystem, skip saving

    _cached_creds = creds
    return creds


def get_sheets_service():
    """Build and return Google Sheets API service (cached singleton)."""
    global _cached_sheets_service
    if _cached_sheets_service:
        # Verify credentials are still valid
        creds = get_credentials()
        if creds:
            return _cached_sheets_service
    creds = get_credentials()
    if not creds:
        return None
    _cached_sheets_service = build("sheets", "v4", credentials=creds)
    return _cached_sheets_service


def get_drive_service():
    """Build and return Google Drive API service (cached singleton)."""
    global _cached_drive_service
    if _cached_drive_service:
        creds = get_credentials()
        if creds:
            return _cached_drive_service
    creds = get_credentials()
    if not creds:
        return None
    _cached_drive_service = build("drive", "v3", credentials=creds)
    return _cached_drive_service


def is_sheets_configured():
    """Check if Google Sheets credentials are available (local file OR Streamlit Cloud secrets)."""
    if os.path.exists(CREDENTIALS_FILE):
        return True
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "google_credentials" in st.secrets:
            return True
    except Exception:
        pass
    return False


def is_sheets_authorized():
    """Check if we have valid OAuth tokens (auto-refresh if expired). Supports local + Cloud secrets."""
    # Try local token file
    if os.path.exists(TOKEN_FILE):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
            if creds and creds.valid:
                return True
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                try:
                    with open(TOKEN_FILE, "w") as f:
                        f.write(creds.to_json())
                except Exception:
                    pass
                return True
        except Exception:
            pass

    # Try Streamlit Cloud secrets
    creds = _load_secrets_credentials()
    if creds and creds.valid:
        return True

    return False


# =====================================================

# =====================================================
# CACHE LAYER
# =====================================================
_sheet_cache = {}  # {sheet_name: {"data": [...], "ts": datetime}}
_CACHE_TTL_SECONDS = 300  # 5 minutes (use Refresh button to force update)


def _invalidate_cache(sheet_name=None):
    """Invalidate cache for one sheet or all sheets."""
    if sheet_name:
        _sheet_cache.pop(sheet_name, None)
    else:
        _sheet_cache.clear()


def invalidate_all_caches():
    """Public function to clear all caches (used by refresh button)."""
    global _cached_sheets_service, _cached_drive_service, _cached_creds
    _invalidate_cache()
    _cached_sheets_service = None
    _cached_drive_service = None
    _cached_creds = None


# =====================================================
# SHEET HELPERS
# =====================================================

def _read_sheet(sheet_name, service=None, force_refresh=False):
    """Read all rows from a sheet. Uses in-memory cache with TTL."""
    if not force_refresh and sheet_name in _sheet_cache:
        cached = _sheet_cache[sheet_name]
        age = (datetime.now() - cached["ts"]).total_seconds()
        if age < _CACHE_TTL_SECONDS:
            return [dict(r) for r in cached["data"]]

    if service is None:
        service = get_sheets_service()
    if not service:
        return []
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}\!A1:ZZ"
        ).execute()
        values = result.get("values", [])
        if len(values) < 1:
            return []
        headers = values[0]
        rows = []
        for row in values[1:]:
            padded = row + [""] * (len(headers) - len(row))
            rows.append(dict(zip(headers, padded)))
        _sheet_cache[sheet_name] = {"data": rows, "ts": datetime.now()}
        return [dict(r) for r in rows]
    except Exception as e:
        print(f"Error reading {sheet_name}: {e}")
        return []


def _append_row(sheet_name, row_data, service=None):
    """Append a single row to a sheet. row_data is a list of values."""
    if service is None:
        service = get_sheets_service()
    if not service:
        return False
    try:
        service.spreadsheets().values().append(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!A1",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": [row_data]}
        ).execute()
        _invalidate_cache(sheet_name)
        return True
    except Exception as e:
        print(f"Error appending to {sheet_name}: {e}")
        return False


def _update_cell(sheet_name, row_index, col_index, value, service=None):
    """Update a single cell. row_index is 0-based data row (header=0)."""
    if service is None:
        service = get_sheets_service()
    if not service:
        return False
    # Convert to A1 notation (row_index + 2 because header is row 1)
    def _col_to_letter(c):
        s = ""
        while c >= 0:
            s = chr(65 + c % 26) + s
            c = c // 26 - 1
        return s
    col_letter = _col_to_letter(col_index)
    cell = f"{sheet_name}!{col_letter}{row_index + 2}"
    try:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=cell,
            valueInputOption="USER_ENTERED",
            body={"values": [[value]]}
        ).execute()
        _invalidate_cache(sheet_name)
        return True
    except Exception as e:
        print(f"Error updating cell {cell}: {e}")
        return False


def _update_row(sheet_name, row_index, row_data, service=None):
    """Update an entire row. row_index is 0-based data row."""
    if service is None:
        service = get_sheets_service()
    if not service:
        return False
    row_num = row_index + 2  # +1 for header, +1 for 1-based
    def _col_to_letter(c):
        s = ""
        while c >= 0:
            s = chr(65 + c % 26) + s
            c = c // 26 - 1
        return s
    end_col = _col_to_letter(len(row_data) - 1)
    range_str = f"{sheet_name}!A{row_num}:{end_col}{row_num}"
    try:
        service.spreadsheets().values().update(
            spreadsheetId=SPREADSHEET_ID,
            range=range_str,
            valueInputOption="USER_ENTERED",
            body={"values": [row_data]}
        ).execute()
        _invalidate_cache(sheet_name)
        return True
    except Exception as e:
        print(f"Error updating row: {e}")
        return False


def _get_headers(sheet_name, service=None):
    """Get headers of a sheet."""
    if service is None:
        service = get_sheets_service()
    if not service:
        return []
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=SPREADSHEET_ID,
            range=f"{sheet_name}!1:1"
        ).execute()
        values = result.get("values", [])
        return values[0] if values else []
    except Exception:
        return []


# =====================================================
# INIT & SETUP
# =====================================================

HEADERS = {
    SHEET_CLIENTS: [
        "id", "name", "name_korean", "email", "phone", "address",
        "case_type", "case_number", "visa_type",
        "retainer_amount", "retainer_date", "retainer_end",
        "contact_person", "notes", "balance", "is_active", "created_at"
    ],
    SHEET_INVOICES: [
        "id", "client_id", "client_name", "invoice_number", "date_issued", "due_date",
        "description", "legal_fees", "filing_fees", "other_expenses",
        "retainer_applied", "total_amount", "amount_due",
        "status", "sent_date", "paid_date", "notes", "drive_file_id"
    ],
    SHEET_PAYMENTS: [
        "id", "client_id", "client_name", "invoice_id", "invoice_number",
        "date_received", "amount", "payment_method", "check_number",
        "deposit_to", "notes", "created_at"
    ],
    SHEET_TRUST: [
        "id", "client_id", "client_name", "date", "type",
        "description", "amount", "balance_after", "notes"
    ],
    SHEET_EXPENSES: [
        "id", "date", "category", "description", "amount",
        "vendor", "client_id", "client_name", "is_billable",
        "receipt_drive_id", "notes"
    ],
    SHEET_DEADLINES: [
        "id", "client_id", "client_name", "deadline_date", "description",
        "category", "status", "notes", "created_at"
    ],
    SHEET_EMAIL_LOG: [
        "id", "client_id", "client_name", "to_email", "subject",
        "email_type", "status", "sent_date", "notes"
    ],
    SHEET_AUDIT_LOG: [
        "id", "timestamp", "user", "action", "entity_type",
        "entity_id", "field_changed", "old_value", "new_value", "details"
    ],
}


def init_sheets():
    """Initialize all sheets with headers if they don't exist."""
    service = get_sheets_service()
    if not service:
        return False

    try:
        # Get existing sheet names
        meta = service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()
        existing_sheets = [s["properties"]["title"] for s in meta.get("sheets", [])]

        # Create missing sheets
        requests = []
        for sheet_name in HEADERS.keys():
            if sheet_name not in existing_sheets:
                requests.append({
                    "addSheet": {"properties": {"title": sheet_name}}
                })

        # Remove default "Sheet1" if our sheets are being created
        if requests and "Sheet1" in existing_sheets:
            sheet1_id = None
            for s in meta["sheets"]:
                if s["properties"]["title"] == "Sheet1":
                    sheet1_id = s["properties"]["sheetId"]
            if sheet1_id is not None:
                requests.append({"deleteSheet": {"sheetId": sheet1_id}})

        if requests:
            service.spreadsheets().batchUpdate(
                spreadsheetId=SPREADSHEET_ID,
                body={"requests": requests}
            ).execute()

        # Write headers to each sheet
        data = []
        for sheet_name, headers in HEADERS.items():
            data.append({
                "range": f"{sheet_name}!A1",
                "values": [headers]
            })

        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={
                "valueInputOption": "RAW",
                "data": data
            }
        ).execute()

        return True
    except Exception as e:
        print(f"Error initializing sheets: {e}")
        return False


def migrate_db():
    """No-op for Google Sheets backend. Schema is defined by HEADERS constants.
    Exists for compatibility with SQLite fallback interface.
    """
    pass


def seed_sample_clients():
    """Seed sample clients if Clients sheet is empty."""
    rows = _read_sheet(SHEET_CLIENTS)
    if len(rows) > 0:
        return

    samples = [
        ["1", "Yun, Soo-Jin", "윤수진", "soojin.yun@email.com", "(847) 555-0101",
         "123 Main St, Des Plaines, IL 60016", "Employment-Based", "UIG-2026-001",
         "H-1B", "1500", "2026-01-15", "2027-01-15", "Yun Soo-Jin", "", "0", "TRUE",
         datetime.now().isoformat()],
        ["2", "Kim, Min-Ho", "김민호", "minho.kim@email.com", "(847) 555-0102",
         "456 Oak Ave, Mount Prospect, IL 60056", "Family-Based", "UIG-2026-002",
         "I-130/I-485", "3500", "2026-02-01", "2027-02-01", "Kim Min-Ho", "", "0", "TRUE",
         datetime.now().isoformat()],
        ["3", "Park, Ji-Yeon", "박지연", "jiyeon.park@email.com", "(847) 555-0103",
         "789 Elm St, Arlington Heights, IL 60004", "Employment-Based", "UIG-2026-003",
         "EB-2 NIW", "5000", "2026-03-10", "2027-03-10", "Park Ji-Yeon", "", "0", "TRUE",
         datetime.now().isoformat()],
        ["4", "Lee, Dong-Hyun", "이동현", "dhlee@email.com", "(312) 555-0104",
         "321 Pine Rd, Chicago, IL 60601", "Humanitarian", "UIG-2026-004",
         "Asylum", "4000", "2025-11-01", "2026-11-01", "Lee Dong-Hyun", "", "0", "TRUE",
         datetime.now().isoformat()],
        ["5", "Choi, Hye-Won", "최혜원", "hwchoi@email.com", "(847) 555-0105",
         "654 Maple Dr, Schaumburg, IL 60193", "Naturalization", "UIG-2026-005",
         "N-400", "1200", "2026-04-01", "2027-04-01", "Choi Hye-Won", "", "0", "TRUE",
         datetime.now().isoformat()],
    ]

    service = get_sheets_service()
    if service:
        try:
            service.spreadsheets().values().append(
                spreadsheetId=SPREADSHEET_ID,
                range=f"{SHEET_CLIENTS}!A1",
                valueInputOption="USER_ENTERED",
                insertDataOption="INSERT_ROWS",
                body={"values": samples}
            ).execute()
        except Exception as e:
            print(f"Error seeding clients: {e}")


# =====================================================
# NEXT ID HELPER
# =====================================================

def _next_id(sheet_name, service=None):
    """Get next auto-increment ID for a sheet."""
    rows = _read_sheet(sheet_name, service)
    if not rows:
        return 1
    ids = [int(r.get("id", 0)) for r in rows if r.get("id", "").isdigit()]
    return max(ids) + 1 if ids else 1


# =====================================================
# CLIENT CRUD
# =====================================================

def get_all_clients(active_only=True):
    rows = _read_sheet(SHEET_CLIENTS)
    if active_only:
        rows = [r for r in rows if r.get("is_active", "TRUE").upper() == "TRUE"]
    # Convert numeric fields
    for r in rows:
        r["id"] = int(r.get("id", 0))
        r["retainer_amount"] = float(r.get("retainer_amount", 0) or 0)
        r["balance"] = float(r.get("balance", 0) or 0)
        r["is_active"] = r.get("is_active", "TRUE").upper() == "TRUE"
    return sorted(rows, key=lambda x: x.get("name", ""))


def get_client(client_id):
    rows = _read_sheet(SHEET_CLIENTS)
    for r in rows:
        if str(r.get("id", "")) == str(client_id):
            r["id"] = int(r.get("id", 0))
            r["retainer_amount"] = float(r.get("retainer_amount", 0) or 0)
            r["balance"] = float(r.get("balance", 0) or 0)
            r["is_active"] = r.get("is_active", "TRUE").upper() == "TRUE"
            return r
    return None


def add_client(name, name_korean="", email="", phone="", address="",
               case_type="", case_number="", visa_type="", retainer_amount=0,
               retainer_date=None, retainer_end=None, contact_person="", notes=""):
    new_id = _next_id(SHEET_CLIENTS)
    row = [
        str(new_id), name, name_korean, email, phone, address,
        case_type, case_number, visa_type, str(retainer_amount),
        retainer_date or "", retainer_end or "", contact_person, notes,
        "0", "TRUE", datetime.now().isoformat()
    ]
    _append_row(SHEET_CLIENTS, row)
    return new_id


def update_client(client_id, **kwargs):
    service = get_sheets_service()
    rows = _read_sheet(SHEET_CLIENTS, service)
    headers = HEADERS[SHEET_CLIENTS]
    for idx, r in enumerate(rows):
        if str(r.get("id", "")) == str(client_id):
            for key, val in kwargs.items():
                if key in headers:
                    r[key] = str(val)
            row_data = [r.get(h, "") for h in headers]
            _update_row(SHEET_CLIENTS, idx, row_data, service)
            return True
    return False


def update_client_balance(client_id, amount):
    """Update client balance by adding amount (positive = owed, negative = paid)."""
    service = get_sheets_service()
    rows = _read_sheet(SHEET_CLIENTS, service)
    headers = HEADERS[SHEET_CLIENTS]
    bal_idx = headers.index("balance")
    for idx, r in enumerate(rows):
        if str(r.get("id", "")) == str(client_id):
            current = float(r.get("balance", 0) or 0)
            new_bal = current + amount
            _update_cell(SHEET_CLIENTS, idx, bal_idx, str(round(new_bal, 2)), service)
            return True
    return False


# =====================================================
# INVOICE CRUD
# =====================================================

def get_next_invoice_number():
    rows = _read_sheet(SHEET_INVOICES)
    year = date.today().year
    prefix = f"INV-{year}-"
    nums = []
    for r in rows:
        inv = r.get("invoice_number", "")
        if inv.startswith(prefix):
            try:
                nums.append(int(inv.replace(prefix, "")))
            except ValueError:
                pass
    next_num = max(nums) + 1 if nums else 1
    return f"{prefix}{next_num:03d}"


def create_invoice(client_id, description, legal_fees=0, filing_fees=0,
                   other_expenses=0, retainer_applied=0, due_date=None,
                   invoice_date=None, notes=""):
    service = get_sheets_service()
    client = get_client(client_id)
    if not client:
        return None
    if invoice_date is None:
        invoice_date = date.today()
    elif isinstance(invoice_date, str):
        invoice_date = date.fromisoformat(invoice_date)

    inv_num = get_next_invoice_number()
    total = legal_fees + filing_fees + other_expenses
    amount_due = total - retainer_applied
    if due_date is None:
        due_date = date.today().isoformat()
    elif isinstance(due_date, date):
        due_date = due_date.isoformat()

    new_id = _next_id(SHEET_INVOICES, service)
    inv_date_str = invoice_date.isoformat() if isinstance(invoice_date, date) else str(invoice_date)
    row = [
        str(new_id), str(client_id), client["name"], inv_num,
        inv_date_str, due_date, description,
        str(legal_fees), str(filing_fees), str(other_expenses),
        str(retainer_applied), str(total), str(amount_due),
        "Unpaid", "", "", notes, ""
    ]
    _append_row(SHEET_INVOICES, row, service)

    # Update client balance
    update_client_balance(client_id, amount_due)

    return inv_num


def get_invoices(client_id=None, status=None):
    rows = _read_sheet(SHEET_INVOICES)
    for r in rows:
        r["id"] = int(r.get("id", 0) or 0)
        r["client_id"] = int(r.get("client_id", 0) or 0)
        r["legal_fees"] = float(r.get("legal_fees", 0) or 0)
        r["filing_fees"] = float(r.get("filing_fees", 0) or 0)
        r["other_expenses"] = float(r.get("other_expenses", 0) or 0)
        r["retainer_applied"] = float(r.get("retainer_applied", 0) or 0)
        r["total_amount"] = float(r.get("total_amount", 0) or 0)
        r["amount_due"] = float(r.get("amount_due", 0) or 0)
    if client_id:
        rows = [r for r in rows if r["client_id"] == int(client_id)]
    if status:
        rows = [r for r in rows if r.get("status", "") == status]
    return rows


def mark_invoice_sent(invoice_id):
    service = get_sheets_service()
    rows = _read_sheet(SHEET_INVOICES, service)
    headers = HEADERS[SHEET_INVOICES]
    sent_idx = headers.index("sent_date")
    status_idx = headers.index("status")
    for idx, r in enumerate(rows):
        if str(r.get("id", "")) == str(invoice_id):
            _update_cell(SHEET_INVOICES, idx, sent_idx, datetime.now().isoformat(), service)
            if r.get("status") == "Unpaid":
                _update_cell(SHEET_INVOICES, idx, status_idx, "Sent", service)
            return True
    return False


def mark_invoice_paid(invoice_id, paid_date=None):
    service = get_sheets_service()
    rows = _read_sheet(SHEET_INVOICES, service)
    headers = HEADERS[SHEET_INVOICES]
    status_idx = headers.index("status")
    paid_idx = headers.index("paid_date")
    for idx, r in enumerate(rows):
        if str(r.get("id", "")) == str(invoice_id):
            _update_cell(SHEET_INVOICES, idx, status_idx, "Paid", service)
            _update_cell(SHEET_INVOICES, idx, paid_idx,
                         paid_date or date.today().isoformat(), service)
            return True
    return False


def set_invoice_drive_file_id(invoice_id, drive_file_id):
    """Store the Google Drive file ID for an uploaded invoice."""
    service = get_sheets_service()
    rows = _read_sheet(SHEET_INVOICES, service)
    headers = HEADERS[SHEET_INVOICES]
    fid_idx = headers.index("drive_file_id")
    for idx, r in enumerate(rows):
        if str(r.get("id", "")) == str(invoice_id):
            _update_cell(SHEET_INVOICES, idx, fid_idx, drive_file_id, service)
            return True
    return False


# =====================================================
# PAYMENT
# =====================================================

def record_payment(client_id, invoice_id, amount=0, payment_method="Check",
                   check_number="", deposit_to="Operating", notes="",
                   date_received=None):
    service = get_sheets_service()
    client = get_client(client_id)
    if not client:
        return None

    # Get invoice number
    inv_num = ""
    if invoice_id:
        invs = get_invoices(client_id=client_id)
        for inv in invs:
            if inv["id"] == int(invoice_id):
                inv_num = inv.get("invoice_number", "")
                break

    pay_date = date_received or date.today().isoformat()
    if isinstance(pay_date, date) and not isinstance(pay_date, str):
        pay_date = pay_date.isoformat()

    new_id = _next_id(SHEET_PAYMENTS, service)
    row = [
        str(new_id), str(client_id), client["name"], str(invoice_id), inv_num,
        pay_date, str(amount), payment_method, check_number,
        deposit_to, notes, datetime.now().isoformat()
    ]
    _append_row(SHEET_PAYMENTS, row, service)

    # Update client balance (negative = reduces debt)
    update_client_balance(client_id, -amount)

    # Check if invoice is fully paid
    if invoice_id:
        invs = get_invoices(client_id=client_id)
        for inv in invs:
            if inv["id"] == int(invoice_id):
                # Sum payments for this invoice
                payments = get_payments(invoice_id=invoice_id)
                paid_total = sum(float(p.get("amount", 0)) for p in payments)
                if paid_total >= inv["amount_due"]:
                    mark_invoice_paid(invoice_id)
                break

    return new_id


def get_payments(client_id=None, invoice_id=None):
    rows = _read_sheet(SHEET_PAYMENTS)
    for r in rows:
        r["id"] = int(r.get("id", 0) or 0)
        r["client_id"] = int(r.get("client_id", 0) or 0)
        r["invoice_id"] = int(r.get("invoice_id", 0) or 0)
        r["amount"] = float(r.get("amount", 0) or 0)
    if client_id:
        rows = [r for r in rows if r["client_id"] == int(client_id)]
    if invoice_id:
        rows = [r for r in rows if r["invoice_id"] == int(invoice_id)]
    return rows


# =====================================================
# TRUST ACCOUNT (IOLTA)
# =====================================================

def trust_deposit(client_id, amount, description="", notes=""):
    service = get_sheets_service()
    client = get_client(client_id)
    if not client:
        return None
    # Calculate current trust balance for this client
    balance = get_trust_balance(client_id)
    new_balance = balance + amount
    new_id = _next_id(SHEET_TRUST, service)
    row = [
        str(new_id), str(client_id), client["name"], date.today().isoformat(),
        "Deposit", description, str(amount), str(round(new_balance, 2)), notes
    ]
    _append_row(SHEET_TRUST, row, service)
    return new_id


def trust_withdrawal(client_id, amount, description="", notes=""):
    service = get_sheets_service()
    client = get_client(client_id)
    if not client:
        return None
    balance = get_trust_balance(client_id)
    new_balance = balance - amount
    new_id = _next_id(SHEET_TRUST, service)
    row = [
        str(new_id), str(client_id), client["name"], date.today().isoformat(),
        "Withdrawal", description, str(-amount), str(round(new_balance, 2)), notes
    ]
    _append_row(SHEET_TRUST, row, service)
    return new_id


def get_trust_balance(client_id=None):
    rows = _read_sheet(SHEET_TRUST)
    if client_id:
        rows = [r for r in rows if str(r.get("client_id", "")) == str(client_id)]
    total = sum(float(r.get("amount", 0) or 0) for r in rows)
    return round(total, 2)


def get_trust_transactions(client_id=None):
    rows = _read_sheet(SHEET_TRUST)
    for r in rows:
        r["id"] = int(r.get("id", 0) or 0)
        r["client_id"] = int(r.get("client_id", 0) or 0)
        r["amount"] = float(r.get("amount", 0) or 0)
        r["balance_after"] = float(r.get("balance_after", 0) or 0)
    if client_id:
        rows = [r for r in rows if r["client_id"] == int(client_id)]
    return rows


# =====================================================
# EXPENSES
# =====================================================

def add_expense(exp_date, category, description, amount, vendor="",
                client_id=None, is_billable=False, notes=""):
    service = get_sheets_service()
    client_name = ""
    if client_id:
        client = get_client(client_id)
        client_name = client["name"] if client else ""

    new_id = _next_id(SHEET_EXPENSES, service)
    row = [
        str(new_id), exp_date if isinstance(exp_date, str) else exp_date.isoformat(),
        category, description, str(amount), vendor,
        str(client_id) if client_id else "", client_name,
        "TRUE" if is_billable else "FALSE", "", notes
    ]
    _append_row(SHEET_EXPENSES, row, service)
    return new_id


def get_expenses(category=None, client_id=None, start_date=None, end_date=None):
    rows = _read_sheet(SHEET_EXPENSES)
    for r in rows:
        r["id"] = int(r.get("id", 0) or 0)
        r["amount"] = float(r.get("amount", 0) or 0)
        r["client_id"] = r.get("client_id", "")
        r["is_billable"] = r.get("is_billable", "FALSE").upper() == "TRUE"
    if category:
        rows = [r for r in rows if r.get("category", "") == category]
    if client_id:
        rows = [r for r in rows if str(r.get("client_id", "")) == str(client_id)]
    if start_date:
        sd = start_date if isinstance(start_date, str) else start_date.isoformat()
        rows = [r for r in rows if r.get("date", "") >= sd]
    if end_date:
        ed = end_date if isinstance(end_date, str) else end_date.isoformat()
        rows = [r for r in rows if r.get("date", "") <= ed]
    return rows


# =====================================================
# DEADLINES
# =====================================================

def add_deadline(client_id, deadline_date, description, category="Filing", notes=""):
    service = get_sheets_service()
    client = get_client(client_id)
    client_name = client["name"] if client else ""
    new_id = _next_id(SHEET_DEADLINES, service)
    dd = deadline_date if isinstance(deadline_date, str) else deadline_date.isoformat()
    row = [
        str(new_id), str(client_id), client_name, dd, description,
        category, "Pending", notes, datetime.now().isoformat()
    ]
    _append_row(SHEET_DEADLINES, row, service)
    return new_id


def complete_deadline(deadline_id):
    service = get_sheets_service()
    rows = _read_sheet(SHEET_DEADLINES, service)
    headers = HEADERS[SHEET_DEADLINES]
    status_idx = headers.index("status")
    for idx, r in enumerate(rows):
        if str(r.get("id", "")) == str(deadline_id):
            _update_cell(SHEET_DEADLINES, idx, status_idx, "Completed", service)
            return True
    return False


def get_upcoming_deadlines(days=30, client_id=None):
    rows = _read_sheet(SHEET_DEADLINES)
    today = date.today().isoformat()
    future = date.today()
    from datetime import timedelta
    future = (future + timedelta(days=days)).isoformat()

    results = []
    for r in rows:
        r["id"] = int(r.get("id", 0) or 0)
        r["client_id"] = int(r.get("client_id", 0) or 0)
        dd = r.get("deadline_date", "")
        if r.get("status", "") == "Pending" and dd >= today and dd <= future:
            if client_id and r["client_id"] != int(client_id):
                continue
            results.append(r)
    return sorted(results, key=lambda x: x.get("deadline_date", ""))


# =====================================================
# EMAIL LOG
# =====================================================

def log_email(client_id, invoice_id, email_type, recipient, subject, notes=""):
    """Log an email. Matches database.py signature: (client_id, invoice_id, email_type, recipient, subject)."""
    service = get_sheets_service()
    client = get_client(client_id)
    client_name = client["name"] if client else ""
    new_id = _next_id(SHEET_EMAIL_LOG, service)
    row = [
        str(new_id), str(client_id), client_name, recipient, subject,
        email_type, "sent", datetime.now().isoformat(), notes
    ]
    _append_row(SHEET_EMAIL_LOG, row, service)
    return new_id


def get_email_log(client_id=None):
    rows = _read_sheet(SHEET_EMAIL_LOG)
    for r in rows:
        r["id"] = int(r.get("id", 0) or 0)
        r["client_id"] = int(r.get("client_id", 0) or 0)
    if client_id:
        rows = [r for r in rows if r["client_id"] == int(client_id)]
    return rows


# =====================================================
# DASHBOARD & REPORTS
# =====================================================

def get_dashboard_stats():
    clients = get_all_clients()
    invoices = get_invoices()
    payments = get_payments()
    expenses = get_expenses()

    total_billed = sum(i["total_amount"] for i in invoices)
    outstanding = sum(i["amount_due"] for i in invoices if i.get("status") != "Paid")
    total_collected = sum(p["amount"] for p in payments)
    total_expenses = sum(e["amount"] for e in expenses)
    trust_bal = get_trust_balance()
    past_due = get_past_due_invoices()

    return {
        "total_clients": len(clients),
        "total_billed": round(total_billed, 2),
        "outstanding": round(outstanding, 2),
        "total_collected": round(total_collected, 2),
        "trust_balance": round(trust_bal, 2),
        "total_expenses": round(total_expenses, 2),
        "net_income": round(total_collected - total_expenses, 2),
        "unpaid_count": len([i for i in invoices if i.get("status") != "Paid"]),
        "past_due_count": len(past_due),
    }


def get_past_due_invoices():
    invoices = get_invoices()
    today = date.today().isoformat()
    past_due = []
    for inv in invoices:
        if inv.get("status") in ("Unpaid", "Sent") and inv.get("due_date", "") < today:
            inv["days_overdue"] = (date.today() - date.fromisoformat(inv["due_date"])).days
            past_due.append(inv)
    return sorted(past_due, key=lambda x: x.get("days_overdue", 0), reverse=True)


def get_retainer_alerts(days_ahead=30):
    """Get clients whose retainer expires within days_ahead days."""
    clients = get_all_clients()
    today = date.today()
    threshold = (today + timedelta(days=days_ahead)).isoformat()
    alerts = []
    for c in clients:
        ret_end = c.get("retainer_end", "")
        if ret_end and ret_end <= threshold and ret_end >= today.isoformat():
            c["days_until_expiry"] = (date.fromisoformat(ret_end) - today).days
            c["days_remaining"] = c["days_until_expiry"]
            alerts.append(c)
    return alerts


def get_expired_retainers():
    """Get clients with expired retainers."""
    clients = get_all_clients()
    today = date.today()
    today_str = today.isoformat()
    expired = []
    for c in clients:
        ret_end = c.get("retainer_end", "")
        if ret_end and ret_end < today_str:
            try:
                c["days_expired"] = (today - date.fromisoformat(ret_end)).days
            except ValueError:
                c["days_expired"] = 0
            expired.append(c)
    return expired



def get_monthly_pnl(year, month):
    """Monthly P&L report."""
    month_prefix = f"{year}-{month:02d}"
    invoices = get_invoices()
    payments = get_payments()
    expenses = get_expenses()

    month_invoices = [i for i in invoices if i.get("date_issued", "").startswith(month_prefix)]
    month_payments = [p for p in payments if p.get("date_received", "").startswith(month_prefix)]
    month_expenses = [e for e in expenses if e.get("date", "").startswith(month_prefix)]

    invoiced = sum(i["total_amount"] for i in month_invoices)
    income = sum(p["amount"] for p in month_payments)
    expense_total = sum(e["amount"] for e in month_expenses)

    return {
        "year": year,
        "month": month,
        "invoiced": round(invoiced, 2),
        "income": round(income, 2),
        "expenses": round(expense_total, 2),
        "net": round(income - expense_total, 2),
        "payments": month_payments,
        "expense_items": month_expenses,
    }


def recalculate_all_balances():
    """Recalculate all client balances from invoices and payments."""
    clients = get_all_clients(active_only=False)
    service = get_sheets_service()
    invoices = get_invoices()
    payments = get_payments()
    headers = HEADERS[SHEET_CLIENTS]
    bal_idx = headers.index("balance")
    all_rows = _read_sheet(SHEET_CLIENTS, service)

    for idx, r in enumerate(all_rows):
        cid = r.get("id", "")
        if not cid:
            continue
        cid_int = int(cid)
        total_invoiced = sum(
            inv["amount_due"] for inv in invoices if inv["client_id"] == cid_int
        )
        total_paid = sum(
            p["amount"] for p in payments if p["client_id"] == cid_int
        )
        new_balance = round(total_invoiced - total_paid, 2)
        _update_cell(SHEET_CLIENTS, idx, bal_idx, str(new_balance), service)


# =====================================================
# AUDIT LOG
# =====================================================

def log_audit(action, entity_type, entity_id="", field_changed="",
              old_value="", new_value="", details="", user="system"):
    """Log an action to the Audit_Log sheet for compliance tracking."""
    service = get_sheets_service()
    if not service:
        return
    try:
        new_id = _next_id(SHEET_AUDIT_LOG, service)
        row = [
            str(new_id), datetime.now().isoformat(), user, action,
            entity_type, str(entity_id), field_changed,
            str(old_value)[:200], str(new_value)[:200], str(details)[:500]
        ]
        _append_row(SHEET_AUDIT_LOG, row, service)
    except Exception as e:
        print(f"Audit log error: {e}")


def get_audit_log(entity_type=None, entity_id=None, limit=100):
    """Retrieve recent audit log entries."""
    rows = _read_sheet(SHEET_AUDIT_LOG)
    if entity_type:
        rows = [r for r in rows if r.get("entity_type") == entity_type]
    if entity_id:
        rows = [r for r in rows if str(r.get("entity_id")) == str(entity_id)]
    # Sort by timestamp descending
    rows.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return rows[:limit]


# =====================================================
# BATCH UPDATE (Performance)
# =====================================================

def _batch_update_cells(sheet_name, updates, service=None):
    """Batch update multiple cells in one API call.
    updates: list of (row_index, col_index, value) tuples
    """
    if service is None:
        service = get_sheets_service()
    if not service or not updates:
        return False

    def _col_to_letter(c):
        s = ""
        while c >= 0:
            s = chr(65 + c % 26) + s
            c = c // 26 - 1
        return s

    data = []
    for row_idx, col_idx, value in updates:
        col_letter = _col_to_letter(col_idx)
        cell_range = f"{sheet_name}!{col_letter}{row_idx + 2}"
        data.append({"range": cell_range, "values": [[value]]})

    try:
        service.spreadsheets().values().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body={"valueInputOption": "USER_ENTERED", "data": data}
        ).execute()
        _invalidate_cache(sheet_name)
        return True
    except Exception as e:
        print(f"Batch update error: {e}")
        return False


def recalculate_all_balances_batch():
    """Recalculate all client balances using batch update (optimized)."""
    service = get_sheets_service()
    if not service:
        return
    invoices = get_invoices()
    payments = get_payments()
    headers = HEADERS[SHEET_CLIENTS]
    bal_idx = headers.index("balance")
    all_rows = _read_sheet(SHEET_CLIENTS, service)

    updates = []
    for idx, r in enumerate(all_rows):
        cid = r.get("id", "")
        if not cid:
            continue
        cid_int = int(cid)
        total_invoiced = sum(
            inv["amount_due"] for inv in invoices if inv["client_id"] == cid_int
        )
        total_paid = sum(
            p["amount"] for p in payments if p["client_id"] == cid_int
        )
        new_balance = round(total_invoiced - total_paid, 2)
        old_balance = r.get("balance", "0")
        if str(new_balance) != str(old_balance):
            updates.append((idx, bal_idx, str(new_balance)))

    if updates:
        _batch_update_cells(SHEET_CLIENTS, updates, service)
        log_audit("batch_recalculate", "balance", details=f"{len(updates)} clients updated")


# =====================================================
# OPTIMISTIC LOCKING (Concurrent Edit Protection)
# =====================================================

def _compute_row_hash(row_dict):
    """Compute a hash of row values for optimistic locking."""
    values = "|".join(str(v) for v in row_dict.values())
    return hashlib.md5(values.encode()).hexdigest()[:12]


def safe_update_client(client_id, expected_hash, **kwargs):
    """Update client only if the row hasn't changed since read (optimistic lock).
    Returns (success: bool, error_msg: str or None)
    """
    service = get_sheets_service()
    rows = _read_sheet(SHEET_CLIENTS, service, force_refresh=True)
    headers = HEADERS[SHEET_CLIENTS]

    for idx, r in enumerate(rows):
        if str(r.get("id", "")) == str(client_id):
            current_hash = _compute_row_hash(r)
            if current_hash != expected_hash:
                return False, "Data was modified by another user. Please refresh and try again."
            # Apply updates
            for key, val in kwargs.items():
                if key in headers:
                    r[key] = str(val)
            row_data = [r.get(h, "") for h in headers]
            _update_row(SHEET_CLIENTS, idx, row_data, service)
            log_audit("update", "client", client_id, details=str(kwargs))
            return True, None
    return False, "Client not found."


def get_client_with_hash(client_id):
    """Get client data with a hash for optimistic locking."""
    rows = _read_sheet(SHEET_CLIENTS, force_refresh=True)
    for r in rows:
        if str(r.get("id", "")) == str(client_id):
            r["_row_hash"] = _compute_row_hash(r)
            return r
    return None


# =====================================================
# BACKUP / EXPORT
# =====================================================

def export_all_sheets_csv(output_dir):
    """Export all sheets as CSV files for backup. Returns list of file paths."""
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    paths = []

    for sheet_name in HEADERS.keys():
        rows = _read_sheet(sheet_name, force_refresh=True)
        if not rows:
            continue
        filename = f"{sheet_name}_{timestamp}.csv"
        filepath = os.path.join(output_dir, filename)
        headers = list(rows[0].keys()) if rows else HEADERS[sheet_name]
        with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(rows)
        paths.append(filepath)

    log_audit("backup_export", "system", details=f"{len(paths)} sheets exported to {output_dir}")
    return paths


def export_sheet_to_excel(output_dir):
    """Export all sheets into a single Excel workbook for backup."""
    try:
        from openpyxl import Workbook
    except ImportError:
        return None

    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(output_dir, f"UIG_Backup_{timestamp}.xlsx")
    wb = Workbook()

    first = True
    for sheet_name in HEADERS.keys():
        rows = _read_sheet(sheet_name, force_refresh=True)
        if first:
            ws = wb.active
            ws.title = sheet_name
            first = False
        else:
            ws = wb.create_sheet(title=sheet_name)

        headers = HEADERS[sheet_name]
        ws.append(headers)
        for row in rows:
            ws.append([row.get(h, "") for h in headers])

    wb.save(filepath)
    log_audit("backup_excel", "system", details=f"Excel backup: {filepath}")
    return filepath


def upload_backup_to_drive(local_path):
    """Upload a backup file to Google Drive Backups folder."""
    try:
        from config import DRIVE_REPORTS_FOLDER_ID
        drive_service = get_drive_service()
        if not drive_service:
            return None

        # Find or create Backups folder under Reports
        query = f"name='Backups' and '{DRIVE_REPORTS_FOLDER_ID}' in parents and mimeType='application/vnd.google-apps.folder' and trashed=false"
        results = drive_service.files().list(q=query, spaces='drive', fields='files(id)').execute()
        folders = results.get('files', [])

        if folders:
            backup_folder_id = folders[0]['id']
        else:
            folder_meta = {
                'name': 'Backups',
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [DRIVE_REPORTS_FOLDER_ID]
            }
            folder = drive_service.files().create(body=folder_meta, fields='id').execute()
            backup_folder_id = folder['id']

        from googleapiclient.http import MediaFileUpload
        file_name = os.path.basename(local_path)
        file_metadata = {'name': file_name, 'parents': [backup_folder_id]}
        media = MediaFileUpload(local_path, resumable=True)
        uploaded = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id,webViewLink'
        ).execute()

        log_audit("backup_upload", "system", details=f"Uploaded {file_name} to Drive")
        return uploaded.get('webViewLink', uploaded.get('id'))
    except Exception as e:
        print(f"Drive backup upload error: {e}")
        return None
