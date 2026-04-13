"""
US Immigration Group - Billing System Configuration
Google Drive & Sheets IDs and settings.
"""

# === Google Drive Folder IDs ===
DRIVE_ROOT_FOLDER_ID = "1FAYoRukcu01_Exx3JGdE4NRNs-5TyURI"       # UIG Billing System/
DRIVE_CLIENTS_FOLDER_ID = "1Idd6BpB_-38Ii5_L6NbPk3YC31Il4x-y"    # UIG Billing System/Clients/
DRIVE_REPORTS_FOLDER_ID = "1xiuwMZaQd2Yl6T55toCmyxL9UxBZJdzq"     # UIG Billing System/Reports/
DRIVE_TEMPLATES_FOLDER_ID = "1ZK2vQJz1nf1pHjfm3iOId5ABwKLZIaWF"   # UIG Billing System/Templates/
DRIVE_MONTHLY_PNL_FOLDER_ID = "18BmPlo0Be6dyR7TGfz6aeE-2NxvilZlM" # Reports/Monthly_PnL/
DRIVE_ANNUAL_FOLDER_ID = "13IOB8LrxGX6YmFFKehddVxXO8gdrrOn2"      # Reports/Annual/
DRIVE_BACKUPS_FOLDER_ID = ""  # Reports/Backups/ (auto-created)

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
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# === Credentials paths ===
import os
APP_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(APP_DIR, "credentials.json")
TOKEN_FILE = os.path.join(APP_DIR, "token.json")
