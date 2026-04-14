"""
US Immigration Group - Legal Billing System v3.0
800 E. Northwest Hwy. Ste 205, Mount Prospect, IL 60016
Full-featured billing with Google Sheets database + Google Drive file storage.
+ USCIS Tracker, PACER/ECF, Client Portal, Multi-language support.
"""
import streamlit as st
import pandas as pd
from datetime import date, datetime, timedelta
import calendar
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

# --- i18n (Multi-language) ---
from i18n import t, get_available_languages, LANGUAGE_NAMES

# --- Google Sheets Database (primary) with SQLite fallback ---
try:
    from google_sheets_db import (
        init_sheets, migrate_db, seed_sample_clients, get_all_clients, get_client,
        get_invoices, create_invoice, record_payment, get_payments,
        add_expense, get_expenses, get_dashboard_stats,
        log_email, get_email_log, mark_invoice_sent,
        get_past_due_invoices, get_retainer_alerts, get_expired_retainers,
        get_monthly_pnl, update_client_balance, recalculate_all_balances,
        add_client, update_client, trust_deposit, trust_withdrawal,
        get_trust_transactions, get_trust_balance,
        add_deadline, complete_deadline, get_upcoming_deadlines,
        is_sheets_configured, is_sheets_authorized, get_credentials,
        set_invoice_drive_file_id,
        invalidate_all_caches, log_audit, get_audit_log,
        export_all_sheets_csv, export_sheet_to_excel, upload_backup_to_drive,
        recalculate_all_balances_batch, get_client_with_hash, safe_update_client,
    )
    USE_GOOGLE_SHEETS = True
except ImportError:
    from database import (
        init_db as init_sheets, migrate_db, seed_sample_clients, get_all_clients, get_client,
        get_invoices, create_invoice, record_payment, get_payments,
        add_expense, get_expenses, get_dashboard_stats, get_db,
        log_email, get_email_log, mark_invoice_sent,
        get_past_due_invoices, get_retainer_alerts, get_expired_retainers,
        get_monthly_pnl, update_client_balance, recalculate_all_balances,
        add_client, update_client, trust_deposit, trust_withdrawal,
        get_trust_transactions, get_trust_balance,
        add_deadline, complete_deadline, get_upcoming_deadlines,
    )
    USE_GOOGLE_SHEETS = False

# --- Google Drive Service ---
try:
    from google_drive_service import (
        upload_invoice, upload_report, upload_document,
        list_client_files, get_client_folder, get_file_link,
    )
    HAS_DRIVE = True
except ImportError:
    HAS_DRIVE = False

from invoice_generator import generate_invoice_excel
try:
    from pdf_invoice_generator import generate_invoice_pdf
    HAS_PDF = True
except ImportError:
    HAS_PDF = False
from email_service import (
    build_invoice_email, build_invoice_email_html, build_past_due_email,
    build_deadline_reminder_email, send_email_smtp, simulate_send_email
)
from gmail_api_service import (
    is_gmail_api_configured, is_gmail_api_authorized,
    create_gmail_draft, authorize_gmail
)
from config import (
    FIRM_NAME, FIRM_ADDRESS, FIRM_CITY_STATE, FIRM_PHONE, FIRM_EMAIL,
    SPREADSHEET_ID, DRIVE_CLIENTS_FOLDER_ID,
)

# --- New modules: USCIS, PACER, Client Portal ---
try:
    from uscis_tracker import (
        check_case_status, check_multiple_cases, get_status_color,
        get_status_emoji, save_case_to_sheets, get_all_tracked_cases,
    )
    HAS_USCIS = True
except ImportError:
    HAS_USCIS = False

try:
    from pacer_tracker import (
        FEDERAL_DISTRICTS, FILING_TYPES, PACER_URLS,
        get_pacer_url, get_auto_deadlines, FEDERAL_DEADLINES,
        save_court_case, get_all_court_cases,
    )
    HAS_PACER = True
except ImportError:
    HAS_PACER = False

try:
    from client_portal import (
        create_portal_access, verify_portal_access,
        get_client_invoices, get_client_payments, get_client_deadlines,
    )
    HAS_PORTAL = True
except ImportError:
    HAS_PORTAL = False

# --- Page Config ---
st.set_page_config(
    page_title="US Immigration Group - Legal Billing",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- Password Protection with Reset via Email ---
import random
import string
import time as _time

def _generate_reset_code():
    """Generate a 6-digit reset code."""
    return ''.join(random.choices(string.digits, k=6))

def _send_reset_code_email(reset_code):
    """Send password reset code via Gmail API."""
    try:
        admin_email = st.secrets.get("admin_email", "p.baek@iifa.edu")
    except Exception:
        admin_email = "p.baek@iifa.edu"

    subject = "[UIG Billing] Password Reset Code"
    html_body = f"""
    <div style="font-family:Arial,sans-serif; max-width:500px; margin:0 auto; padding:30px;">
        <div style="text-align:center; border-bottom:3px solid #F5A623; padding-bottom:20px;">
            <h2 style="color:#1A3C5E;">⚖️ US Immigration Group</h2>
            <p style="color:#666;">Legal Billing System</p>
        </div>
        <div style="padding:30px 0; text-align:center;">
            <p style="color:#333; font-size:16px;">Your password reset code is:</p>
            <div style="background:#F5A623; color:#fff; font-size:36px; font-weight:bold;
                        letter-spacing:8px; padding:20px 40px; border-radius:10px;
                        display:inline-block; margin:20px 0;">{reset_code}</div>
            <p style="color:#999; font-size:13px;">This code expires in 10 minutes.</p>
        </div>
        <div style="border-top:1px solid #eee; padding-top:15px; text-align:center;">
            <p style="color:#999; font-size:12px;">
                If you did not request this reset, please ignore this email.<br>
                US Immigration Group | (847) 449-8660
            </p>
        </div>
    </div>
    """
    try:
        from gmail_api_service import create_gmail_draft
        result = create_gmail_draft(admin_email, subject, html_body)
        if result:
            # Try to send the draft directly
            try:
                from google_sheets_db import get_credentials
                from googleapiclient.discovery import build
                creds = get_credentials()
                if creds:
                    gmail_service = build('gmail', 'v1', credentials=creds)
                    draft_id = result.get('id')
                    if draft_id:
                        gmail_service.users().drafts().send(
                            userId='me', body={'id': draft_id}
                        ).execute()
                        return True
            except Exception:
                pass
            return True  # Draft created at minimum
    except Exception:
        pass
    return False

def check_password():
    """Returns True if the user has entered the correct password. Includes reset via email."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "portal_authenticated" not in st.session_state:
        st.session_state.portal_authenticated = False
    if "portal_client" not in st.session_state:
        st.session_state.portal_client = None
    if "show_reset" not in st.session_state:
        st.session_state.show_reset = False
    if "show_new_password" not in st.session_state:
        st.session_state.show_new_password = False
    if "reset_code" not in st.session_state:
        st.session_state.reset_code = None
    if "reset_code_time" not in st.session_state:
        st.session_state.reset_code_time = 0

    if st.session_state.authenticated:
        return True

    # Get password from secrets or use default
    try:
        correct_password = st.secrets.get("app_password", "uig2025!")
    except Exception:
        correct_password = "uig2025!"

    # Header
    st.markdown("""
    <div style="display:flex; justify-content:center; margin-top:60px;">
        <div style="text-align:center;">
            <h1 style="color:#1A3C5E;">⚖️ US Immigration Group</h1>
            <h3 style="color:#666;">Legal Billing System</h3>
            <p style="color:#999;">800 E. Northwest Hwy. Ste 205, Mount Prospect, IL 60016</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        st.markdown("---")

        # === Step 3: Set New Password ===
        if st.session_state.show_new_password:
            st.markdown("#### 🔑 Set New Password")
            new_pw = st.text_input("New Password", type="password", placeholder="Enter new password", key="new_pw")
            new_pw2 = st.text_input("Confirm Password", type="password", placeholder="Confirm new password", key="new_pw2")
            if st.button("Change Password", use_container_width=True, type="primary"):
                if not new_pw or len(new_pw) < 4:
                    st.error("Password must be at least 4 characters.")
                elif new_pw != new_pw2:
                    st.error("Passwords do not match.")
                else:
                    st.session_state.authenticated = True
                    st.session_state.show_new_password = False
                    st.session_state.show_reset = False
                    st.session_state.reset_code = None
                    st.success(f"✅ Password changed! Please update Streamlit Cloud Secrets with: app_password = \"{new_pw}\"")
                    st.info("⚠️ To make the new password permanent, go to Streamlit Cloud → Manage app → Settings → Secrets and update app_password.")
                    _time.sleep(3)
                    st.rerun()
            if st.button("← Back to Login", use_container_width=True):
                st.session_state.show_new_password = False
                st.session_state.show_reset = False
                st.rerun()

        # === Step 2: Enter Reset Code ===
        elif st.session_state.show_reset:
            st.markdown("#### 📧 Check Your Email")
            try:
                admin_email = st.secrets.get("admin_email", "p.baek@iifa.edu")
            except Exception:
                admin_email = "p.baek@iifa.edu"
            masked = admin_email[:3] + "***" + admin_email[admin_email.index("@"):]
            st.info(f"A reset code was sent to **{masked}**")

            code_input = st.text_input("Enter 6-digit code", placeholder="000000", max_chars=6, key="reset_input")
            if st.button("Verify Code", use_container_width=True, type="primary"):
                # Check expiration (10 minutes)
                if _time.time() - st.session_state.reset_code_time > 600:
                    st.error("Code expired. Please request a new one.")
                    st.session_state.show_reset = False
                    st.session_state.reset_code = None
                elif code_input == st.session_state.reset_code:
                    st.session_state.show_new_password = True
                    st.rerun()
                else:
                    st.error("Incorrect code. Please try again.")

            if st.button("← Back to Login", use_container_width=True):
                st.session_state.show_reset = False
                st.session_state.reset_code = None
                st.rerun()

        # === Step 1: Normal Login ===
        else:
            password = st.text_input("Password", type="password", placeholder="Enter password")
            if st.button("Login", use_container_width=True, type="primary"):
                if password == correct_password:
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Incorrect password. Please try again.")

            st.markdown("")
            if st.button("🔒 Forgot Password?", use_container_width=True):
                reset_code = _generate_reset_code()
                st.session_state.reset_code = reset_code
                st.session_state.reset_code_time = _time.time()
                with st.spinner("Sending reset code to your email..."):
                    sent = _send_reset_code_email(reset_code)
                if sent:
                    st.session_state.show_reset = True
                    st.rerun()
                else:
                    st.error("Failed to send email. Please contact administrator.")

        st.markdown("---")

        # --- Client Portal Login ---
        if HAS_PORTAL:
            with st.expander("🌐 Client Portal Login"):
                portal_code = st.text_input("Access Code", placeholder="Enter your access code",
                                           key="portal_code_input", type="password")
                if st.button("Enter Portal", use_container_width=True, key="portal_login_btn"):
                    if portal_code:
                        try:
                            from google_sheets_db import get_credentials
                            from googleapiclient.discovery import build
                            creds = get_credentials()
                            if creds:
                                sheets_svc = build('sheets', 'v4', credentials=creds)
                                client_info = verify_portal_access(
                                    portal_code, sheets_svc, SPREADSHEET_ID
                                )
                                if client_info:
                                    st.session_state.portal_authenticated = True
                                    st.session_state.portal_client = client_info
                                    st.session_state.authenticated = True
                                    st.rerun()
                                else:
                                    st.error("Invalid access code. Please try again.")
                            else:
                                st.error("System not configured. Contact your attorney.")
                        except Exception as e:
                            st.error("Portal temporarily unavailable. Contact your attorney.")
                    else:
                        st.warning("Please enter your access code.")

    return False

if not check_password():
    st.stop()

# --- Client Portal View (restricted) ---
if st.session_state.get("portal_authenticated") and st.session_state.get("portal_client"):
    _portal_client = st.session_state.portal_client
    _portal_lang = _portal_client.get("language", "en")
    _client_id = _portal_client.get("client_id", "")
    _client_name = _portal_client.get("client_name", "Client")

    st.markdown(f"""
    <div class="gold-banner">
        <h2 style="margin:0;">🌐 Client Portal</h2>
        <p style="margin:5px 0 0;">Welcome, {_client_name}</p>
    </div>
    """, unsafe_allow_html=True)

    st.sidebar.markdown("## 🌐 Client Portal")
    st.sidebar.markdown(f"**{_client_name}**")
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        st.session_state.portal_authenticated = False
        st.session_state.portal_client = None
        st.session_state.authenticated = False
        st.rerun()

    # --- Initialize services ---
    try:
        from google_sheets_db import get_credentials
        from googleapiclient.discovery import build
        _creds = get_credentials()
        _sheets_svc = build('sheets', 'v4', credentials=_creds) if _creds else None
        _drive_svc = build('drive', 'v3', credentials=_creds) if _creds else None
    except Exception:
        _creds = None
        _sheets_svc = None
        _drive_svc = None

    from client_portal import (
        get_client_invoices, get_client_payments, get_client_deadlines,
        get_or_create_client_folder, upload_client_document,
        get_client_uploaded_files, save_client_intake,
        translate_to_english, detect_language, send_submission_notification,
    )

    portal_tab1, portal_tab2, portal_tab3, portal_tab4, portal_tab5 = st.tabs([
        "📋 Case Info", "📤 Upload Documents", "📄 Invoices", "💰 Payments", "📅 Deadlines"
    ])

    # ============================
    # TAB 1: CASE INTAKE FORM
    # ============================
    with portal_tab1:
        st.subheader("📋 Your Case Information")
        st.markdown("Please fill in your information as completely as possible. "
                    "You may write in **any language** — we will translate automatically.")

        with st.form("case_intake_form", clear_on_submit=False):
            st.markdown("#### Personal Information")
            pi_col1, pi_col2 = st.columns(2)
            with pi_col1:
                intake_fullname = st.text_input("Full Legal Name *", placeholder="e.g. Juan Carlos Garcia Lopez")
                intake_dob = st.text_input("Date of Birth", placeholder="MM/DD/YYYY")
                intake_nationality = st.text_input("Nationality / Country of Birth", placeholder="e.g. Mexico")
            with pi_col2:
                intake_phone = st.text_input("Phone Number *", placeholder="e.g. (847) 555-1234")
                intake_email = st.text_input("Email Address *", placeholder="e.g. you@email.com")
                intake_address = st.text_input("Current Address", placeholder="Street, City, State, ZIP")

            st.markdown("---")
            st.markdown("#### Immigration / Case Details")
            ic_col1, ic_col2 = st.columns(2)
            with ic_col1:
                intake_status = st.selectbox("Current Immigration Status", [
                    "Select...", "U.S. Citizen", "Lawful Permanent Resident (Green Card)",
                    "H-1B Visa", "H-4 Visa", "L-1 Visa", "O-1 Visa",
                    "F-1 Student Visa", "J-1 Exchange Visitor", "B-1/B-2 Visitor",
                    "TPS", "DACA", "Asylum Pending", "Undocumented",
                    "Other (describe below)"
                ])
            with ic_col2:
                intake_case_type = st.selectbox("Type of Case / Service Needed", [
                    "Select...", "Family-Based Green Card", "Employment-Based Green Card",
                    "Naturalization / Citizenship", "H-1B Petition",
                    "L-1 Intracompany Transfer", "O-1 Extraordinary Ability",
                    "Asylum Application", "VAWA Petition", "U Visa",
                    "T Visa", "DACA Renewal", "TPS Application/Renewal",
                    "Removal / Deportation Defense", "Bond Hearing",
                    "Consular Processing", "Waiver (I-601 / I-212 / I-601A)",
                    "EB-5 Investor", "Other (describe below)"
                ])

            st.markdown("---")
            st.markdown("#### Describe Your Case")
            st.caption("✍️ You can write in any language (Korean, Spanish, Chinese, etc.) — "
                      "your description will be automatically translated to English for our team.")
            intake_description = st.text_area(
                "Please describe your situation in detail *",
                height=200,
                placeholder="Describe your immigration situation, what you need help with, "
                           "any deadlines you're aware of, previous cases or petitions filed, etc.\n\n"
                           "어떤 언어로든 작성하세요 / Escriba en cualquier idioma / 用任何语言写"
            )
            intake_notes = st.text_area(
                "Additional Notes (optional)",
                height=100,
                placeholder="Any other information you'd like us to know..."
            )

            submitted = st.form_submit_button("📨 Submit Case Information", use_container_width=True, type="primary")

        if submitted:
            if not intake_fullname or not intake_phone or not intake_description:
                st.error("Please fill in all required fields (*)")
            else:
                with st.spinner("Processing your submission..."):
                    # --- Auto-translate ---
                    desc_lang = detect_language(intake_description)
                    if desc_lang != "en":
                        translated_desc, detected = translate_to_english(intake_description, _creds)
                        st.info(f"🌐 Auto-translated from **{detected}** to English")
                    else:
                        translated_desc = intake_description
                        detected = "en"

                    notes_translated = intake_notes
                    if intake_notes and detect_language(intake_notes) != "en":
                        notes_translated, _ = translate_to_english(intake_notes, _creds)

                    # --- Create/get client folder on Drive ---
                    folder_link = ""
                    if _drive_svc:
                        client_folder_id = get_or_create_client_folder(
                            _drive_svc, _client_name, _client_id, DRIVE_CLIENTS_FOLDER_ID
                        )
                        if client_folder_id:
                            folder_link = f"https://drive.google.com/drive/folders/{client_folder_id}"

                    # --- Save to Google Sheets ---
                    intake_data = {
                        "client_id": _client_id,
                        "client_name": _client_name,
                        "full_name": intake_fullname,
                        "date_of_birth": intake_dob,
                        "nationality": intake_nationality,
                        "phone": intake_phone,
                        "email": intake_email,
                        "current_address": intake_address,
                        "immigration_status": intake_status if intake_status != "Select..." else "",
                        "case_type": intake_case_type if intake_case_type != "Select..." else "",
                        "case_description_original": intake_description,
                        "original_language": detected,
                        "case_description_english": translated_desc,
                        "additional_notes": notes_translated,
                        "documents_uploaded": "0",
                        "drive_folder_link": folder_link,
                    }

                    submission_id = save_client_intake(_sheets_svc, SPREADSHEET_ID, intake_data)

                    # --- Send email notification ---
                    if _creds and submission_id:
                        summary = {
                            "Full Name": intake_fullname,
                            "Phone": intake_phone,
                            "Email": intake_email,
                            "Nationality": intake_nationality,
                            "Immigration Status": intake_status if intake_status != "Select..." else "N/A",
                            "Case Type": intake_case_type if intake_case_type != "Select..." else "N/A",
                            "Case Description (English)": translated_desc[:500] + ("..." if len(translated_desc) > 500 else ""),
                            "Original Language": detected,
                        }
                        send_submission_notification(
                            _creds, _client_name, submission_id,
                            summary, folder_link=folder_link,
                            notify_email="info@usimmigrationgroup.org"
                        )

                if submission_id:
                    st.success(f"✅ Your information has been submitted successfully! (Ref: {submission_id})")
                    st.info("Our team has been notified and will review your case. "
                           "You may also upload supporting documents in the **Upload Documents** tab.")
                else:
                    st.error("There was an issue saving your information. Please try again or contact our office.")

    # ============================
    # TAB 2: DOCUMENT UPLOAD
    # ============================
    with portal_tab2:
        st.subheader("📤 Upload Documents")
        st.markdown("Upload your supporting documents (passport, I-94, visa, forms, letters, etc.)")
        st.caption("Accepted formats: PDF, JPG, PNG, DOCX, XLSX, TXT — Max 200MB per file")

        uploaded_files = st.file_uploader(
            "Choose files to upload",
            type=["pdf", "jpg", "jpeg", "png", "docx", "xlsx", "txt", "doc", "csv"],
            accept_multiple_files=True,
            key="portal_file_upload"
        )

        if uploaded_files:
            if st.button("📤 Upload All Files", use_container_width=True, type="primary"):
                if _drive_svc:
                    client_folder_id = get_or_create_client_folder(
                        _drive_svc, _client_name, _client_id, DRIVE_CLIENTS_FOLDER_ID
                    )
                    if client_folder_id:
                        upload_results = []
                        progress_bar = st.progress(0)
                        for idx, uf in enumerate(uploaded_files):
                            with st.spinner(f"Uploading {uf.name}..."):
                                result = upload_client_document(
                                    _drive_svc,
                                    uf.getvalue(),
                                    uf.name,
                                    uf.type or "application/octet-stream",
                                    client_folder_id,
                                    subfolder="Documents"
                                )
                                if result:
                                    upload_results.append(result)
                            progress_bar.progress((idx + 1) / len(uploaded_files))

                        if upload_results:
                            st.success(f"✅ {len(upload_results)} file(s) uploaded successfully!")

                            # Notify firm via email
                            if _creds:
                                folder_link = f"https://drive.google.com/drive/folders/{client_folder_id}"
                                send_submission_notification(
                                    _creds, _client_name,
                                    f"UPLOAD-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                                    {"Action": "Document Upload", "Files Uploaded": str(len(upload_results))},
                                    file_links=upload_results,
                                    folder_link=folder_link,
                                    notify_email="info@usimmigrationgroup.org"
                                )
                                st.info("📧 Our team has been notified about your upload.")

                            for r in upload_results:
                                st.markdown(f"✅ **{r['file_name']}** — [View in Drive]({r['file_link']})")
                        else:
                            st.error("Failed to upload files. Please try again.")
                    else:
                        st.error("Could not create your folder. Please contact our office.")
                else:
                    st.error("Drive service not available. Please contact our office.")

        # Show previously uploaded files
        st.markdown("---")
        st.subheader("📁 Your Uploaded Documents")
        if _drive_svc:
            try:
                client_folder_id = get_or_create_client_folder(
                    _drive_svc, _client_name, _client_id, DRIVE_CLIENTS_FOLDER_ID
                )
                if client_folder_id:
                    existing_files = get_client_uploaded_files(_drive_svc, client_folder_id)
                    if existing_files:
                        for ef in existing_files:
                            size_kb = int(ef.get('size', 0)) / 1024
                            size_str = f"{size_kb:.1f} KB" if size_kb < 1024 else f"{size_kb/1024:.1f} MB"
                            st.markdown(f"""
                            <div style="background:#f8f9fa; padding:10px 15px; border-radius:8px; margin:5px 0;
                                        border-left:3px solid #1A3C5E; display:flex; justify-content:space-between;">
                                <div>
                                    <strong>📄 {ef['name']}</strong><br>
                                    <span style="color:#999; font-size:12px;">{ef.get('created', '')[:10]} | {size_str}</span>
                                </div>
                                <div><a href="{ef['link']}" target="_blank" style="color:#F5A623;">View ↗</a></div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.info("No documents uploaded yet.")
            except Exception:
                st.info("No documents uploaded yet.")
        else:
            st.warning("Document storage not available.")

    # ============================
    # TAB 3: INVOICES
    # ============================
    with portal_tab3:
        st.subheader("📄 Your Invoices")
        invoices = get_client_invoices(_client_id, _sheets_svc, SPREADSHEET_ID) if _sheets_svc else []
        if invoices:
            for inv in invoices:
                status_color = "#28a745" if inv["status"].lower() == "paid" else "#dc3545"
                st.markdown(f"""
                <div style="background:#f8f9fa; padding:12px; border-radius:8px; margin:8px 0;
                            border-left:4px solid {status_color};">
                    <strong>{inv['invoice_number']}</strong> — ${float(inv.get('amount', 0)):,.2f}<br>
                    <span style="color:#666;">Due: {inv['due_date']}</span> |
                    <span style="color:{status_color}; font-weight:bold;">{inv['status']}</span><br>
                    <span style="color:#999;">{inv.get('description', '')}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No invoices found.")

    # ============================
    # TAB 4: PAYMENTS
    # ============================
    with portal_tab4:
        st.subheader("💰 Your Payments")
        payments = get_client_payments(_client_id, _sheets_svc, SPREADSHEET_ID) if _sheets_svc else []
        if payments:
            for pmt in payments:
                st.markdown(f"""
                <div style="background:#e0ffe0; padding:12px; border-radius:8px; margin:8px 0;
                            border-left:4px solid #28a745;">
                    <strong>${float(pmt.get('amount', 0)):,.2f}</strong> — {pmt['date']}<br>
                    <span style="color:#666;">Method: {pmt.get('method', 'N/A')} | Ref: {pmt.get('reference', 'N/A')}</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No payments recorded.")

    # ============================
    # TAB 5: DEADLINES
    # ============================
    with portal_tab5:
        st.subheader("📅 Upcoming Deadlines")
        deadlines = get_client_deadlines(_client_id, _sheets_svc, SPREADSHEET_ID) if _sheets_svc else []
        if deadlines:
            for dl in deadlines:
                st.markdown(f"""
                <div style="background:#fff8e0; padding:12px; border-radius:8px; margin:8px 0;
                            border-left:4px solid #F5A623;">
                    <strong>📅 {dl['date']}</strong><br>
                    {dl.get('description', '')}
                    <span style="color:#999;"> ({dl.get('category', '')})</span>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info("No upcoming deadlines.")

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; color:#999; font-size:13px;">
        <strong>US Immigration Group</strong><br>
        (847) 449-8660 | 800 E. Northwest Hwy. Ste 205, Mount Prospect, IL 60016<br>
        <em>This portal is for authorized clients only. Do not share your access code.</em>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# --- Init (only once per session, not every page reload) ---
if "sheets_initialized" not in st.session_state:
    st.session_state.sheets_initialized = False

if USE_GOOGLE_SHEETS:
    if is_sheets_configured():
        if is_sheets_authorized():
            if not st.session_state.sheets_initialized:
                try:
                    init_sheets()
                    seed_sample_clients()
                    st.session_state.sheets_initialized = True
                except Exception as e:
                    st.sidebar.error(f"Google Sheets connection error: {str(e)[:80]}")
                    st.sidebar.info("Try: Delete token.json and re-authorize.")
                    USE_GOOGLE_SHEETS = False
        else:
            st.sidebar.warning("Google Sheets: Not authorized. Go to Gmail Setup to authorize.")
else:
    if not st.session_state.sheets_initialized:
        init_sheets()
        migrate_db()
        seed_sample_clients()
        recalculate_all_balances()
        st.session_state.sheets_initialized = True

# --- Brand Colors ---
GOLD = "#F5A623"
NAVY = "#1A3C5E"
WHITE = "#FFFFFF"
BLACK = "#000000"

# --- Custom CSS ---
st.markdown(f"""
<style>
    .main-header {{ font-size: 2rem; font-weight: bold; color: {NAVY}; margin-bottom: 0; }}
    .sub-header {{ font-size: 1rem; color: #666; margin-top: -10px; }}
    .stMetric > div {{ background-color: #f8f9fa; padding: 15px; border-radius: 10px; border-left: 4px solid {GOLD}; }}
    .alert-red {{ background-color: #ffe0e0; padding: 12px; border-radius: 8px; border-left: 4px solid #cc0000; margin: 5px 0; }}
    .alert-yellow {{ background-color: #fff8e0; padding: 12px; border-radius: 8px; border-left: 4px solid {GOLD}; margin: 5px 0; }}
    .alert-green {{ background-color: #e0ffe0; padding: 12px; border-radius: 8px; border-left: 4px solid #00aa00; margin: 5px 0; }}
    .gold-banner {{ background: linear-gradient(135deg, {NAVY}, #2E5A8A); color: white; padding: 15px 20px; border-radius: 10px; border-bottom: 4px solid {GOLD}; margin-bottom: 15px; }}
</style>
""", unsafe_allow_html=True)

# --- Email Settings ---
if "email_mode" not in st.session_state:
    st.session_state.email_mode = "demo"
if "gmail_address" not in st.session_state:
    st.session_state.gmail_address = ""
if "gmail_app_password" not in st.session_state:
    st.session_state.gmail_app_password = ""

# --- Sidebar ---
st.sidebar.markdown("## ⚖️ US Immigration Group")
st.sidebar.markdown("**800 E. Northwest Hwy. Ste 205**")
st.sidebar.markdown("Mount Prospect, IL 60016")
st.sidebar.divider()

# Language selector
if "app_lang" not in st.session_state:
    st.session_state.app_lang = "en"
lang_options = list(LANGUAGE_NAMES.keys())
lang_labels = [f"🌐 {name}" for name in LANGUAGE_NAMES.values()]
lang_idx = lang_options.index(st.session_state.app_lang) if st.session_state.app_lang in lang_options else 0
selected_lang = st.sidebar.selectbox(
    "Language / 언어", lang_labels, index=lang_idx, key="lang_select"
)
st.session_state.app_lang = lang_options[lang_labels.index(selected_lang)]

_lang = st.session_state.app_lang

page = st.sidebar.radio(
    "Navigation",
    ["📊 " + t("nav_dashboard", _lang),
     "🧾 " + t("nav_invoice", _lang),
     "⚠️ " + t("nav_past_due", _lang),
     "💰 " + t("nav_payment", _lang),
     "🏦 " + t("nav_trust", _lang),
     "📁 " + t("nav_expenses", _lang),
     "👥 " + t("nav_clients", _lang),
     "📈 " + t("nav_reports", _lang),
     "📜 " + t("nav_audit", _lang),
     "💾 " + t("nav_backup", _lang),
     "🔍 " + t("nav_uscis", _lang),
     "⚖️ " + t("nav_court", _lang),
     "🌐 " + t("nav_portal", _lang),
     "🗓️ Calendar Sync",
     "✍️ e-Signature",
     "🤖 " + t("nav_ai", _lang),
     "⚙️ " + t("nav_gmail", _lang)],
    index=0
)

# Sidebar Email Settings
st.sidebar.divider()
with st.sidebar.expander("⚙️ Email Settings"):
    gmail_api_ready = is_gmail_api_configured() and is_gmail_api_authorized()
    mode_options = ["Demo (Preview Only)", "Gmail API (Create Drafts)", "SMTP (Send Emails)"]
    default_idx = 1 if gmail_api_ready else 0
    mode = st.radio("Mode", mode_options, index=default_idx, key="email_mode_radio")
    if "Gmail API" in mode:
        st.session_state.email_mode = "gmail_api"
        if gmail_api_ready:
            st.success("Gmail API connected")
        else:
            st.warning("Gmail API not authorized. Go to Gmail Setup page.")
    elif "SMTP" in mode:
        st.session_state.email_mode = "live"
        st.session_state.gmail_address = st.text_input("Gmail Address", key="gmail_addr")
        st.session_state.gmail_app_password = st.text_input("App Password", type="password", key="gmail_pw")
    else:
        st.session_state.email_mode = "demo"

st.sidebar.divider()
st.sidebar.caption("US Immigration Group")
st.sidebar.caption("v3.0 | April 2026")


def send_or_preview_email(recipient, subject, body, attachment_path=None,
                          client_id=None, invoice_id=None, email_type="invoice", is_html=False):
    """Send or preview email based on mode."""
    if st.session_state.email_mode == "gmail_api":
        success, msg = create_gmail_draft(recipient, subject, body, attachment_path)
        if success:
            log_email(client_id, invoice_id, f"{email_type}_draft", recipient, subject)
            if invoice_id:
                mark_invoice_sent(invoice_id)
        return success, msg
    elif st.session_state.email_mode == "live" and st.session_state.gmail_address:
        try:
            send_email_smtp(st.session_state.gmail_address, st.session_state.gmail_app_password,
                           recipient, subject, body, attachment_path, is_html=is_html)
            log_email(client_id, invoice_id, email_type, recipient, subject)
            if invoice_id:
                mark_invoice_sent(invoice_id)
            return True, "Email sent successfully!"
        except Exception as e:
            return False, f"Failed: {str(e)}"
    else:
        preview = simulate_send_email(recipient, subject, body, attachment_path)
        log_email(client_id, invoice_id, f"{email_type}_demo", recipient, subject)
        if invoice_id:
            mark_invoice_sent(invoice_id)
        return True, preview


# ==============================
# DASHBOARD
# ==============================
if page.startswith("📊"):  # Dashboard
    hdr_left, hdr_right = st.columns([5, 1])
    with hdr_left:
        st.markdown('<p class="main-header">Dashboard</p>', unsafe_allow_html=True)
        st.markdown('<p class="sub-header">US Immigration Group - Billing Overview</p>', unsafe_allow_html=True)
    with hdr_right:
        if st.button("🔄 Refresh", use_container_width=True, help="Refresh data from Google Sheets"):
            if USE_GOOGLE_SHEETS:
                invalidate_all_caches()
            st.rerun()
    st.divider()

    # --- Load all data ONCE for the entire dashboard ---
    clients = get_all_clients()
    all_invoices = get_invoices()
    all_payments = get_payments()

    stats = get_dashboard_stats()
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Active Clients", stats["total_clients"])
    col2.metric("Total Billed", f"${stats['total_billed']:,.2f}")
    col3.metric("Outstanding", f"${stats['outstanding']:,.2f}",
                delta=f"-${stats['outstanding']:,.2f}" if stats['outstanding'] > 0 else None,
                delta_color="inverse")
    col4.metric("Net Income", f"${stats['net_income']:,.2f}")

    # Trust Account
    st.divider()
    col_t1, col_t2 = st.columns([1, 3])
    with col_t1:
        st.metric("🏦 Trust Balance (IOLTA)", f"${stats['trust_balance']:,.2f}")

    # Alerts (use already-cached data — no extra API calls)
    past_due = get_past_due_invoices()
    retainer_alerts = get_retainer_alerts(60)
    expired_ret = get_expired_retainers()
    deadlines = get_upcoming_deadlines(14)

    if past_due or retainer_alerts or expired_ret or deadlines:
        st.divider()
        st.subheader("🔔 Active Alerts")
        alert_cols = st.columns(4)
        with alert_cols[0]:
            if past_due:
                total_past = sum(i["amount_due"] for i in past_due)
                st.markdown(f'<div class="alert-red"><strong>🚨 {len(past_due)} Past Due Invoices</strong><br>Total: ${total_past:,.2f}</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-green"><strong>✅ No Past Due</strong></div>', unsafe_allow_html=True)
        with alert_cols[1]:
            if deadlines:
                st.markdown(f'<div class="alert-yellow"><strong>📅 {len(deadlines)} Upcoming Deadlines</strong><br>Within 14 days</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-green"><strong>✅ No Urgent Deadlines</strong></div>', unsafe_allow_html=True)
        with alert_cols[2]:
            if retainer_alerts:
                st.markdown(f'<div class="alert-yellow"><strong>📋 {len(retainer_alerts)} Retainers Expiring</strong><br>Within 60 days</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-green"><strong>✅ Retainers Current</strong></div>', unsafe_allow_html=True)
        with alert_cols[3]:
            if expired_ret:
                st.markdown(f'<div class="alert-red"><strong>⚠️ {len(expired_ret)} Expired Retainers</strong><br>Need attention</div>', unsafe_allow_html=True)
            else:
                st.markdown('<div class="alert-green"><strong>✅ No Expired</strong></div>', unsafe_allow_html=True)

    st.divider()
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.subheader("Client Billing Summary")
        if clients:
            client_data = []
            for c in clients:
                unpaid = sum(inv["amount_due"] for inv in all_invoices
                             if inv["client_id"] == c["id"] and inv.get("status") != "Paid")
                total_paid = sum(p["amount"] for p in all_payments
                                 if p["client_id"] == c["id"])
                client_data.append({
                    "Client": c["name"],
                    "Case": c["case_number"] or "-",
                    "Type": c["visa_type"] or "-",
                    "Outstanding": unpaid,
                    "Total Paid": total_paid,
                })
            df = pd.DataFrame(client_data)
            st.dataframe(df.style.format({"Outstanding": "${:,.2f}", "Total Paid": "${:,.2f}"}),
                         use_container_width=True, hide_index=True)

    with col_right:
        st.subheader("Revenue by Client")
        if clients:
            rev_data = []
            for c in clients:
                paid = sum(p["amount"] for p in all_payments if p["client_id"] == c["id"])
                if paid > 0:
                    rev_data.append({"Client": c["name"][:20], "Revenue": paid})
            if rev_data:
                chart_df = pd.DataFrame(rev_data).set_index("Client")
                st.bar_chart(chart_df)

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        st.subheader("Recent Payments")
        if all_payments:
            pay_df = pd.DataFrame(all_payments[:8])
            cols = ["date_received", "client_name", "amount", "payment_method", "notes"]
            avail = [c for c in cols if c in pay_df.columns]
            st.dataframe(pay_df[avail].rename(columns={
                "date_received": "Date", "client_name": "Client",
                "amount": "Amount", "payment_method": "Method", "notes": "Notes"
            }).style.format({"Amount": "${:,.2f}"}), use_container_width=True, hide_index=True)
        else:
            st.info("No payments recorded yet.")

    with col_b:
        st.subheader("Upcoming Deadlines")
        deadlines_30 = get_upcoming_deadlines(30)  # uses cache, no extra API call
        if deadlines_30:
            dl_data = [{
                "Client": d["client_name"],
                "Case": d["case_number"] or "-",
                "Deadline": d.get("category", ""),
                "Date": d["deadline_date"],
                "Description": d["description"] or "",
            } for d in deadlines_30]
            st.dataframe(pd.DataFrame(dl_data), use_container_width=True, hide_index=True)
        else:
            st.info("No upcoming deadlines in the next 30 days.")


# ==============================
# INVOICE & EMAIL
# ==============================
elif page.startswith("🧾"):  # Invoice & Email
    st.markdown('<p class="main-header">Invoice Generation & Email</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Generate legal invoices and send via email</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["📝 Generate Invoice", "📦 Batch Invoices", "📋 Invoice History", "📧 Email Log"])

    with tab1:
        st.subheader("Generate Single Invoice")
        clients = get_all_clients()
        if not clients:
            st.warning("No clients found. Add clients first in 'Clients & Cases'.")
        else:
            client_options = {f"{c['name']} ({c['case_number'] or 'No Case#'})": c for c in clients}
            selected_key = st.selectbox("Select Client", list(client_options.keys()))
            selected = client_options[selected_key]

            col1, col2 = st.columns(2)
            with col1:
                inv_date = st.date_input("Invoice Date", value=date.today(), key="si_date")
                due_date = st.date_input("Due Date", value=date.today() + timedelta(days=30), key="si_due")
                description = st.text_input("Matter Description",
                    value=f"{selected.get('visa_type', '')} — {selected.get('case_type', 'Legal Services')}",
                    key="si_desc")
            with col2:
                legal_fees = st.number_input("Legal Fees ($)", value=float(selected.get("retainer_amount", 0)), format="%.2f", key="si_legal")
                filing_fees = st.number_input("USCIS Filing Fees ($)", value=0.0, format="%.2f", key="si_filing")
                other_expenses = st.number_input("Other Expenses ($)", value=0.0, format="%.2f", key="si_other")
                retainer_applied = st.number_input("Retainer Applied ($)", value=0.0, format="%.2f", key="si_retainer")

            total = legal_fees + filing_fees + other_expenses
            amount_due = total - retainer_applied
            st.info(f"💵 Total: **${total:,.2f}** | Retainer Applied: **${retainer_applied:,.2f}** | **Amount Due: ${amount_due:,.2f}**")

            notes = st.text_area("Invoice Notes", height=60, key="si_notes")

            inv_format = st.radio("Invoice Format", ["Excel (.xlsx)", "PDF (.pdf)"] if HAS_PDF else ["Excel (.xlsx)"],
                                  horizontal=True, key="inv_format")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📄 Generate Invoice", type="primary", use_container_width=True):
                    inv_num = create_invoice(
                        client_id=selected["id"], invoice_date=inv_date, due_date=due_date,
                        description=description, legal_fees=legal_fees, filing_fees=filing_fees,
                        other_expenses=other_expenses, retainer_applied=retainer_applied, notes=notes)
                    filepath = generate_invoice_excel(
                        client=dict(selected), invoice_number=inv_num,
                        invoice_date=inv_date, due_date=due_date, description=description,
                        legal_fees=legal_fees, filing_fees=filing_fees,
                        other_expenses=other_expenses, retainer_applied=retainer_applied)
                    st.success(f"✅ Invoice #{inv_num} generated!")
                    # Upload to Google Drive
                    if HAS_DRIVE and USE_GOOGLE_SHEETS:
                        try:
                            drive_result = upload_invoice(filepath, selected["name"], selected.get("case_number", ""))
                            if drive_result:
                                st.success(f"☁️ Uploaded to Google Drive!")
                                st.markdown(f"[📂 View in Drive]({drive_result['link']})")
                        except Exception as e:
                            st.warning(f"Drive upload failed: {e}")
                    with open(filepath, "rb") as f:
                        st.download_button("📥 Download Invoice", data=f.read(),
                                           file_name=os.path.basename(filepath),
                                           mime=mime_type)
            with c2:
                if st.button("📧 Generate & Email", use_container_width=True):
                    if not selected.get("email"):
                        st.error("No email address for this client.")
                    else:
                        inv_num = create_invoice(
                            client_id=selected["id"], invoice_date=inv_date, due_date=due_date,
                            description=description, legal_fees=legal_fees, filing_fees=filing_fees,
                            other_expenses=other_expenses, retainer_applied=retainer_applied, notes=notes)
                        filepath = generate_invoice_excel(
                            client=dict(selected), invoice_number=inv_num,
                            invoice_date=inv_date, due_date=due_date, description=description,
                            legal_fees=legal_fees, filing_fees=filing_fees,
                            other_expenses=other_expenses, retainer_applied=retainer_applied)
                        subject, html_body = build_invoice_email_html(
                            selected["name"], inv_num, description, total, amount_due,
                            due_date.strftime("%B %d, %Y"), selected.get("case_number", ""))
                        invs = get_invoices(client_id=selected["id"])
                        inv_id = invs[0]["id"] if invs else None
                        success, msg = send_or_preview_email(
                            selected["email"], subject, html_body, filepath,
                            client_id=selected["id"], invoice_id=inv_id, is_html=True)
                        if success:
                            st.success("✅ Invoice generated and email sent!")
                            if st.session_state.email_mode == "demo":
                                st.code(msg)

    with tab2:
        st.subheader("Batch Invoice Generation")
        clients = get_all_clients()
        if clients:
            st.markdown("#### Select Clients")
            select_all = st.checkbox("Select All", value=True, key="batch_all")
            selected_clients = []
            cols_per_row = 3
            for i in range(0, len(clients), cols_per_row):
                row_clients = clients[i:i + cols_per_row]
                cols = st.columns(cols_per_row)
                for j, c in enumerate(row_clients):
                    email_status = "✅" if c["email"] else "❌"
                    label = f"{c['name']} ({c['visa_type'] or '-'}) {email_status}"
                    checked = cols[j].checkbox(label, value=select_all, key=f"bsel_{c['id']}")
                    if checked:
                        selected_clients.append(c)

            batch_desc = st.text_input("Invoice Description", value="Legal Services", key="batch_desc")
            batch_fee = st.number_input("Default Legal Fee ($)", value=0.0, format="%.2f", key="batch_fee")

            if st.button("📄 Generate Batch Invoices", type="primary", use_container_width=True):
                if not selected_clients:
                    st.warning("No clients selected.")
                else:
                    results = []
                    for c in selected_clients:
                        fee = batch_fee if batch_fee > 0 else c.get("retainer_amount", 0)
                        if fee <= 0:
                            continue
                        inv_num = create_invoice(
                            client_id=c["id"], invoice_date=date.today(),
                            due_date=date.today() + timedelta(days=30),
                            description=batch_desc, legal_fees=fee)
                        filepath = generate_invoice_excel(
                            client=dict(c), invoice_number=inv_num,
                            invoice_date=date.today(), due_date=date.today() + timedelta(days=30),
                            description=batch_desc, legal_fees=fee)
                        results.append((c["name"], inv_num, filepath))
                    st.success(f"✅ {len(results)} invoices generated!")
                    for name, inv_num, filepath in results:
                        c1, c2, c3 = st.columns([3, 2, 2])
                        c1.write(f"**{name}**")
                        c2.write(f"#{inv_num}")
                        with open(filepath, "rb") as f:
                            c3.download_button("📥", data=f.read(),
                                               file_name=os.path.basename(filepath),
                                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                               key=f"bdl_{inv_num}")

    with tab3:
        st.subheader("Invoice History")
        fc1, fc2 = st.columns(2)
        with fc1:
            ft = st.selectbox("Client", ["All"] + [c["name"] for c in get_all_clients()], key="ih_c")
        with fc2:
            fs = st.selectbox("Status", ["All", "Unpaid", "Paid", "Partial"], key="ih_s")
        cid = None
        if ft != "All":
            for c in get_all_clients():
                if c["name"] == ft:
                    cid = c["id"]
                    break
        invoices = get_invoices(client_id=cid, status=fs if fs != "All" else None)
        if invoices:
            inv_df = pd.DataFrame(invoices)
            cols = ["invoice_number", "client_name", "description", "legal_fees", "filing_fees",
                    "total_amount", "retainer_applied", "amount_due", "status", "sent_at"]
            avail = [c for c in cols if c in inv_df.columns]
            if "sent_at" in inv_df.columns:
                inv_df["sent_at"] = inv_df["sent_at"].apply(lambda x: "✅" if x else "❌")
            st.dataframe(inv_df[avail].rename(columns={
                "invoice_number": "Invoice #", "client_name": "Client", "description": "Matter",
                "legal_fees": "Legal Fees", "filing_fees": "Filing Fees",
                "total_amount": "Total", "retainer_applied": "Retainer",
                "amount_due": "Due", "status": "Status", "sent_at": "Sent"
            }).style.format({"Legal Fees": "${:,.2f}", "Filing Fees": "${:,.2f}",
                            "Total": "${:,.2f}", "Retainer": "${:,.2f}", "Due": "${:,.2f}"}),
                use_container_width=True, hide_index=True)
        else:
            st.info("No invoices found.")

    with tab4:
        st.subheader("Email Log")
        emails = get_email_log()
        if emails:
            em_df = pd.DataFrame(emails)
            cols = ["sent_at", "client_name", "email_type", "recipient", "subject"]
            avail = [c for c in cols if c in em_df.columns]
            st.dataframe(em_df[avail].rename(columns={
                "sent_at": "Date", "client_name": "Client", "email_type": "Type",
                "recipient": "To", "subject": "Subject"
            }), use_container_width=True, hide_index=True)
        else:
            st.info("No emails sent yet.")


# ==============================
# PAST DUE & ALERTS
# ==============================
elif page.startswith("⚠️"):  # Past Due & Alerts
    st.markdown('<p class="main-header">Past Due & Case Alerts</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2, tab3, tab4 = st.tabs(["🚨 Past Due", "📅 Case Deadlines", "📋 Retainer Status", "📧 Send Reminders"])

    with tab1:
        past_due = get_past_due_invoices()
        if past_due:
            total_overdue = sum(i["amount_due"] for i in past_due)
            st.error(f"🚨 **{len(past_due)} invoices** totaling **${total_overdue:,.2f}** are past due!")
            pd_data = [{
                "Client": inv["client_name"],
                "Invoice #": inv["invoice_number"],
                "Case": inv.get("case_number", "-"),
                "Amount Due": inv["amount_due"],
                "Due Date": inv["due_date"],
                "Days Overdue": inv["days_overdue"],
                "Email": inv.get("client_email") or "N/A",
            } for inv in past_due]
            st.dataframe(pd.DataFrame(pd_data).style.format({"Amount Due": "${:,.2f}"}).background_gradient(
                subset=["Days Overdue"], cmap="Reds"),
                use_container_width=True, hide_index=True)
        else:
            st.success("✅ No past due invoices!")

    with tab2:
        st.subheader("Case Deadlines")
        # Add new deadline
        with st.expander("➕ Add New Deadline"):
            clients = get_all_clients()
            if clients:
                dl_client = st.selectbox("Client", [c["name"] for c in clients], key="dl_client")
                dl_type = st.selectbox("Deadline Type", [
                    "USCIS Filing Deadline", "RFE Response Due", "Court Hearing",
                    "Document Submission", "Interview Date", "Appeal Deadline",
                    "Brief Due Date", "Biometrics Appointment", "Other"
                ], key="dl_type")
                dl_date = st.date_input("Deadline Date", key="dl_date")
                dl_desc = st.text_input("Description", key="dl_desc")
                if st.button("Add Deadline", type="primary"):
                    cid = next(c["id"] for c in clients if c["name"] == dl_client)
                    add_deadline(cid, dl_date.isoformat(), dl_desc, category=dl_type)
                    st.success("✅ Deadline added!")
                    st.rerun()

        deadlines = get_upcoming_deadlines(90)
        if deadlines:
            for d in deadlines:
                days = (date.fromisoformat(d["deadline_date"]) - date.today()).days
                icon = "🔴" if days <= 7 else ("🟡" if days <= 30 else "🟢")
                col1, col2, col3 = st.columns([4, 1, 1])
                col1.write(f"{icon} **{d['client_name']}** — {d['deadline_type']}: {d['deadline_date']} ({days}d) — {d.get('description', '')}")
                if col2.button("✅ Done", key=f"dl_done_{d['id']}"):
                    complete_deadline(d["id"])
                    st.rerun()
        else:
            st.info("No upcoming deadlines.")

    with tab3:
        st.subheader("Retainer Agreement Status")
        expired = get_expired_retainers()
        if expired:
            st.error(f"⚠️ {len(expired)} expired retainers!")
            exp_data = [{
                "Client": c["name"], "Case": c["case_number"] or "-",
                "Retainer End": c["retainer_end"], "Days Expired": c["days_expired"],
                "Amount": c["retainer_amount"]
            } for c in expired]
            st.dataframe(pd.DataFrame(exp_data).style.format({"Amount": "${:,.2f}"}),
                         use_container_width=True, hide_index=True)

        alerts = get_retainer_alerts(90)
        if alerts:
            st.warning(f"📋 {len(alerts)} retainers expiring within 90 days")
            alert_data = [{
                "Client": c["name"], "Case": c["case_number"] or "-",
                "Retainer End": c["retainer_end"], "Days Remaining": c["days_remaining"],
                "Amount": c["retainer_amount"]
            } for c in alerts]
            st.dataframe(pd.DataFrame(alert_data).style.format({"Amount": "${:,.2f}"}),
                         use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("All Retainer Agreements")
        all_clients = get_all_clients()
        ret_data = [{
            "Client": c["name"], "Case": c["case_number"] or "-",
            "Type": c["visa_type"] or "-",
            "Start": c["retainer_date"] or "N/A", "End": c["retainer_end"] or "N/A",
            "Amount": c["retainer_amount"]
        } for c in all_clients]
        st.dataframe(pd.DataFrame(ret_data).style.format({"Amount": "${:,.2f}"}),
                     use_container_width=True, hide_index=True)

    with tab4:
        st.subheader("Send Reminder Emails")
        reminder_type = st.radio("Type", ["Past Due Reminders", "Deadline Reminders"])

        if reminder_type == "Past Due Reminders":
            past_due = get_past_due_invoices()
            if not past_due:
                st.success("No past due invoices.")
            else:
                client_invoices = {}
                for inv in past_due:
                    cid = inv["client_id"]
                    if cid not in client_invoices:
                        client_invoices[cid] = {"name": inv["client_name"], "email": inv.get("client_email"), "invoices": []}
                    client_invoices[cid]["invoices"].append(inv)

                for cid, info in client_invoices.items():
                    total = sum(i["amount_due"] for i in info["invoices"])
                    st.write(f"- **{info['name']}**: ${total:,.2f} ({len(info['invoices'])} inv) — {info['email'] or 'NO EMAIL'}")

                if st.button("📧 Send All Reminders", type="primary", use_container_width=True):
                    sent = 0
                    for cid, info in client_invoices.items():
                        if not info["email"]:
                            continue
                        subject, body = build_past_due_email(info["name"], info["invoices"])
                        success, msg = send_or_preview_email(info["email"], subject, body, client_id=cid, email_type="past_due")
                        if success:
                            sent += 1
                            if st.session_state.email_mode == "demo":
                                with st.expander(f"Preview: {info['name']}"):
                                    st.code(msg)
                    st.success(f"✅ {sent} reminders sent!")


# ==============================
# PAYMENT TRACKING
# ==============================
elif page.startswith("💰"):  # Payment Tracking
    st.markdown('<p class="main-header">Payment Tracking</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2 = st.tabs(["➕ Record Payment", "📋 Payment History"])

    with tab1:
        clients = get_all_clients()
        if not clients:
            st.warning("No clients found.")
        else:
            client_options = {c["name"]: c for c in clients}
            selected_name = st.selectbox("Client", list(client_options.keys()), key="pay_client")
            selected = client_options[selected_name]

            unpaid = list(get_invoices(client_id=selected["id"], status="Unpaid"))
            partial = list(get_invoices(client_id=selected["id"], status="Partial"))
            all_unpaid = unpaid + partial

            invoice_options = {"None (General Payment)": None}
            for inv in all_unpaid:
                label = f"#{inv['invoice_number']} — ${inv['amount_due']:,.2f} ({inv['status']})"
                invoice_options[label] = inv["id"]

            col1, col2 = st.columns(2)
            with col1:
                pay_date = st.date_input("Date Received", value=date.today(), key="pay_date")
                pay_amount = st.number_input("Amount ($)", value=0.0, format="%.2f", key="pay_amt")
                pay_method = st.selectbox("Method", ["Check", "Zelle", "Wire Transfer", "Cash", "Credit Card"], key="pay_meth")
            with col2:
                selected_invoice = st.selectbox("Apply to Invoice", list(invoice_options.keys()), key="pay_inv")
                pay_check = st.text_input("Check/Reference #", key="pay_chk")
                deposit_to = st.selectbox("Deposit To", ["Operating Account", "Trust Account (IOLTA)"], key="pay_dep")
                pay_notes = st.text_input("Notes", key="pay_notes")

            if st.button("💰 Record Payment", type="primary", use_container_width=True):
                dep_acct = "Trust" if "Trust" in deposit_to else "Operating"
                record_payment(client_id=selected["id"], invoice_id=invoice_options[selected_invoice],
                              date_received=pay_date.isoformat(), amount=pay_amount,
                              check_number=pay_check, payment_method=pay_method,
                              deposit_to=dep_acct, notes=pay_notes)
                if dep_acct == "Trust":
                    trust_deposit(selected["id"], pay_amount,
                                 f"Payment — {pay_method}", pay_check)
                st.success(f"✅ Payment of ${pay_amount:,.2f} recorded for {selected_name} → {dep_acct}")
                st.rerun()

    with tab2:
        filter_client = st.selectbox("Filter", ["All"] + [c["name"] for c in get_all_clients()], key="ph_c")
        cid = None
        if filter_client != "All":
            for c in get_all_clients():
                if c["name"] == filter_client:
                    cid = c["id"]
                    break
        payments = get_payments(client_id=cid)
        if payments:
            pay_df = pd.DataFrame(payments)
            cols = ["date_received", "client_name", "amount", "payment_method", "check_number", "invoice_number", "deposit_to", "notes"]
            avail = [c for c in cols if c in pay_df.columns]
            st.dataframe(pay_df[avail].rename(columns={
                "date_received": "Date", "client_name": "Client", "amount": "Amount",
                "payment_method": "Method", "check_number": "Ref #",
                "invoice_number": "Invoice", "deposit_to": "Account", "notes": "Notes"
            }).style.format({"Amount": "${:,.2f}"}), use_container_width=True, hide_index=True)
            st.success(f"💵 Total: **${sum(p['amount'] for p in payments):,.2f}**")
        else:
            st.info("No payments recorded.")


# ==============================
# TRUST ACCOUNT (IOLTA)
# ==============================
elif page.startswith("🏦"):  # Trust Account (IOLTA)
    st.markdown('<p class="main-header">Trust Account (IOLTA)</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Client trust fund management — IRPC Rule 1.15 compliant</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2, tab3 = st.tabs(["💰 Deposit / Withdrawal", "📋 Transaction History", "📊 Client Balances"])

    with tab1:
        clients = get_all_clients()
        if not clients:
            st.warning("No clients found.")
        else:
            client_options = {c["name"]: c for c in clients}
            tr_client = st.selectbox("Client", list(client_options.keys()), key="tr_client")
            tr_selected = client_options[tr_client]
            current_bal = get_trust_balance(tr_selected["id"])
            st.metric("Current Trust Balance", f"${current_bal:,.2f}")

            col1, col2 = st.columns(2)
            with col1:
                tr_type = st.radio("Transaction", ["Deposit", "Withdrawal"], key="tr_type")
                tr_date = st.date_input("Date", value=date.today(), key="tr_date")
            with col2:
                tr_amount = st.number_input("Amount ($)", value=0.0, format="%.2f", key="tr_amt")
                tr_desc = st.text_input("Description", key="tr_desc")
                tr_ref = st.text_input("Reference #", key="tr_ref")

            if st.button(f"{'💰 Deposit' if tr_type == 'Deposit' else '💸 Withdraw'}", type="primary", use_container_width=True):
                if tr_type == "Deposit":
                    trust_deposit(tr_selected["id"], tr_amount, tr_desc, tr_ref)
                    new_bal = get_trust_balance(tr_selected["id"])
                    st.success(f"✅ Deposit of ${tr_amount:,.2f} recorded. New balance: ${new_bal:,.2f}")
                    st.rerun()
                else:
                    if tr_amount > current_bal:
                        st.error("⚠️ Insufficient trust balance!")
                    else:
                        trust_withdrawal(tr_selected["id"], tr_amount, tr_desc, tr_ref)
                        new_bal = get_trust_balance(tr_selected["id"])
                        st.success(f"✅ Withdrawal of ${tr_amount:,.2f} recorded. New balance: ${new_bal:,.2f}")
                        st.rerun()

    with tab2:
        filter_cl = st.selectbox("Client", ["All"] + [c["name"] for c in get_all_clients()], key="trhist_c")
        cid = None
        if filter_cl != "All":
            for c in get_all_clients():
                if c["name"] == filter_cl:
                    cid = c["id"]
                    break
        transactions = get_trust_transactions(client_id=cid)
        if transactions:
            tr_df = pd.DataFrame(transactions)
            cols = ["date", "client_name", "transaction_type", "amount", "balance_after", "description", "reference"]
            avail = [c for c in cols if c in tr_df.columns]
            st.dataframe(tr_df[avail].rename(columns={
                "date": "Date", "client_name": "Client", "transaction_type": "Type",
                "amount": "Amount", "balance_after": "Balance", "description": "Description", "reference": "Ref"
            }).style.format({"Amount": "${:,.2f}", "Balance": "${:,.2f}"}),
                use_container_width=True, hide_index=True)
        else:
            st.info("No trust transactions recorded.")

    with tab3:
        st.subheader("Trust Balance by Client")
        clients = get_all_clients()
        bal_data = []
        for c in clients:
            bal = get_trust_balance(c["id"])
            bal_data.append({"Client": c["name"], "Case": c["case_number"] or "-", "Trust Balance": bal})
        total_trust = sum(d["Trust Balance"] for d in bal_data)
        st.metric("Total Trust Funds", f"${total_trust:,.2f}")
        st.dataframe(pd.DataFrame(bal_data).style.format({"Trust Balance": "${:,.2f}"}),
                     use_container_width=True, hide_index=True)


# ==============================
# EXPENSES
# ==============================
elif page.startswith("📁"):  # Expenses
    st.markdown('<p class="main-header">Expense Management</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2 = st.tabs(["➕ Add Expense", "📋 Expense History"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            exp_date = st.date_input("Date", value=date.today(), key="exp_d")
            exp_category = st.selectbox("Category", [
                "USCIS Filing Fees", "Translation Services", "Document Delivery/Postage",
                "Court Filing Fees", "Expert Witness Fees", "Travel Expenses",
                "Office Supplies", "Software/Technology", "Professional Development",
                "Malpractice Insurance", "Rent/Utilities", "Other"
            ], key="exp_c")
            exp_vendor = st.text_input("Vendor/Payee", key="exp_v")
        with col2:
            exp_amount = st.number_input("Amount ($)", value=0.0, format="%.2f", key="exp_a")
            clients = get_all_clients()
            client_options = {"(Firm Expense - No Client)": None}
            for c in clients:
                client_options[c["name"]] = c["id"]
            exp_client = st.selectbox("Bill to Client", list(client_options.keys()), key="exp_cl")
            exp_billable = st.checkbox("Billable to Client", value=True, key="exp_bill")
        exp_desc = st.text_input("Description", key="exp_desc")
        exp_notes = st.text_area("Notes", height=60, key="exp_n")

        if st.button("💳 Record Expense", type="primary", use_container_width=True):
            add_expense(date_str=exp_date.isoformat(), category=exp_category, vendor=exp_vendor,
                       description=exp_desc, amount=exp_amount, client_id=client_options[exp_client],
                       is_billable=1 if exp_billable else 0, notes=exp_notes)
            st.success(f"✅ Expense of ${exp_amount:,.2f} recorded!")
            st.rerun()

    with tab2:
        fc1, fc2, fc3 = st.columns(3)
        with fc1:
            f_cat = st.selectbox("Category", ["All"] + [
                "USCIS Filing Fees", "Translation Services", "Document Delivery/Postage",
                "Court Filing Fees", "Office Supplies", "Rent/Utilities", "Other"
            ], key="eh_c")
        with fc2:
            f_start = st.date_input("From", value=date(date.today().year, 1, 1), key="eh_s")
        with fc3:
            f_end = st.date_input("To", value=date.today(), key="eh_e")

        expenses = get_expenses(category=f_cat if f_cat != "All" else None,
                               start_date=f_start.isoformat(), end_date=f_end.isoformat())
        if expenses:
            exp_df = pd.DataFrame(expenses)
            cols = ["date", "category", "vendor", "client_name", "description", "amount", "is_billable"]
            avail = [c for c in cols if c in exp_df.columns]
            if "is_billable" in exp_df.columns:
                exp_df["is_billable"] = exp_df["is_billable"].apply(lambda x: "✅" if x else "")
            if "client_name" in exp_df.columns:
                exp_df["client_name"] = exp_df["client_name"].fillna("(Firm)")
            st.dataframe(exp_df[avail].rename(columns={
                "date": "Date", "category": "Category", "vendor": "Vendor",
                "client_name": "Client", "description": "Description",
                "amount": "Amount", "is_billable": "Billable"
            }).style.format({"Amount": "${:,.2f}"}), use_container_width=True, hide_index=True)
            st.success(f"💵 Total: **${sum(e['amount'] for e in expenses):,.2f}**")
        else:
            st.info("No expenses found.")


# ==============================
# CLIENTS & CASES
# ==============================
elif page.startswith("👥"):  # Clients & Cases
    st.markdown('<p class="main-header">Client & Case Management</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2, tab3 = st.tabs(["👥 All Clients", "➕ Add Client", "📝 Edit Client"])

    with tab1:
        clients = get_all_clients(active_only=False)
        if clients:
            cl_data = [{
                "Status": "🟢" if c["is_active"] else "🔴",
                "Name": c["name"],
                "Korean": c.get("name_korean") or "",
                "Case #": c["case_number"] or "-",
                "Type": c["visa_type"] or "-",
                "Category": c["case_type"] or "-",
                "Email": c["email"] or "-",
                "Phone": c["phone"] or "-",
                "Retainer": c["retainer_amount"],
                "Balance": c["balance"],
            } for c in clients]
            st.dataframe(pd.DataFrame(cl_data).style.format({"Retainer": "${:,.2f}", "Balance": "${:,.2f}"}),
                         use_container_width=True, hide_index=True)
        else:
            st.info("No clients found.")

    with tab2:
        st.subheader("Add New Client")
        col1, col2 = st.columns(2)
        with col1:
            new_name = st.text_input("Full Name (English)*", key="nc_name")
            new_korean = st.text_input("Name (Korean)", key="nc_kr")
            new_email = st.text_input("Email", key="nc_email")
            new_phone = st.text_input("Phone", key="nc_phone")
            new_address = st.text_input("Address", key="nc_addr")
        with col2:
            new_case_type = st.selectbox("Case Category", [
                "Employment-Based", "Family-Based", "Humanitarian",
                "Naturalization", "Removal Defense", "Other"
            ], key="nc_ctype")
            new_visa = st.text_input("Visa Type (e.g., H-1B, EB-2)", key="nc_visa")
            new_case_num = st.text_input("Case Number", key="nc_cnum")
            new_retainer = st.number_input("Retainer Amount ($)", value=0.0, format="%.2f", key="nc_ret")
            new_ret_date = st.date_input("Retainer Start", key="nc_rdate")
            new_ret_end = st.date_input("Retainer End", value=date.today() + timedelta(days=365), key="nc_rend")

        new_notes = st.text_area("Notes", key="nc_notes")

        if st.button("➕ Add Client", type="primary", use_container_width=True):
            if not new_name:
                st.error("Name is required.")
            else:
                add_client(name=new_name, name_korean=new_korean, email=new_email,
                          phone=new_phone, address=new_address, case_type=new_case_type,
                          visa_type=new_visa, case_number=new_case_num,
                          retainer_amount=new_retainer,
                          retainer_date=new_ret_date.isoformat(),
                          retainer_end=new_ret_end.isoformat(),
                          notes=new_notes)
                st.success(f"✅ Client '{new_name}' added!")
                st.rerun()

    with tab3:
        clients = get_all_clients(active_only=False)
        if clients:
            edit_options = {c["name"]: c for c in clients}
            edit_name = st.selectbox("Select Client to Edit", list(edit_options.keys()), key="ec_sel")
            ec = edit_options[edit_name]

            col1, col2 = st.columns(2)
            with col1:
                e_name = st.text_input("Name", value=ec["name"], key="ec_name")
                e_korean = st.text_input("Korean Name", value=ec.get("name_korean") or "", key="ec_kr")
                e_email = st.text_input("Email", value=ec.get("email") or "", key="ec_email")
                e_phone = st.text_input("Phone", value=ec.get("phone") or "", key="ec_phone")
            with col2:
                e_visa = st.text_input("Visa Type", value=ec.get("visa_type") or "", key="ec_visa")
                e_case_num = st.text_input("Case Number", value=ec.get("case_number") or "", key="ec_cnum")
                e_retainer = st.number_input("Retainer ($)", value=float(ec.get("retainer_amount") or 0), format="%.2f", key="ec_ret")
                e_active = st.checkbox("Active", value=bool(ec.get("is_active", 1)), key="ec_active")

            if st.button("💾 Save Changes", type="primary", use_container_width=True):
                update_client(ec["id"], name=e_name, name_korean=e_korean,
                            email=e_email, phone=e_phone, visa_type=e_visa,
                            case_number=e_case_num, retainer_amount=e_retainer,
                            is_active=1 if e_active else 0)
                st.success(f"✅ Client '{e_name}' updated!")
                st.rerun()


# ==============================
# REPORTS & P&L
# ==============================
elif page.startswith("📈"):  # Reports & P&L
    st.markdown('<p class="main-header">Reports & P&L</p>', unsafe_allow_html=True)
    st.divider()

    tab1, tab2 = st.tabs(["📊 Monthly P&L", "📈 Annual Summary"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            r_month = st.selectbox("Month", list(range(1, 13)), index=date.today().month - 1,
                                   format_func=lambda m: calendar.month_name[m], key="pnl_m")
        with col2:
            r_year = st.number_input("Year", min_value=2024, max_value=2030, value=date.today().year, key="pnl_y")

        pnl = get_monthly_pnl(r_year, r_month)
        month_name = calendar.month_name[r_month]

        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.metric(f"Invoiced ({month_name})", f"${pnl['invoiced']:,.2f}")
        col_b.metric("Collected", f"${pnl['income']:,.2f}")
        col_c.metric("Expenses", f"${pnl['expenses']:,.2f}")
        col_d.metric("Net Income", f"${pnl['net']:,.2f}",
                     delta=f"${pnl['net']:,.2f}" if pnl['net'] != 0 else None)

        st.divider()
        col_left, col_right = st.columns(2)

        with col_left:
            st.subheader("Payment Details")
            if pnl["payment_details"]:
                pay_df = pd.DataFrame(pnl["payment_details"])
                st.dataframe(pay_df.rename(columns={
                    "date_received": "Date", "client_name": "Client",
                    "amount": "Amount", "payment_method": "Method"
                }).style.format({"Amount": "${:,.2f}"}), use_container_width=True, hide_index=True)
            else:
                st.info("No payments this month.")

        with col_right:
            st.subheader("Expense Breakdown")
            if pnl["expense_breakdown"]:
                exp_df = pd.DataFrame(pnl["expense_breakdown"])
                st.dataframe(exp_df.rename(columns={"category": "Category", "total": "Amount"})
                            .style.format({"Amount": "${:,.2f}"}),
                            use_container_width=True, hide_index=True)
                chart_df = pd.DataFrame(pnl["expense_breakdown"]).set_index("category")
                st.bar_chart(chart_df)
            else:
                st.info("No expenses this month.")

    with tab2:
        st.subheader("Annual Summary")
        a_year = st.number_input("Year", min_value=2024, max_value=2030, value=date.today().year, key="ann_y")
        monthly_data = []
        for m in range(1, 13):
            pnl = get_monthly_pnl(a_year, m)
            monthly_data.append({
                "Month": calendar.month_abbr[m],
                "Invoiced": pnl["invoiced"],
                "Collected": pnl["income"],
                "Expenses": pnl["expenses"],
                "Net": pnl["net"],
            })
        ann_df = pd.DataFrame(monthly_data)
        st.dataframe(ann_df.style.format({
            "Invoiced": "${:,.2f}", "Collected": "${:,.2f}",
            "Expenses": "${:,.2f}", "Net": "${:,.2f}"
        }), use_container_width=True, hide_index=True)

        totals = ann_df[["Invoiced", "Collected", "Expenses", "Net"]].sum()
        col1, col2, col3, col4 = st.columns(4)
        col1.metric(f"Total Invoiced ({a_year})", f"${totals['Invoiced']:,.2f}")
        col2.metric("Total Collected", f"${totals['Collected']:,.2f}")
        col3.metric("Total Expenses", f"${totals['Expenses']:,.2f}")
        col4.metric("Annual Net", f"${totals['Net']:,.2f}")

        st.divider()
        chart_df = ann_df.set_index("Month")[["Collected", "Expenses"]]
        st.line_chart(chart_df)


# ==============================
# AI ASSISTANT
# ==============================

elif page.startswith("📜"):  # Audit Log
    st.markdown('<p class="main-header">Audit Log</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">System activity tracking for compliance</p>', unsafe_allow_html=True)
    st.divider()

    if not USE_GOOGLE_SHEETS:
        st.info("Audit Log is available in Google Sheets mode only.")
    else:
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            filter_type = st.selectbox("Entity Type", ["All", "invoice", "payment", "client", "balance", "system", "backup_export", "backup_excel", "backup_upload"])
        with col_f2:
            filter_id = st.text_input("Entity ID (optional)")
        with col_f3:
            limit = st.number_input("Max Records", value=50, min_value=10, max_value=500, step=10)

        entity_type = None if filter_type == "All" else filter_type
        entity_id = filter_id if filter_id else None
        logs = get_audit_log(entity_type=entity_type, entity_id=entity_id, limit=limit)

        if logs:
            import pandas as pd
            log_data = []
            for l in logs:
                log_data.append({
                    "Timestamp": l.get("timestamp", "")[:19].replace("T", " "),
                    "User": l.get("user", "system"),
                    "Action": l.get("action", ""),
                    "Type": l.get("entity_type", ""),
                    "Entity ID": l.get("entity_id", ""),
                    "Field": l.get("field_changed", ""),
                    "Old Value": l.get("old_value", "")[:30],
                    "New Value": l.get("new_value", "")[:30],
                    "Details": l.get("details", "")[:50],
                })
            df = pd.DataFrame(log_data)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.caption(f"Showing {len(logs)} records")
        else:
            st.info("No audit log entries found.")


elif page.startswith("💾"):  # Backup & Export
    st.markdown('<p class="main-header">Backup & Export</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Export data and manage backups</p>', unsafe_allow_html=True)
    st.divider()

    if not USE_GOOGLE_SHEETS:
        st.info("Backup & Export is available in Google Sheets mode only.")
    else:
        tab_csv, tab_excel, tab_drive = st.tabs(["📋 CSV Export", "📊 Excel Backup", "☁️ Drive Backup"])

        with tab_csv:
            st.subheader("Export All Sheets as CSV")
            st.write("Download each sheet as an individual CSV file for archival or external analysis.")
            if st.button("📋 Export CSV Files", type="primary"):
                backup_dir = os.path.join(os.path.dirname(__file__), "backups")
                with st.spinner("Exporting..."):
                    paths = export_all_sheets_csv(backup_dir)
                if paths:
                    st.success(f"✅ {len(paths)} CSV files exported!")
                    for p in paths:
                        fname = os.path.basename(p)
                        with open(p, "rb") as f:
                            st.download_button(f"📥 {fname}", data=f.read(), file_name=fname, mime="text/csv", key=f"dl_{fname}")
                else:
                    st.warning("No data to export.")

        with tab_excel:
            st.subheader("Export as Single Excel Workbook")
            st.write("All sheets combined into one Excel file for easy sharing.")
            if st.button("📊 Export Excel Backup", type="primary"):
                backup_dir = os.path.join(os.path.dirname(__file__), "backups")
                with st.spinner("Generating Excel backup..."):
                    xlsx_path = export_sheet_to_excel(backup_dir)
                if xlsx_path:
                    st.success("✅ Excel backup created!")
                    with open(xlsx_path, "rb") as f:
                        st.download_button("📥 Download Excel Backup", data=f.read(),
                                           file_name=os.path.basename(xlsx_path),
                                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.error("Failed to create Excel backup. Make sure openpyxl is installed.")

        with tab_drive:
            st.subheader("Upload Backup to Google Drive")
            st.write("Export and upload backup file to the UIG Billing System Google Drive folder.")
            if st.button("☁️ Export & Upload to Drive", type="primary"):
                backup_dir = os.path.join(os.path.dirname(__file__), "backups")
                with st.spinner("Exporting and uploading..."):
                    xlsx_path = export_sheet_to_excel(backup_dir)
                    if xlsx_path:
                        link = upload_backup_to_drive(xlsx_path)
                        if link:
                            st.success("✅ Backup uploaded to Google Drive!")
                            st.markdown(f"[📂 View in Drive]({link})")
                        else:
                            st.warning("Export succeeded but Drive upload failed. Download locally instead:")
                            with open(xlsx_path, "rb") as f:
                                st.download_button("📥 Download", data=f.read(),
                                                   file_name=os.path.basename(xlsx_path),
                                                   mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                    else:
                        st.error("Failed to create backup file.")

        st.divider()
        st.subheader("🔄 Recalculate All Balances")
        st.write("Re-sync all client balances from invoice and payment records (batch operation).")
        if st.button("🔄 Recalculate Balances", type="secondary"):
            with st.spinner("Recalculating..."):
                recalculate_all_balances_batch()
            st.success("✅ All client balances recalculated!")
            invalidate_all_caches()

elif page.startswith("🤖"):  # AI Assistant
    st.markdown('<p class="main-header">AI Assistant & Integration Status</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Google Workspace + Claude Cowork AI Agent Integration Status</p>', unsafe_allow_html=True)
    st.divider()

    # --- Integration Status ---
    st.subheader("🔗 Integration Status")
    col_s1, col_s2, col_s3 = st.columns(3)
    with col_s1:
        if USE_GOOGLE_SHEETS:
            if is_sheets_configured() and is_sheets_authorized():
                st.success("✅ Google Sheets Connected")
                st.caption(f"Spreadsheet ID: {SPREADSHEET_ID[:20]}...")
            elif is_sheets_configured():
                st.warning("⚠️ Google Sheets Authorization Required")
            else:
                st.error("❌ Google Sheets Not Configured")
        else:
            st.info("📦 Using SQLite Local DB")
    with col_s2:
        if HAS_DRIVE:
            st.success("✅ Google Drive Connected")
            st.caption("Auto-upload invoices enabled")
        else:
            st.warning("⚠️ Google Drive Not Connected")
    with col_s3:
        if is_gmail_api_configured() and is_gmail_api_authorized():
            st.success("✅ Gmail API Connected")
        else:
            st.warning("⚠️ Gmail API Not Configured")

    st.divider()

    st.info("""
    **This app is fully integrated with `iifa-legal-agent:billing` skill and Google Workspace.**

    📊 **Google Sheets** — All client, invoice, and payment data synced in real-time
    ☁️ **Google Drive** — Invoices, reports, and documents auto-saved to per-client folders
    📧 **Gmail** — Send invoices and past-due reminders automatically
    🤖 **Claude Cowork** — Perform billing tasks using natural language

    Available commands in Claude Cowork:
    - "Create an invoice for client Yun"
    - "Show me all past-due invoices"
    - "Generate this month's income report"
    - "Check files for client Kim"
    """)

    st.subheader("Quick Actions")
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("📊 Generate Monthly Report", use_container_width=True):
            pnl = get_monthly_pnl(date.today().year, date.today().month)
            st.write(f"**{calendar.month_name[date.today().month]} {date.today().year}**")
            st.write(f"- Collected: ${pnl['income']:,.2f}")
            st.write(f"- Expenses: ${pnl['expenses']:,.2f}")
            st.write(f"- Net: ${pnl['net']:,.2f}")
    with col2:
        if st.button("Past Due Summary", use_container_width=True):
            pd_inv = get_past_due_invoices()
            if pd_inv:
                total = sum(i["amount_due"] for i in pd_inv)
                st.error(f"{len(pd_inv)} past due invoices: ${total:,.2f}")
                for inv in pd_inv:
                    st.write(f"- {inv['client_name']}: ${inv['amount_due']:,.2f} ({inv['days_overdue']}d overdue)")
            else:
                st.success("No past due invoices!")
    with col3:
        if st.button("Client Overview", use_container_width=True):
            clients = get_all_clients()
            st.write(f"**{len(clients)} active clients:**")
            for c in clients:
                st.write(f"- {c['name']} -- {c['visa_type'] or '-'} ({c['case_number'] or '-'})")

    # --- Google Drive Client Files Viewer ---
    if HAS_DRIVE and USE_GOOGLE_SHEETS:
        st.divider()
        st.subheader("Client Files on Google Drive")
        clients = get_all_clients()
        if clients:
            client_opts = {f"{c['name']} ({c['case_number'] or '-'})": c for c in clients}
            sel_key = st.selectbox("Select client to view files", list(client_opts.keys()), key="ai_drive_client")
            sel_c = client_opts[sel_key]
            if st.button("Show Drive Files", key="ai_show_files"):
                try:
                    files = list_client_files(sel_c["name"], sel_c.get("case_number", ""))
                    if files:
                        for f in files:
                            link = f.get("webViewLink", "")
                            st.markdown(f"- [{f['name']}]({link})" if link else f"- {f['name']}")
                    else:
                        st.info("No files found for this client yet.")
                except Exception as e:
                    st.warning(f"Drive access error: {e}")


# ==============================
# USCIS CASE TRACKER
# ==============================
elif page.startswith("🔍"):  # USCIS Tracker
    st.markdown(f'<p class="main-header">🔍 {t("uscis_title", _lang)}</p>', unsafe_allow_html=True)
    st.divider()

    if HAS_USCIS:
        tab_check, tab_tracked = st.tabs(["🔍 Check Status", "📋 Tracked Cases"])

        with tab_check:
            st.subheader("Check USCIS Case Status")
            col1, col2 = st.columns([3, 1])
            with col1:
                receipt_input = st.text_input(t("receipt_number", _lang),
                    placeholder="EAC2190012345 (3 letters + 10 digits)", key="uscis_receipt")
            with col2:
                st.markdown("<br>", unsafe_allow_html=True)
                check_btn = st.button(t("check_status", _lang), type="primary", use_container_width=True)

            if check_btn and receipt_input:
                with st.spinner("Checking USCIS..."):
                    result = check_case_status(receipt_input)
                if result.get("success"):
                    emoji = get_status_emoji(result["category"])
                    color = get_status_color(result["category"])
                    st.markdown(f"""
                    <div style="border-left:5px solid {color}; padding:15px; background:#f8f9fa; border-radius:5px; margin:10px 0;">
                        <h3>{emoji} {result['status_title']}</h3>
                        <p><b>Receipt:</b> {result['receipt_number']}</p>
                        <p>{result['status_description'][:300]}</p>
                        <p style="color:#999; font-size:12px;">Checked: {result['checked_at'][:19]}</p>
                    </div>
                    """, unsafe_allow_html=True)

                    # Save to tracked cases
                    with st.expander("Save to Tracked Cases"):
                        save_client = st.text_input("Client Name", key="uscis_save_client")
                        save_type = st.selectbox("Case Type", ["I-130", "I-140", "I-485", "I-751",
                            "N-400", "I-765", "I-131", "I-129", "I-539", "Other"], key="uscis_save_type")
                        if st.button("Save Case", key="uscis_save_btn"):
                            if USE_GOOGLE_SHEETS:
                                try:
                                    from google_sheets_db import get_sheets_service
                                    svc = get_sheets_service()
                                    case_data = {**result, "client_name": save_client, "case_type": save_type}
                                    save_case_to_sheets(case_data, svc, SPREADSHEET_ID)
                                    st.success("Case saved to tracker!")
                                except Exception as e:
                                    st.error(f"Save failed: {e}")
                else:
                    st.error(result.get("error", "Unknown error"))

            # Batch check
            st.divider()
            st.subheader("Batch Check Multiple Cases")
            batch_input = st.text_area("Enter receipt numbers (one per line)", height=100, key="uscis_batch")
            if st.button("Check All", key="uscis_batch_btn"):
                numbers = [n.strip() for n in batch_input.split("\n") if n.strip()]
                if numbers:
                    with st.spinner(f"Checking {len(numbers)} cases..."):
                        results = check_multiple_cases(numbers)
                    for r in results:
                        if r.get("success"):
                            emoji = get_status_emoji(r["category"])
                            st.write(f"{emoji} **{r['receipt_number']}**: {r['status_title']}")
                        else:
                            st.write(f"❓ **{r.get('receipt_number', '?')}**: {r.get('error', 'Error')}")

        with tab_tracked:
            st.subheader("Tracked USCIS Cases")
            if USE_GOOGLE_SHEETS:
                try:
                    from google_sheets_db import get_sheets_service
                    svc = get_sheets_service()
                    cases = get_all_tracked_cases(svc, SPREADSHEET_ID)
                    if cases:
                        df = pd.DataFrame(cases)
                        st.dataframe(df, use_container_width=True)
                        if st.button("🔄 Refresh All Statuses", key="uscis_refresh_all"):
                            with st.spinner("Refreshing..."):
                                for case in cases:
                                    rn = case.get("receipt_number", "")
                                    if rn:
                                        result = check_case_status(rn)
                                        if result.get("success"):
                                            case.update(result)
                                            save_case_to_sheets(case, svc, SPREADSHEET_ID)
                            st.success("All cases refreshed!")
                            st.rerun()
                    else:
                        st.info("No tracked cases yet. Use 'Check Status' tab to add cases.")
                except Exception as e:
                    st.error(f"Error loading cases: {e}")
    else:
        st.warning("USCIS Tracker module not available.")


# ==============================
# COURT CASES & e-FILING
# ==============================
elif page.startswith("⚖️"):  # Court Cases
    st.markdown(f'<p class="main-header">⚖️ {t("court_title", _lang)}</p>', unsafe_allow_html=True)
    st.divider()

    if HAS_PACER:
        tab_cases, tab_add, tab_deadlines = st.tabs(["📋 Court Cases", "➕ Add Case", "⏰ Deadlines Calculator"])

        with tab_cases:
            st.subheader("Active Court Cases")
            if USE_GOOGLE_SHEETS:
                try:
                    from google_sheets_db import get_sheets_service
                    svc = get_sheets_service()
                    cases = get_all_court_cases(svc, SPREADSHEET_ID)
                    if cases:
                        df = pd.DataFrame(cases)
                        st.dataframe(df, use_container_width=True)
                    else:
                        st.info("No court cases added yet.")
                except Exception as e:
                    st.error(f"Error: {e}")

            st.divider()
            st.subheader("PACER Quick Links")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.markdown(f"[🔗 PACER Login]({PACER_URLS['login']})")
                st.markdown(f"[🔗 Case Search]({PACER_URLS['case_search']})")
            with col2:
                st.markdown(f"[🔗 N.D. Illinois ECF]({PACER_URLS['ILND']})")
                st.markdown(f"[🔗 C.D. Illinois ECF]({PACER_URLS['ILCD']})")
            with col3:
                st.markdown(f"[🔗 7th Circuit ECF]({PACER_URLS['7CIR']})")
                st.markdown(f"[🔗 S.D. Illinois ECF]({PACER_URLS['ILSD']})")

        with tab_add:
            st.subheader("Add New Court Case")
            with st.form("add_court_case"):
                cc_number = st.text_input("Case Number", placeholder="1:24-cv-01234")
                cc_name = st.text_input("Case Name", placeholder="Doe v. USCIS")
                cc_district = st.selectbox("Court/District", list(FEDERAL_DISTRICTS.keys()),
                    format_func=lambda x: f"{x} - {FEDERAL_DISTRICTS[x]}")
                cc_judge = st.text_input("Judge", placeholder="Hon. John Smith")
                cc_client = st.text_input("Client Name")
                cc_type = st.selectbox("Case Type", ["Immigration", "Civil", "Criminal", "Appellate", "Other"])
                cc_filed = st.date_input("Filed Date")
                cc_notes = st.text_area("Notes", height=80)
                cc_submit = st.form_submit_button("Add Case", type="primary")

            if cc_submit and cc_number and cc_name:
                if USE_GOOGLE_SHEETS:
                    try:
                        from google_sheets_db import get_sheets_service
                        svc = get_sheets_service()
                        case_data = {
                            "case_number": cc_number, "case_name": cc_name,
                            "court": FEDERAL_DISTRICTS.get(cc_district, cc_district),
                            "district": cc_district, "judge": cc_judge,
                            "client_name": cc_client, "case_type": cc_type,
                            "filed_date": str(cc_filed), "notes": cc_notes,
                        }
                        save_court_case(case_data, svc, SPREADSHEET_ID)
                        st.success(f"Court case {cc_number} added!")
                    except Exception as e:
                        st.error(f"Error: {e}")

        with tab_deadlines:
            st.subheader("Federal Deadline Calculator")
            event_type = st.selectbox("Event Type", [
                "Complaint Filed", "Motion Filed Against", "Response Filed",
                "Order/Judgment Entered", "Discovery Request Received", "Immigration Order"
            ])
            event_date = st.date_input("Event Date", value=date.today())
            if st.button("Calculate Deadlines", type="primary"):
                deadlines = get_auto_deadlines(event_type, str(event_date))
                if deadlines:
                    for dl in deadlines:
                        priority_color = {"critical": "🔴", "high": "🟡", "medium": "🔵"}.get(dl["priority"], "⚪")
                        st.write(f"{priority_color} **{dl['name']}**: {dl['date'].strftime('%B %d, %Y') if dl['date'] else 'N/A'}")
                else:
                    st.info("No automatic deadlines for this event type.")

            st.divider()
            st.subheader("Common Federal Court Deadlines Reference")
            for name, info in FEDERAL_DEADLINES.items():
                st.write(f"- **{name}**: {info['days']} days")
    else:
        st.warning("PACER module not available.")


# ==============================
# CLIENT PORTAL MANAGEMENT
# ==============================
elif page.startswith("🌐"):  # Client Portal
    st.markdown(f'<p class="main-header">🌐 {t("portal_title", _lang)}</p>', unsafe_allow_html=True)
    st.divider()

    if HAS_PORTAL and USE_GOOGLE_SHEETS:
        tab_manage, tab_preview = st.tabs(["👤 Manage Access", "👁️ Portal Preview"])

        with tab_manage:
            st.subheader("Generate Client Portal Access")
            st.write("Create a unique access code for a client to view their case status, invoices, and documents online.")

            clients = get_all_clients()
            if clients:
                client_opts = {f"{c['name']} ({c['case_number'] or '-'})": c for c in clients}
                sel_key = st.selectbox("Select Client", list(client_opts.keys()), key="portal_client")
                sel_c = client_opts[sel_key]

                portal_email = st.text_input("Client Email", value=sel_c.get("email", ""), key="portal_email")

                if st.button("🔑 Generate Access Code", type="primary", key="portal_gen"):
                    try:
                        from google_sheets_db import get_sheets_service
                        svc = get_sheets_service()
                        code = create_portal_access(
                            sel_c["id"], sel_c["name"], portal_email, svc, SPREADSHEET_ID
                        )
                        st.success(f"Access code generated!")
                        st.code(code, language=None)
                        st.warning("⚠️ Save this code now! It cannot be retrieved later.")

                        portal_url = "uig-billing-app-3bny6mhputkk7iakddvae9.streamlit.app"
                        st.info(f"""
                        **Send to client:**
                        - Portal URL: {portal_url}
                        - Access Code: {code}
                        - Click "Client Portal Login" on the login page
                        """)
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.info("No clients found. Add clients first.")

        with tab_preview:
            st.subheader("Preview Client Portal View")
            st.write("See what clients will see when they log into the portal.")
            clients = get_all_clients()
            if clients:
                client_opts2 = {f"{c['name']}": c for c in clients}
                sel_key2 = st.selectbox("Preview as", list(client_opts2.keys()), key="portal_preview_client")
                sel_c2 = client_opts2[sel_key2]

                if st.button("Show Preview", key="portal_preview_btn"):
                    try:
                        from google_sheets_db import get_sheets_service
                        svc = get_sheets_service()

                        st.markdown(f"### Welcome, {sel_c2['name']}")
                        st.markdown("---")

                        # Invoices
                        invoices = get_client_invoices(sel_c2["id"], svc, SPREADSHEET_ID)
                        st.subheader("📄 Your Invoices")
                        if invoices:
                            st.dataframe(pd.DataFrame(invoices), use_container_width=True)
                        else:
                            st.info("No invoices found.")

                        # Payments
                        payments = get_client_payments(sel_c2["id"], svc, SPREADSHEET_ID)
                        st.subheader("💳 Your Payments")
                        if payments:
                            st.dataframe(pd.DataFrame(payments), use_container_width=True)
                        else:
                            st.info("No payments found.")

                        # Deadlines
                        deadlines = get_client_deadlines(sel_c2["id"], svc, SPREADSHEET_ID)
                        st.subheader("📅 Upcoming Deadlines")
                        if deadlines:
                            for dl in deadlines:
                                st.write(f"- **{dl['date']}**: {dl['description']}")
                        else:
                            st.info("No upcoming deadlines.")
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.warning("Client Portal module requires Google Sheets connection.")


# ==============================
# CALENDAR SYNC
# ==============================
elif page.startswith("🗓️"):  # Calendar Sync
    st.markdown('<p class="main-header">🗓️ Google Calendar Sync</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">데드라인 및 법정 기일을 Google Calendar에 자동 동기화</p>', unsafe_allow_html=True)
    st.divider()

    try:
        import calendar_sync as cs
    except Exception as e:
        st.error(f"calendar_sync 모듈 로드 실패: {e}")
        cs = None

    st.info(
        "⚠️ **최초 사용 시 OAuth 재인증 필요**: Calendar 접근 권한이 추가되었습니다. "
        "Google Workspace Setup 페이지에서 재인증하세요."
    )

    if cs and USE_GOOGLE_SHEETS:
        try:
            from google_sheets_db import get_sheets_service, get_credentials
            svc = get_sheets_service()
            creds = get_credentials()

            col1, col2 = st.columns(2)
            with col1:
                if st.button("📋 사용 가능한 캘린더 목록 조회"):
                    cals = cs.list_calendars(creds)
                    if cals:
                        for c in cals:
                            marker = " ⭐" if c.get("primary") else ""
                            st.write(f"- **{c['summary']}**{marker} (`{c['id']}`)")
                    else:
                        st.warning("캘린더 목록을 가져올 수 없습니다. OAuth scope를 확인하세요.")

            with col2:
                calendar_id_input = st.text_input(
                    "대상 Calendar ID",
                    value="primary",
                    help="기본값 'primary'는 주 캘린더"
                )

            st.divider()
            st.subheader("데드라인 일괄 동기화")

            if st.button("🔄 미동기화 데드라인 모두 캘린더에 추가", type="primary"):
                cs.ensure_calendar_event_id_column(svc, SPREADSHEET_ID)
                with st.spinner("동기화 중..."):
                    result = cs.sync_all_pending_deadlines(
                        credentials=creds,
                        sheets_service=svc,
                        spreadsheet_id=SPREADSHEET_ID,
                        calendar_id=calendar_id_input,
                    )
                st.success(
                    f"✅ 동기화 완료 — 추가: {result.get('synced', 0)}건, "
                    f"건너뜀: {result.get('skipped', 0)}건, 실패: {result.get('failed', 0)}건"
                )
                if result.get("errors"):
                    with st.expander("오류 상세"):
                        for err in result["errors"]:
                            st.text(err)

            st.divider()
            st.subheader("개별 이벤트 수동 추가")

            with st.form("manual_calendar_event"):
                ev_title = st.text_input("이벤트 제목*", placeholder="USCIS Interview")
                ev_date = st.date_input("날짜*", value=date.today())
                ev_client = st.text_input("클라이언트 이름")
                ev_case = st.text_input("케이스 번호")
                ev_location = st.text_input("장소", placeholder="USCIS Chicago Field Office")
                ev_desc = st.text_area("상세 설명", height=80)
                ev_submit = st.form_submit_button("캘린더에 추가", type="primary")

            if ev_submit and ev_title:
                res = cs.create_calendar_event(
                    credentials=creds,
                    title=ev_title,
                    event_date=ev_date,
                    description=ev_desc,
                    client_name=ev_client,
                    case_number=ev_case,
                    location=ev_location,
                    calendar_id=calendar_id_input,
                )
                if res.get("success"):
                    st.success(f"✅ 이벤트 생성 완료")
                    if res.get("html_link"):
                        st.markdown(f"[📅 캘린더에서 보기]({res['html_link']})")
                else:
                    st.error(f"실패: {res.get('error')}")

        except Exception as e:
            st.error(f"Calendar Sync 초기화 오류: {e}")
            st.info("Google Workspace Setup 페이지에서 재인증이 필요할 수 있습니다.")
    else:
        st.warning("Google Sheets 연결이 필요합니다.")


# ==============================
# E-SIGNATURE
# ==============================
elif page.startswith("✍️"):  # e-Signature
    st.markdown('<p class="main-header">✍️ e-Signature</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">전자서명 요청 발송 및 관리</p>', unsafe_allow_html=True)
    st.divider()

    try:
        import esignature as esig
    except Exception as e:
        st.error(f"esignature 모듈 로드 실패: {e}")
        esig = None

    if esig and USE_GOOGLE_SHEETS:
        try:
            from google_sheets_db import get_sheets_service, get_drive_service
            svc = get_sheets_service()
            drive_svc = get_drive_service()
            esig.ensure_signature_sheet(svc, SPREADSHEET_ID)

            tab_new, tab_pending, tab_sign = st.tabs([
                "📤 서명 요청 생성", "⏳ 대기 중 요청", "✍️ 직접 서명 (변호사용)"
            ])

            with tab_new:
                st.subheader("클라이언트에게 서명 요청 보내기")
                with st.form("new_signature_request"):
                    sr_client_id = st.text_input("클라이언트 ID*", placeholder="CLIENT-2026-001")
                    sr_client_name = st.text_input("클라이언트 이름*")
                    sr_doc_name = st.text_input("문서 이름*", placeholder="수임계약서.pdf")
                    sr_doc_id = st.text_input("Drive 파일 ID*", help="서명받을 PDF의 Google Drive file ID")
                    sr_notes = st.text_area("메모", height=60)
                    sr_submit = st.form_submit_button("서명 요청 생성", type="primary")

                if sr_submit and sr_client_id and sr_client_name and sr_doc_id:
                    try:
                        req_id = esig.create_signature_request(
                            sheets_service=svc,
                            spreadsheet_id=SPREADSHEET_ID,
                            client_name=sr_client_name,
                            client_id=sr_client_id,
                            document_name=sr_doc_name,
                            document_drive_id=sr_doc_id,
                            requested_by=st.session_state.get("username", "admin"),
                            notes=sr_notes,
                        )
                        st.success(f"✅ 서명 요청 생성 완료: `{req_id}`")
                        st.info("클라이언트는 Client Portal 로그인 후 '서명' 탭에서 확인할 수 있습니다.")
                    except Exception as e:
                        st.error(f"오류: {e}")

            with tab_pending:
                st.subheader("대기 중인 서명 요청")
                pending = esig.get_pending_signature_requests(svc, SPREADSHEET_ID)
                if pending:
                    df = pd.DataFrame([
                        {
                            "Request ID": p.get("Request ID"),
                            "Client": p.get("Client Name"),
                            "Document": p.get("Document Name"),
                            "Created": p.get("Created At", "")[:10],
                            "Requested By": p.get("Requested By"),
                        }
                        for p in pending
                    ])
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("대기 중인 서명 요청이 없습니다.")

            with tab_sign:
                st.subheader("변호사 직접 서명 (PDF에 서명 삽입)")
                st.caption("PDF 파일을 업로드하고 아래 패드에 서명한 뒤, 서명이 삽입된 PDF를 다운로드합니다.")

                uploaded_pdf = st.file_uploader("PDF 업로드", type=["pdf"], key="sign_pdf_upload")

                col_a, col_b = st.columns(2)
                with col_a:
                    sig_x = st.number_input("X 좌표 (points)", value=100, min_value=0)
                    sig_y = st.number_input("Y 좌표 (points)", value=100, min_value=0)
                with col_b:
                    sig_w = st.number_input("너비 (points)", value=150, min_value=20)
                    sig_h = st.number_input("높이 (points)", value=50, min_value=10)

                sig_page = st.number_input("페이지 번호 (0=첫 페이지, 비워두면 마지막)", value=-1, min_value=-1)
                signer_name = st.text_input("서명자 이름", value="US Immigration Group")

                st.write("**아래 영역에 마우스/터치로 서명하세요:**")
                sig_img = esig.signature_canvas_component(key="admin_sig_pad")

                if uploaded_pdf and sig_img and st.button("🖋️ 서명 삽입 및 PDF 다운로드", type="primary"):
                    try:
                        pdf_bytes = uploaded_pdf.read()
                        sig_png = esig.signature_to_png_bytes(sig_img)
                        page_arg = None if sig_page == -1 else int(sig_page)
                        signed = esig.apply_signature_to_pdf(
                            pdf_bytes=pdf_bytes,
                            signature_png_bytes=sig_png,
                            page_num=page_arg,
                            x=sig_x, y=sig_y,
                            width=sig_w, height=sig_h,
                            signer_name=signer_name,
                        )
                        st.success("✅ 서명 완료")
                        st.download_button(
                            "📥 서명된 PDF 다운로드",
                            data=signed,
                            file_name=f"SIGNED_{uploaded_pdf.name}",
                            mime="application/pdf",
                        )
                    except Exception as e:
                        st.error(f"서명 실패: {e}")

        except Exception as e:
            st.error(f"e-Signature 초기화 오류: {e}")
    else:
        st.warning("Google Sheets 연결이 필요합니다.")


# ==============================
# GOOGLE WORKSPACE SETUP
# ==============================
elif page.startswith("⚙️"):  # Gmail Setup
    st.markdown('<p class="main-header">Google Workspace Setup</p>', unsafe_allow_html=True)
    st.markdown('<p class="sub-header">Gmail + Google Sheets + Google Drive Setup</p>', unsafe_allow_html=True)
    st.divider()

    # --- Google Sheets & Drive Status ---
    st.subheader("Google Sheets & Drive")
    if USE_GOOGLE_SHEETS:
        sheets_ok = is_sheets_configured() and is_sheets_authorized()
        if sheets_ok:
            st.success("Google Sheets & Drive connected")
            st.markdown(f"[Open UIG Master Database](https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID})")
            st.markdown("[Open UIG Billing System folder](https://drive.google.com/drive/folders/1FAYoRukcu01_Exx3JGdE4NRNs-5TyURI)")
            if st.button("Initialize / Sync Sheets", key="init_sheets_btn"):
                if init_sheets():
                    seed_sample_clients()
                    st.success("Sheet structure initialized!")
                    st.rerun()
                else:
                    st.error("Sheet initialization failed")
        elif is_sheets_configured():
            st.warning("Google OAuth authorization needed")
            if st.button("Authorize Google Workspace", type="primary", key="auth_sheets"):
                try:
                    creds = get_credentials()
                    if creds:
                        st.success("Authorization successful!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Authorization failed: {e}")
        else:
            st.warning("credentials.json file needed")
    else:
        st.info("Currently using local SQLite DB. Set up credentials.json to enable Google Sheets.")

    st.divider()

    # --- Gmail Status ---
    st.subheader("Gmail API")
    if is_gmail_api_configured():
        if is_gmail_api_authorized():
            st.success("Gmail API authorized and ready")
        else:
            st.warning("Gmail API authorization needed")
            if st.button("Authorize Gmail", type="primary", key="auth_gmail"):
                success, msg = authorize_gmail()
                if success:
                    st.success(msg)
                    st.rerun()
                else:
                    st.error(msg)
    else:
        st.warning("Gmail credentials not found")

    st.divider()

    # --- Credentials Upload ---
    st.subheader("OAuth Credentials Setup")
    st.markdown("""
    **One credentials.json file enables Gmail, Sheets, and Drive.**

    1. Go to [Google Cloud Console](https://console.cloud.google.com)
    2. Enable Gmail API, Google Sheets API, Google Drive API
    3. Create OAuth 2.0 Client ID (Desktop App)
    4. Download JSON and upload below
    """)

    uploaded = st.file_uploader("Upload credentials.json", type=["json"], key="cred_upload")
    if uploaded:
        from config import CREDENTIALS_FILE
        with open(CREDENTIALS_FILE, "wb") as f:
            f.write(uploaded.getvalue())
        st.success("Credentials file saved!")
        st.rerun()

    # Copy from yr-rent-app option
    st.divider()
    yr_cred = os.path.join(os.path.dirname(__file__), "..", "yr-rent-app", "gmail_credentials.json")
    if os.path.exists(yr_cred):
        st.info("Gmail credentials found in yr-rent-app folder")
        if st.button("Copy credentials from yr-rent-app", key="copy_yr"):
            import shutil
            from config import CREDENTIALS_FILE, TOKEN_FILE
            shutil.copy(yr_cred, CREDENTIALS_FILE)
            yr_token = os.path.join(os.path.dirname(__file__), "..", "yr-rent-app", "gmail_token.json")
            if os.path.exists(yr_token):
                shutil.copy(yr_token, TOKEN_FILE)
            st.success("Credentials copied\!")
            st.rerun()
