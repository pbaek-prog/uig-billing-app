"""
UIG AI LEGAL AGENT - Google Drive Folder Setup Script
Run this once to create the complete folder structure on Google Drive.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "token.json")
SCOPES = [
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive.file",
]

# Load credentials
creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())

service = build("drive", "v3", credentials=creds)


def create_folder(name, parent_id=None):
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_id:
        metadata["parents"] = [parent_id]
    folder = service.files().create(body=metadata, fields="id, webViewLink").execute()
    print(f"  + {name}  (ID: {folder['id']})")
    return folder["id"]


print("=" * 60)
print("  UIG AI LEGAL AGENT - Google Drive Folder Setup")
print("=" * 60)

# === Root ===
root_id = create_folder("UIG AI LEGAL AGENT")
print(f"\nRoot folder created!\n")

# === Clients ===
clients_id = create_folder("Clients", root_id)

# === Cases ===
cases_id = create_folder("Cases", root_id)

# === Immigration ===
immigration_id = create_folder("Immigration", root_id)
imm_petitions = create_folder("Petitions", immigration_id)
imm_forms = create_folder("Forms", immigration_id)
imm_rfe = create_folder("RFE_Responses", immigration_id)
imm_approvals = create_folder("Approvals", immigration_id)

# === Billing & Finance ===
billing_id = create_folder("Billing_Finance", root_id)
billing_invoices = create_folder("Invoices", billing_id)
billing_payments = create_folder("Payment_Records", billing_id)
billing_retainers = create_folder("Retainer_Agreements", billing_id)
billing_trust = create_folder("Trust_Account_IOLTA", billing_id)
billing_expenses = create_folder("Expenses", billing_id)

# === Reports ===
reports_id = create_folder("Reports", root_id)
reports_monthly = create_folder("Monthly_PnL", reports_id)
reports_annual = create_folder("Annual", reports_id)
reports_backups = create_folder("Backups", reports_id)

# === Court Documents ===
court_id = create_folder("Court_Documents", root_id)
court_motions = create_folder("Motions", court_id)
court_briefs = create_folder("Briefs", court_id)
court_evidence = create_folder("Evidence", court_id)
court_orders = create_folder("Court_Orders", court_id)

# === Contracts ===
contracts_id = create_folder("Contracts_Agreements", root_id)

# === Correspondence ===
correspondence_id = create_folder("Correspondence", root_id)
corr_uscis = create_folder("USCIS", correspondence_id)
corr_courts = create_folder("Courts", correspondence_id)
corr_clients = create_folder("Client_Letters", correspondence_id)
corr_opposing = create_folder("Opposing_Counsel", correspondence_id)

# === Compliance ===
compliance_id = create_folder("Compliance", root_id)

# === Templates ===
templates_id = create_folder("Templates", root_id)

# === Archive ===
archive_id = create_folder("Archive", root_id)

# === Save folder IDs ===
folder_ids = {
    "ROOT": root_id,
    "CLIENTS": clients_id,
    "CASES": cases_id,
    "IMMIGRATION": immigration_id,
    "IMMIGRATION_PETITIONS": imm_petitions,
    "IMMIGRATION_FORMS": imm_forms,
    "IMMIGRATION_RFE": imm_rfe,
    "IMMIGRATION_APPROVALS": imm_approvals,
    "BILLING": billing_id,
    "BILLING_INVOICES": billing_invoices,
    "BILLING_PAYMENTS": billing_payments,
    "BILLING_RETAINERS": billing_retainers,
    "BILLING_TRUST": billing_trust,
    "BILLING_EXPENSES": billing_expenses,
    "REPORTS": reports_id,
    "REPORTS_MONTHLY": reports_monthly,
    "REPORTS_ANNUAL": reports_annual,
    "REPORTS_BACKUPS": reports_backups,
    "COURT": court_id,
    "COURT_MOTIONS": court_motions,
    "COURT_BRIEFS": court_briefs,
    "COURT_EVIDENCE": court_evidence,
    "COURT_ORDERS": court_orders,
    "CONTRACTS": contracts_id,
    "CORRESPONDENCE": correspondence_id,
    "CORRESPONDENCE_USCIS": corr_uscis,
    "CORRESPONDENCE_COURTS": corr_courts,
    "CORRESPONDENCE_CLIENTS": corr_clients,
    "CORRESPONDENCE_OPPOSING": corr_opposing,
    "COMPLIANCE": compliance_id,
    "TEMPLATES": templates_id,
    "ARCHIVE": archive_id,
}

# Save to JSON file for reference
output_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "drive_folder_ids.json")
with open(output_file, "w") as f:
    json.dump(folder_ids, f, indent=2)

print("\n" + "=" * 60)
print("  ALL FOLDERS CREATED SUCCESSFULLY!")
print("=" * 60)
print(f"\nFolder IDs saved to: {output_file}")
print(f"\nGoogle Drive structure:")
print(f"""
UIG AI LEGAL AGENT/
├── Clients/           (per-client subfolders auto-created)
├── Cases/             (litigation case files)
├── Immigration/
│   ├── Petitions/
│   ├── Forms/
│   ├── RFE_Responses/
│   └── Approvals/
├── Billing_Finance/
│   ├── Invoices/
│   ├── Payment_Records/
│   ├── Retainer_Agreements/
│   ├── Trust_Account_IOLTA/
│   └── Expenses/
├── Reports/
│   ├── Monthly_PnL/
│   ├── Annual/
│   └── Backups/
├── Court_Documents/
│   ├── Motions/
│   ├── Briefs/
│   ├── Evidence/
│   └── Court_Orders/
├── Contracts_Agreements/
├── Correspondence/
│   ├── USCIS/
│   ├── Courts/
│   ├── Client_Letters/
│   └── Opposing_Counsel/
├── Compliance/
├── Templates/
└── Archive/
""")
