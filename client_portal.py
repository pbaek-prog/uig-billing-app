"""
Client Portal - Secure client-facing view
Allows clients to view their case status, invoices, payments, and documents.
Each client gets a unique access code.
Features:
  - Document upload to Google Drive (auto-create client folder)
  - Case intake form (personal info + case description)
  - Auto-translate non-English submissions to English
  - Email notification to firm on new submission
"""
import hashlib
import secrets
import string
import re
import json
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


# ============================================================
# DOCUMENT UPLOAD & CLIENT FOLDER MANAGEMENT
# ============================================================

def get_or_create_client_folder(drive_service, client_name, client_id, parent_folder_id):
    """Get or create a client-specific folder in Google Drive.
    Folder name format: 'ClientName (ID)' under the Clients parent folder.
    Returns folder_id.
    """
    folder_name = f"{client_name} ({client_id})"

    # Search for existing folder
    try:
        query = (
            f"name='{folder_name}' and "
            f"'{parent_folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        results = drive_service.files().list(
            q=query, spaces='drive', fields='files(id, name)', pageSize=5
        ).execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
    except Exception:
        pass

    # Create new folder
    try:
        file_metadata = {
            'name': folder_name,
            'mimeType': 'application/vnd.google-apps.folder',
            'parents': [parent_folder_id]
        }
        folder = drive_service.files().create(
            body=file_metadata, fields='id'
        ).execute()
        folder_id = folder.get('id')

        # Create subfolders
        for sub in ["Documents", "Forms", "Correspondence", "Case_Notes"]:
            sub_meta = {
                'name': sub,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [folder_id]
            }
            drive_service.files().create(body=sub_meta, fields='id').execute()

        return folder_id
    except Exception:
        return None


def get_subfolder_id(drive_service, parent_folder_id, subfolder_name):
    """Find a subfolder by name inside a parent folder."""
    try:
        query = (
            f"name='{subfolder_name}' and "
            f"'{parent_folder_id}' in parents and "
            f"mimeType='application/vnd.google-apps.folder' and trashed=false"
        )
        results = drive_service.files().list(
            q=query, spaces='drive', fields='files(id)', pageSize=1
        ).execute()
        files = results.get('files', [])
        if files:
            return files[0]['id']
    except Exception:
        pass
    return parent_folder_id  # fallback to parent


def upload_client_document(drive_service, file_content, file_name, mime_type,
                           client_folder_id, subfolder="Documents"):
    """Upload a document to the client's folder on Google Drive.
    Returns dict with file_id, file_link, or None on failure.
    """
    from googleapiclient.http import MediaInMemoryUpload

    target_folder = get_subfolder_id(drive_service, client_folder_id, subfolder)

    try:
        media = MediaInMemoryUpload(file_content, mimetype=mime_type, resumable=False)
        file_metadata = {
            'name': file_name,
            'parents': [target_folder]
        }
        uploaded = drive_service.files().create(
            body=file_metadata, media_body=media, fields='id, webViewLink'
        ).execute()
        return {
            'file_id': uploaded.get('id'),
            'file_link': uploaded.get('webViewLink'),
            'file_name': file_name,
        }
    except Exception as e:
        return None


def get_client_uploaded_files(drive_service, client_folder_id):
    """List all files in a client's folder (recursive)."""
    files_list = []
    try:
        query = f"'{client_folder_id}' in parents and trashed=false"
        results = drive_service.files().list(
            q=query, spaces='drive',
            fields='files(id, name, mimeType, webViewLink, createdTime, size)',
            pageSize=100
        ).execute()
        for f in results.get('files', []):
            if f['mimeType'] == 'application/vnd.google-apps.folder':
                # Recurse into subfolders
                files_list.extend(get_client_uploaded_files(drive_service, f['id']))
            else:
                files_list.append({
                    'id': f['id'],
                    'name': f['name'],
                    'link': f.get('webViewLink', ''),
                    'created': f.get('createdTime', ''),
                    'size': f.get('size', '0'),
                })
    except Exception:
        pass
    return files_list


# ============================================================
# CASE INTAKE FORM (save to Google Sheets)
# ============================================================

def setup_intake_sheet(sheets_service, spreadsheet_id):
    """Create Client_Intake sheet if it doesn't exist."""
    sheet_name = "Client_Intake"
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
            headers = [[
                "submission_id", "client_id", "client_name", "submitted_at",
                "full_name", "date_of_birth", "nationality", "phone", "email",
                "current_address", "immigration_status", "case_type",
                "case_description_original", "original_language",
                "case_description_english", "additional_notes",
                "documents_uploaded", "drive_folder_link",
                "notification_sent", "reviewed"
            ]]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A1:T1",
                valueInputOption="RAW", body={"values": headers}
            ).execute()
            return True
        except Exception:
            return False


def save_client_intake(sheets_service, spreadsheet_id, intake_data):
    """Save a client intake form submission to Google Sheets.
    intake_data is a dict with all form fields.
    Returns submission_id or None.
    """
    setup_intake_sheet(sheets_service, spreadsheet_id)

    submission_id = f"INTAKE-{datetime.now().strftime('%Y%m%d%H%M%S')}-{secrets.token_hex(3).upper()}"

    row = [
        submission_id,
        intake_data.get("client_id", ""),
        intake_data.get("client_name", ""),
        datetime.now().isoformat(),
        intake_data.get("full_name", ""),
        intake_data.get("date_of_birth", ""),
        intake_data.get("nationality", ""),
        intake_data.get("phone", ""),
        intake_data.get("email", ""),
        intake_data.get("current_address", ""),
        intake_data.get("immigration_status", ""),
        intake_data.get("case_type", ""),
        intake_data.get("case_description_original", ""),
        intake_data.get("original_language", "en"),
        intake_data.get("case_description_english", ""),
        intake_data.get("additional_notes", ""),
        intake_data.get("documents_uploaded", "0"),
        intake_data.get("drive_folder_link", ""),
        "FALSE",
        "FALSE",
    ]

    try:
        sheets_service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id, range="Client_Intake!A:T",
            valueInputOption="RAW", body={"values": [row]}
        ).execute()
        return submission_id
    except Exception:
        return None


# ============================================================
# AUTO-TRANSLATION (Google Translate API v2 via discovery)
# ============================================================

def detect_language(text):
    """Simple heuristic language detection based on Unicode ranges.
    Returns language code estimate.
    """
    if not text or not text.strip():
        return "en"

    sample = text[:500]

    # Count character types
    cjk = 0
    hangul = 0
    hiragana_katakana = 0
    cyrillic = 0
    arabic = 0
    devanagari = 0
    latin = 0
    vietnamese_marks = 0

    # Vietnamese-specific diacritical characters
    viet_chars = set("ăắằẳẵặâấầẩẫậđêếềểễệôốồổỗộơớờởỡợưứừửữựỳỷỹ"
                     "ĂẮẰẲẴẶÂẤẦẨẪẬĐÊẾỀỂỄỆÔỐỒỔỖỘƠỚỜỞỠỢƯỨỪỬỮỰỲỶỸ")

    for ch in sample:
        cp = ord(ch)
        if ch in viet_chars:
            vietnamese_marks += 1
        elif 0xAC00 <= cp <= 0xD7AF or 0x1100 <= cp <= 0x11FF:
            hangul += 1
        elif 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            cjk += 1
        elif 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
            hiragana_katakana += 1
        elif 0x0400 <= cp <= 0x04FF:
            cyrillic += 1
        elif 0x0600 <= cp <= 0x06FF or 0xFE70 <= cp <= 0xFEFF:
            arabic += 1
        elif 0x0900 <= cp <= 0x097F:
            devanagari += 1
        elif 0x0041 <= cp <= 0x007A:
            latin += 1

    total = max(1, hangul + cjk + hiragana_katakana + cyrillic + arabic + devanagari + latin + vietnamese_marks)

    if hangul / total > 0.2:
        return "ko"
    if hiragana_katakana / total > 0.1:
        return "ja"
    if cjk / total > 0.2:
        return "zh"
    if cyrillic / total > 0.2:
        return "ru"
    if arabic / total > 0.2:
        return "ar"
    if devanagari / total > 0.2:
        return "hi"
    if vietnamese_marks / total > 0.05:
        return "vi"

    # For Latin-script languages (es, pt, fr, tl), default to "en" —
    # Google Translate API will detect more accurately if available
    return "en"


def translate_to_english(text, credentials=None):
    """Translate text to English using Google Cloud Translation API.
    Falls back to returning original text with [NEEDS TRANSLATION] prefix
    if API is not available.
    Returns (translated_text, detected_language).
    """
    if not text or not text.strip():
        return text, "en"

    # Detect language locally first
    detected = detect_language(text)
    if detected == "en":
        return text, "en"

    # Try Google Cloud Translation API (uses same credentials)
    if credentials:
        try:
            from googleapiclient.discovery import build
            translate_service = build('translate', 'v2', credentials=credentials)
            result = translate_service.translations().list(
                q=text, target='en', format='text'
            ).execute()
            translations = result.get('translations', [])
            if translations:
                translated = translations[0].get('translatedText', text)
                api_detected = translations[0].get('detectedSourceLanguage', detected)
                return translated, api_detected
        except Exception:
            pass

    # Fallback: return original with marker
    lang_names = {
        "ko": "Korean", "zh": "Chinese", "ja": "Japanese", "es": "Spanish",
        "vi": "Vietnamese", "ru": "Russian", "ar": "Arabic", "hi": "Hindi",
        "pt": "Portuguese", "fr": "French", "tl": "Tagalog",
    }
    lang_name = lang_names.get(detected, detected)
    return f"[ORIGINAL: {lang_name}] {text}", detected


# ============================================================
# EMAIL NOTIFICATION TO FIRM
# ============================================================

def send_submission_notification(gmail_credentials, client_name, submission_id,
                                 intake_summary, file_links=None,
                                 folder_link=None,
                                 notify_email="info@usimmigrationgroup.org"):
    """Send email notification to firm about new client submission.
    Uses Gmail API to create and send a message.
    """
    try:
        from googleapiclient.discovery import build
        gmail_service = build('gmail', 'v1', credentials=gmail_credentials)

        files_html = ""
        if file_links:
            files_html = "<h3 style='color:#1A3C5E;'>📎 Uploaded Documents</h3><ul>"
            for fl in file_links:
                files_html += f"<li><a href='{fl['link']}'>{fl['name']}</a></li>"
            files_html += "</ul>"

        folder_html = ""
        if folder_link:
            folder_html = f"<p>📁 <a href='{folder_link}'>Open Client Folder in Drive</a></p>"

        html_body = f"""
        <div style="font-family:Arial,sans-serif; max-width:700px; margin:0 auto; padding:20px;">
            <div style="background:linear-gradient(135deg,#1A3C5E,#2E5A8A); color:white;
                        padding:20px; border-radius:10px 10px 0 0; border-bottom:4px solid #F5A623;">
                <h2 style="margin:0;">📋 New Client Portal Submission</h2>
                <p style="margin:5px 0 0; opacity:0.9;">Submission ID: {submission_id}</p>
            </div>
            <div style="background:#f8f9fa; padding:20px; border-radius:0 0 10px 10px;">
                <h3 style="color:#1A3C5E;">👤 Client: {client_name}</h3>
                <table style="width:100%; border-collapse:collapse;">
        """

        for key, value in intake_summary.items():
            if value:
                html_body += f"""
                    <tr style="border-bottom:1px solid #eee;">
                        <td style="padding:8px; font-weight:bold; color:#555; width:35%;">{key}</td>
                        <td style="padding:8px; color:#333;">{value}</td>
                    </tr>"""

        html_body += f"""
                </table>
                {files_html}
                {folder_html}
                <hr style="border:none; border-top:1px solid #ddd; margin:20px 0;">
                <p style="color:#999; font-size:12px;">
                    This notification was sent automatically from the UIG Client Portal.<br>
                    US Immigration Group | (847) 449-8660
                </p>
            </div>
        </div>
        """

        import base64
        from email.mime.text import MIMEText

        message = MIMEText(html_body, 'html')
        message['to'] = notify_email
        message['subject'] = f"[UIG Portal] New Submission from {client_name} ({submission_id})"
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

        # Send the message
        gmail_service.users().messages().send(
            userId='me', body={'raw': raw}
        ).execute()
        return True
    except Exception as e:
        # Try creating a draft instead
        try:
            draft_body = {'message': {'raw': raw}}
            gmail_service.users().drafts().create(
                userId='me', body=draft_body
            ).execute()
            return True
        except Exception:
            return False
