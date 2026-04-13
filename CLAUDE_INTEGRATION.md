# UIG Billing App — Claude Cowork AI Integration Guide

## Overview
The UIG Billing System uses **Google Sheets** as its primary database and **Google Drive** for file storage.
When Claude Cowork's `iifa-legal-agent:billing` skill is invoked, it should use the Python modules in this
folder to read/write data, ensuring all changes are reflected in both the Streamlit web app and Google Drive.

## Architecture

```
Claude Cowork (AI Agent)
    ↓ imports
uig-billing-app/google_sheets_db.py  →  Google Sheets (UIG_Master_Database)
uig-billing-app/google_drive_service.py  →  Google Drive (UIG Billing System folder)
uig-billing-app/invoice_generator.py  →  Generate .xlsx invoices
uig-billing-app/email_service.py  →  Draft emails
    ↓
Streamlit App (app.py) reads same Google Sheets  →  Real-time sync
```

## Google Sheets Master Database
- **Spreadsheet ID:** `1Rr8ltyzzBihlSqPLi2RTBGbxNZzsVQICOHHzvDZTsOA`
- **Sheets:** Clients, Invoices, Payments, Trust_Account, Expenses, Deadlines, Email_Log

## Google Drive Folder Structure
- **Root:** `UIG Billing System/` (ID: `1FAYoRukcu01_Exx3JGdE4NRNs-5TyURI`)
- **Clients:** Per-client folders with Invoices/, Retainer_Billing/, Documents/ subfolders
- **Reports:** Monthly_PnL/, Annual/
- **Templates:** Invoice and letter templates

## How AI Agent Should Use This

### To create an invoice:
```python
import sys
sys.path.insert(0, r"C:\Users\btma2\UIG Cowork\uig-billing-app")
from google_sheets_db import get_all_clients, create_invoice, get_client
from invoice_generator import generate_invoice_excel
from google_drive_service import upload_invoice

# 1. Find client
clients = get_all_clients()
client = next(c for c in clients if "Yun" in c["name"])

# 2. Create invoice in Google Sheets
inv_num = create_invoice(
    client_id=client["id"],
    description="H-1B Petition Preparation",
    legal_fees=3500, filing_fees=460,
    invoice_date=date.today(),
    due_date=date.today() + timedelta(days=30)
)

# 3. Generate Excel file
filepath = generate_invoice_excel(
    client=client, invoice_number=inv_num,
    invoice_date=date.today(), due_date=due_date,
    description="H-1B Petition", legal_fees=3500, filing_fees=460
)

# 4. Upload to Google Drive
result = upload_invoice(filepath, client["name"], client.get("case_number", ""))
print(f"Drive link: {result['link']}")
```

### To check balances:
```python
from google_sheets_db import get_dashboard_stats, get_past_due_invoices
stats = get_dashboard_stats()
past_due = get_past_due_invoices()
```

### To record a payment:
```python
from google_sheets_db import record_payment
record_payment(client_id=1, invoice_id=1, amount=1500, payment_method="Check", deposit_to="Operating")
```

### IOLTA Trust Account:
```python
from google_sheets_db import trust_deposit, trust_withdrawal, get_trust_balance
trust_deposit(client_id=1, amount=3500, description="Retainer deposit")
balance = get_trust_balance(client_id=1)
```

## Key Config (config.py)
- All Google Drive folder IDs
- Google Sheets spreadsheet ID
- OAuth credentials and token paths
- Firm information (name, address, phone)
