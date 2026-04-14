"""
US Immigration Group - Billing System Configuration
Google Drive & Sheets IDs and settings.
"""

# === Google Drive Folder IDs (UIG AI LEGAL AGENT) ===
DRIVE_ROOT_FOLDER_ID = "1R1ULDz4IJZhD8T9gTK5stTpT8obQ98v4"
DRIVE_CLIENTS_FOLDER_ID = "1ctz7GADuUKNPw85k-7pLmNsYW7Cc0pZm"
DRIVE_CASES_FOLDER_ID = "1eVvvfKHRJSfGb-FhkNoeVRWjDl_7WZNW"
DRIVE_REPORTS_FOLDER_ID = "1HXELl2yv-xDCdEYSvatoZq3q57hZ5IyM"
DRIVE_TEMPLATES_FOLDER_ID = "1EuTv7QvMfN8NHCgD6PU1-xfxPqGu6UWv"
DRIVE_MONTHLY_PNL_FOLDER_ID = "1iRyBXu4hnQThGNPCQiOGYqn-ypVS41IV"
DRIVE_ANNUAL_FOLDER_ID = "1xVR5xGk3WrGT0F-H-mbzRRjq-GaGYW5x"
DRIVE_BACKUPS_FOLDER_ID = "1YTvZHWZVLU5zlRfCFYo97UhPDHOP2QrA"
# Immigration
DRIVE_IMMIGRATION_FOLDER_ID = "1DwGXdQeNWQmOVqjSt_RTJhxkopqV854W"
DRIVE_IMMIGRATION_PETITIONS_ID = "1knsz2ukA3tIgzJsEWLByAqicVSmjZ6wv"
DRIVE_IMMIGRATION_FORMS_ID = "1sEsQV_zclk9pg-nq63wm9v1o3DTE8s_x"
DRIVE_IMMIGRATION_RFE_ID = "1_QYZqaUBIIIl_-KBCYITe0wNUlMcm6S4"
DRIVE_IMMIGRATION_APPROVALS_ID = "15ISz-x6oru_7LOWkYUz_LMthJfn-UlLj"
# Billing & Finance
DRIVE_BILLING_FOLDER_ID = "1qSWaOTfM0n3j1jIYWzhgquuSOEm6ACeU"
DRIVE_BILLING_INVOICES_ID = "1pcIW-tud4FTJ5nzY93210sEAwZALjY1j"
DRIVE_BILLING_PAYMENTS_ID = "12tipfOVmqCs8Byo6LcGtCL7mKtdE9bTc"
DRIVE_BILLING_RETAINERS_ID = "1tl2BxzVp3W2eyUBWXvmdS5g2TKo-wC9H"
DRIVE_BILLING_TRUST_ID = "1akNgxnzWBHCNKVuliBmJq8qPNh6nRvpy"
DRIVE_BILLING_EXPENSES_ID = "1JW2vCF283GmEKHR17t2c0Sx_5d2T6AB_"
# Court Documents
DRIVE_COURT_FOLDER_ID = "1YFGT4pNXh8Inq4q8q7ML1Z1BZV1a4o_h"
DRIVE_COURT_MOTIONS_ID = "1wvr0gFFJVlaGLQU640XMpVNR7nSoIawn"
DRIVE_COURT_BRIEFS_ID = "1W2ifulX1JgWt6v-CB7uwW2PeubiJoCX5"
DRIVE_COURT_EVIDENCE_ID = "1Tabl87Ai9NF_oCbxcsuItsCl3TroF_I-"
DRIVE_COURT_ORDERS_ID = "1OgqeJgJEBqsldNFtpNBrtMEUGiCQuNDQ"
# Contracts & Correspondence
DRIVE_CONTRACTS_FOLDER_ID = "1yJkM9qRuYA3NXjU44lki7ChwIJttmfPV"
DRIVE_CORRESPONDENCE_FOLDER_ID = "13iH_ZEfsgWWdo8MC555dGSCpHxj7Pt6r"
DRIVE_CORRESPONDENCE_USCIS_ID = "1YPBe7uTv156T25k6aDQaTh-LozqLXGOX"
DRIVE_CORRESPONDENCE_COURTS_ID = "1xCjcx_BQbwf-uo5yoHAniYQLaESYfRD3"
DRIVE_CORRESPONDENCE_CLIENTS_ID = "1qAwg1F_6FeHzxaIfwBBc-o_SkxO4qlgb"
DRIVE_CORRESPONDENCE_OPPOSING_ID = "1UJdHZHhQK1JgjBNQ6Q6LXNq7UJWsKsfs"
# Compliance & Archive
DRIVE_COMPLIANCE_FOLDER_ID = "1OibbB86XI_YwMAX7GPQf30b_eRtFDwU1"
DRIVE_ARCHIVE_FOLDER_ID = "1LaTPUsG_1QzQFgr8evyP6EaY4_Po7jJy"

# === Google Sheets Master Database ===
SPREADSHEET_ID = "1Rr8ltyzzBihlSqPLi2RTBGbxNZzsVQICOHHzvDZTsOA"

# === Sheet Names ===
SHEET_CLIENTS = "Clients"
SHEET_INVOICES = "Invoices"
SHEET_PAYMENTS = "Payments"
SHEET_TRUST = "Trust_Account"
SHEET_EXPENSES = "Expenses"
SHEET_DEADLINES = "Deadlines"
SHEET_EMAIL_LOG = "Email_Log"
SHEET_AUDIT_LOG = "Audit_Log"

# === Firm Info ===
FIRM_NAME = "US Immigration Group"
FIRM_ADDRESS = "800 E. Northwest Hwy. Ste 205"
FIRM_CITY_STATE = "Mount Prospect, IL 60016"
FIRM_PHONE = "(847) 449-8660"
FIRM_EMAIL = "info@usimmigrationgroup.org"

# === Brand Colors ===
GOLD = "#F5A623"
NAVY = "#1A3C5E"

# === OAuth Scopes (Gmail + Sheets + Drive) ===
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/calendar.events",
]

# === Credentials paths ===
import os
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(APP_DIR, "credentials.json")
TOKEN_FILE = os.path.join(APP_DIR, "token.json")
