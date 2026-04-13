"""Generate professional PDF invoices for US Immigration Group legal billing.
Uses reportlab for PDF generation.
"""
from datetime import date
import os

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "generated_invoices")
os.makedirs(OUTPUT_DIR, exist_ok=True)

FIRM = {
    "name": "US IMMIGRATION GROUP",
    "address": "800 E. Northwest Hwy. Ste 205",
    "city_state": "Mount Prospect, IL 60016",
    "phone": "(847) 449-8660",
    "email": "info@usimmigrationgroup.org",
    "website": "www.usimmigrationgroup.org",
}

# Brand colors (RGB)
NAVY = (26, 60, 94)
GOLD = (245, 166, 35)
WHITE = (255, 255, 255)
LIGHT_GRAY = (240, 244, 248)
DARK_GRAY = (102, 102, 102)


def generate_invoice_pdf(client, invoice_number, invoice_date, due_date,
                         description, legal_fees=0, filing_fees=0,
                         other_expenses=0, retainer_applied=0, line_items=None):
    """Generate a legal invoice as a professional PDF.

    Args:
        client: dict with keys name, email, address, case_number, visa_type
        invoice_number: str e.g. "INV-2026-001"
        invoice_date: date object
        due_date: date object
        description: str case description
        legal_fees, filing_fees, other_expenses, retainer_applied: float
        line_items: optional list of (description, category, amount) tuples

    Returns:
        Path to generated PDF file, or None if reportlab not installed.
    """
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib.units import inch
        from reportlab.lib.colors import HexColor, Color
        from reportlab.pdfgen import canvas
        from reportlab.lib.styles import getSampleStyleSheet
    except ImportError:
        print("reportlab not installed. Run: pip install reportlab")
        return None

    safe_name = client.get("name", "Client").replace(",", "").replace(".", "").replace("/", "_").replace(" ", "_")[:25]
    filename = f"Invoice_{invoice_number}_{safe_name}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    c = canvas.Canvas(filepath, pagesize=letter)
    width, height = letter  # 612 x 792
    margin = 50

    navy = Color(*[x/255.0 for x in NAVY])
    gold = Color(*[x/255.0 for x in GOLD])
    white = Color(*[x/255.0 for x in WHITE])
    light_gray = Color(*[x/255.0 for x in LIGHT_GRAY])
    dark_gray = Color(*[x/255.0 for x in DARK_GRAY])

    # === Gold top bar ===
    c.setFillColor(gold)
    c.rect(0, height - 8, width, 8, fill=1, stroke=0)

    # === Firm Name & Info ===
    y = height - 40
    c.setFont("Helvetica-Bold", 18)
    c.setFillColor(navy)
    c.drawString(margin, y, FIRM["name"])

    c.setFont("Helvetica", 10)
    c.setFillColor(HexColor("#333333"))
    y -= 16
    c.drawString(margin, y, FIRM["address"])
    y -= 13
    c.drawString(margin, y, FIRM["city_state"])
    y -= 13
    c.setFont("Helvetica", 9)
    c.setFillColor(dark_gray)
    c.drawString(margin, y, f"Tel: {FIRM['phone']}  |  {FIRM['email']}")
    y -= 12
    c.drawString(margin, y, FIRM["website"])

    # === INVOICE title (right side) ===
    c.setFont("Helvetica-Bold", 28)
    c.setFillColor(navy)
    c.drawRightString(width - margin, height - 45, "INVOICE")

    # === Gold divider line ===
    y -= 15
    c.setStrokeColor(gold)
    c.setLineWidth(3)
    c.line(margin, y, width - margin, y)

    # === Invoice Details (right) ===
    y -= 25
    details_y = y
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(navy)

    inv_date_str = invoice_date.strftime("%B %d, %Y") if isinstance(invoice_date, date) else str(invoice_date)
    due_date_str = due_date.strftime("%B %d, %Y") if isinstance(due_date, date) else str(due_date)

    labels = [
        ("Invoice #:", invoice_number),
        ("Date:", inv_date_str),
        ("Due Date:", due_date_str),
        ("Matter:", (description or "Legal Services")[:40]),
    ]
    for lbl, val in labels:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(dark_gray)
        c.drawRightString(440, details_y, lbl)
        c.setFont("Helvetica", 9)
        c.setFillColor(HexColor("#333333"))
        c.drawString(445, details_y, val)
        details_y -= 14

    # === Bill To (left) ===
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(navy)
    c.drawString(margin, y, "BILL TO:")
    y -= 15
    c.setFont("Helvetica-Bold", 12)
    c.setFillColor(HexColor("#333333"))
    c.drawString(margin, y, client.get("name", ""))
    y -= 14
    if client.get("address"):
        c.setFont("Helvetica", 10)
        c.drawString(margin, y, client["address"])
        y -= 13
    if client.get("email"):
        c.setFont("Helvetica", 9)
        c.setFillColor(dark_gray)
        c.drawString(margin, y, client["email"])
        y -= 13

    case_parts = []
    if client.get("case_number"):
        case_parts.append(f"Case: {client['case_number']}")
    if client.get("visa_type"):
        case_parts.append(f"Type: {client['visa_type']}")
    if case_parts:
        c.setFont("Helvetica", 9)
        c.setFillColor(dark_gray)
        c.drawString(margin, y, "  |  ".join(case_parts))
        y -= 13

    # === Line Items Table ===
    y -= 20
    table_top = y

    # Header row
    c.setFillColor(navy)
    c.rect(margin, y - 2, width - 2 * margin, 18, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin + 8, y + 3, "DESCRIPTION")
    c.drawCentredString(420, y + 3, "CATEGORY")
    c.drawRightString(width - margin - 8, y + 3, "AMOUNT")

    y -= 20

    # Build line items
    if line_items is None:
        line_items = []
        if legal_fees > 0:
            line_items.append((f"Legal Services - {description or 'Legal Fees'}", "Legal Fees", legal_fees))
        if filing_fees > 0:
            line_items.append(("USCIS Filing Fees", "Filing Fees", filing_fees))
        if other_expenses > 0:
            line_items.append(("Additional Expenses (translations, postage, etc.)", "Expenses", other_expenses))

    for i, item in enumerate(line_items):
        desc_text, cat, amount = item[0], item[1], item[2]
        if i % 2 == 1:
            c.setFillColor(light_gray)
            c.rect(margin, y - 3, width - 2 * margin, 16, fill=1, stroke=0)

        c.setFillColor(HexColor("#333333"))
        c.setFont("Helvetica", 9)
        # Truncate long descriptions
        if len(desc_text) > 55:
            desc_text = desc_text[:52] + "..."
        c.drawString(margin + 8, y + 2, desc_text)
        c.drawCentredString(420, y + 2, cat)
        c.drawRightString(width - margin - 8, y + 2, f"${amount:,.2f}")
        y -= 16

    # Divider
    y -= 5
    c.setStrokeColor(HexColor("#CCCCCC"))
    c.setLineWidth(0.5)
    c.line(300, y, width - margin, y)
    y -= 5

    # === Totals ===
    total = legal_fees + filing_fees + other_expenses
    amount_due = total - retainer_applied

    totals = [
        ("Total Legal Fees", legal_fees, False),
        ("Total Filing Fees & Expenses", filing_fees + other_expenses, False),
        ("Subtotal", total, False),
    ]
    if retainer_applied > 0:
        totals.append(("Less: Retainer Applied", -retainer_applied, False))
    totals.append(("AMOUNT DUE", amount_due, True))

    for label, value, is_total in totals:
        y -= 18
        if is_total:
            c.setFillColor(gold)
            c.rect(300, y - 4, width - margin - 300, 20, fill=1, stroke=0)
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 11)
        elif label == "Subtotal":
            c.setFillColor(light_gray)
            c.rect(300, y - 4, width - margin - 300, 18, fill=1, stroke=0)
            c.setFillColor(HexColor("#333333"))
            c.setFont("Helvetica-Bold", 10)
        else:
            c.setFillColor(HexColor("#333333"))
            c.setFont("Helvetica", 10)

        c.drawRightString(450, y, label)
        if value < 0:
            c.drawRightString(width - margin - 8, y, f"(${abs(value):,.2f})")
        else:
            c.drawRightString(width - margin - 8, y, f"${value:,.2f}")

    # === Payment Instructions ===
    y -= 40
    c.setFont("Helvetica-Bold", 10)
    c.setFillColor(navy)
    c.drawString(margin, y, "Payment Information")

    c.setFont("Helvetica", 9)
    c.setFillColor(dark_gray)
    instructions = [
        "Payment Due: Upon Receipt",
        "Check: Payable to US Immigration Group",
        f"Zelle: {FIRM['email']}",
        "Wire Transfer: Contact office for details",
    ]
    for line in instructions:
        y -= 14
        c.drawString(margin + 10, y, line)

    # === Gold bottom bar ===
    y -= 30
    c.setStrokeColor(gold)
    c.setLineWidth(3)
    c.line(margin, y, width - margin, y)

    # Footer
    y -= 18
    c.setFont("Helvetica-Oblique", 9)
    c.setFillColor(dark_gray)
    c.drawCentredString(width / 2, y, "Thank you for choosing US Immigration Group.")

    c.save()
    return filepath
