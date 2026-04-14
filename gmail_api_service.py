"""Gmail API service for creating drafts in user's Gmail account.
Uses OAuth2 for authentication - requires one-time browser authorization.
Adapted for US Immigration Group billing system.
"""
import os
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    GMAIL_API_AVAILABLE = True
except ImportError:
    GMAIL_API_AVAILABLE = False

try:
    from config import SCOPES, CREDENTIALS_FILE, TOKEN_FILE
    GMAIL_SCOPES = SCOPES  # Unified scopes include gmail.compose
    TOKEN_PATH = TOKEN_FILE
    CREDENTIALS_PATH = CREDENTIALS_FILE
except ImportError:
    GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.compose']
    TOKEN_PATH = os.path.join(os.path.dirname(__file__), 'gmail_token.json')
    CREDENTIALS_PATH = os.path.join(os.path.dirname(__file__), 'gmail_credentials.json')


def get_gmail_service():
    """Get authenticated Gmail API service. Returns None if not configured."""
    if not GMAIL_API_AVAILABLE:
        return None
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        elif os.path.exists(CREDENTIALS_PATH):
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
            creds = flow.run_local_server(port=8503, open_browser=True)
        else:
            return None

        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())

    return build('gmail', 'v1', credentials=creds)


def is_gmail_api_configured():
    if GMAIL_API_AVAILABLE and os.path.exists(CREDENTIALS_PATH):
        return True
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "google_credentials" in st.secrets:
            return True
    except Exception:
        pass
    return False


def is_gmail_api_authorized():
    # Try local token file
    if GMAIL_API_AVAILABLE and os.path.exists(TOKEN_PATH):
        try:
            creds = Credentials.from_authorized_user_file(TOKEN_PATH, GMAIL_SCOPES)
            if creds and creds.valid:
                return True
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
                with open(TOKEN_PATH, 'w') as f:
                    f.write(creds.to_json())
                return True
        except Exception:
            pass
    # Try Streamlit Cloud secrets
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "google_credentials" in st.secrets:
            import json
            token_data = st.secrets["google_credentials"].get("token_json", "")
            if token_data:
                token_info = json.loads(token_data)
                if token_info.get("refresh_token"):
                    return True
    except Exception:
        pass
    return False


def create_gmail_draft(to, subject, html_body, attachment_path=None):
    """Create a draft email in the user's Gmail account."""
    service = get_gmail_service()
    if not service:
        return False, "Gmail API not configured. Please set up OAuth credentials."

    msg = MIMEMultipart()
    msg['to'] = to
    msg['subject'] = subject
    msg.attach(MIMEText(html_body, 'html'))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, 'rb') as f:
            part = MIMEBase('application', 'octet-stream')
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition',
                          f'attachment; filename={os.path.basename(attachment_path)}')
            msg.attach(part)

    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    draft_body = {'message': {'raw': raw}}

    try:
        draft = service.users().drafts().create(userId='me', body=draft_body).execute()
        draft_id = draft.get('id', '')
        return True, f"Draft created (ID: {draft_id})"
    except Exception as e:
        return False, f"Failed to create draft: {str(e)}"


def authorize_gmail():
    """Run the OAuth authorization flow."""
    if not GMAIL_API_AVAILABLE:
        return False, "Google API libraries not installed. Run: pip install google-api-python-client google-auth-oauthlib"
    if not os.path.exists(CREDENTIALS_PATH):
        return False, f"Missing {CREDENTIALS_PATH}. Download OAuth credentials from Google Cloud Console."
    try:
        flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, GMAIL_SCOPES)
        creds = flow.run_local_server(port=8503, open_browser=True)
        with open(TOKEN_PATH, 'w') as f:
            f.write(creds.to_json())
        return True, "Gmail API authorized successfully!"
    except Exception as e:
        return False, f"Authorization failed: {str(e)}"
