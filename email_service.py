"""Email service for US Immigration Group - invoice emails, payment reminders, deadline alerts."""
import smtplib
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

FIRM = {
    "name": "US Immigration Group",
    "address": "800 E. Northwest Hwy. Ste 205, Mount Prospect, IL 60016",
    "phone": "(847) 449-8660",
    "email": "info@usimmigrationgroup.org",
    "website": "www.usimmigrationgroup.org",
}


def build_invoice_email_html(client_name, invoice_number, description,
                              total_amount, amount_due, due_date_str, case_number=""):
    """Build professional HTML invoice email."""
    subject = f"Invoice #{invoice_number} - {FIRM['name']}"
    html = f"""<html><body style="font-family:Arial,sans-serif;color:#333;max-width:700px;margin:0 auto;">
<div style="background:linear-gradient(135deg,#1A3C5E,#2E5A8A);color:white;padding:20px;text-align:center;">
<h1 style="margin:0;font-size:22px;letter-spacing:1px;">{FIRM['name'].upper()}</h1>
<p style="margin:5px 0 0;font-size:12px;color:#F5A623;">{FIRM['address']}</p>
<p style="margin:2px 0 0;font-size:12px;color:#ddd;">Tel: {FIRM['phone']} | {FIRM['email']}</p></div>
<div style="border-top:4px solid #F5A623;padding:25px;border:1px solid #ddd;border-top:4px solid #F5A623;">
<h2 style="color:#1A3C5E;border-bottom:2px solid #1A3C5E;padding-bottom:8px;margin-top:0;">INVOICE #{invoice_number}</h2>
<table style="width:100%;margin-bottom:20px;"><tr>
<td style="vertical-align:top;width:50%;"><strong>Client:</strong> {client_name}<br>
{f'<strong>Case:</strong> {case_number}<br>' if case_number else ''}
<strong>Matter:</strong> {description}</td>
<td style="vertical-align:top;width:50%;text-align:right;">
<strong>Due Date:</strong> <span style="color:#CC0000;font-weight:bold;">{due_date_str}</span></td></tr></table>
<table style="width:100%;border-collapse:collapse;margin-bottom:20px;">
<tr style="background:#1A3C5E;color:white;">
<td style="padding:12px;font-size:14px;"><strong>Total Charges</strong></td>
<td style="padding:12px;text-align:right;font-size:14px;"><strong>${total_amount:,.2f}</strong></td></tr>
<tr style="background:#F5A623;color:white;">
<td style="padding:14px;font-size:16px;"><strong>AMOUNT DUE</strong></td>
<td style="padding:14px;text-align:right;font-size:16px;"><strong>${amount_due:,.2f}</strong></td></tr></table>
<div style="background:#f0f7ff;padding:15px;border-radius:5px;border-left:4px solid #1A3C5E;margin-bottom:20px;">
<strong style="color:#1A3C5E;">Payment Information:</strong>
<ul style="margin:8px 0;color:#555;">
<li>Make checks payable to: <strong>US Immigration Group</strong></li>
<li>Zelle: <strong>{FIRM['email']}</strong></li>
<li>Wire Transfer: Contact office for details</li>
<li>Mail: {FIRM['address']}</li></ul></div>
<p style="font-size:12px;color:#666;border-top:1px solid #ddd;padding-top:15px;">
Questions? Contact us at {FIRM['email']} or {FIRM['phone']}</p></div>
<div style="background:#f5f5f5;padding:10px;text-align:center;font-size:11px;color:#999;">
&copy; 2026 {FIRM['name']} | {FIRM['website']}</div></body></html>"""
    return subject, html


def build_invoice_email(client_name, invoice_number, description,
                        total_amount, amount_due, due_date_str, case_number=""):
    """Build plain text invoice email."""
    subject = f"Invoice #{invoice_number} - {FIRM['name']}"
    body = f"""Dear {client_name},

Please find your invoice #{invoice_number} for legal services.

    Matter: {description}
    {f'Case Number: {case_number}' if case_number else ''}
    Total Charges: ${total_amount:,.2f}
    Amount Due: ${amount_due:,.2f}
    Due Date: {due_date_str}

Payment Methods:
  - Check payable to: US Immigration Group
  - Zelle: {FIRM['email']}
  - Wire Transfer: Contact our office for details
  - Mail to: {FIRM['address']}

If you have any questions regarding this invoice, please contact us at {FIRM['email']} or {FIRM['phone']}.

Thank you for choosing US Immigration Group.

Best regards,
{FIRM['name']}
{FIRM['address']}
{FIRM['phone']}
"""
    return subject, body


def build_past_due_email(client_name, invoices_info):
    """Build past-due reminder email."""
    total_owed = sum(inv["amount_due"] for inv in invoices_info)
    invoice_lines = "\n".join(
        f"    - Invoice #{inv['invoice_number']}: ${inv['amount_due']:,.2f} "
        f"(due {inv['due_date']}, {inv['days_overdue']} days overdue)"
        for inv in invoices_info
    )
    subject = f"PAST DUE NOTICE - ${total_owed:,.2f} Outstanding - {FIRM['name']}"
    body = f"""Dear {client_name},

This is a reminder that the following invoice(s) are past due:

{invoice_lines}

    Total Outstanding: ${total_owed:,.2f}

Please remit payment at your earliest convenience. If you have already sent payment, please disregard this notice.

If you need to discuss payment arrangements, please contact us at {FIRM['email']} or {FIRM['phone']}.

Thank you,
{FIRM['name']}
{FIRM['address']}
"""
    return subject, body


def build_deadline_reminder_email(client_name, deadline_type, deadline_date, description, case_number=""):
    """Build a case deadline reminder email."""
    subject = f"Case Deadline Reminder: {deadline_type} - {FIRM['name']}"
    body = f"""Dear {client_name},

This is a reminder about an upcoming deadline for your case{f' ({case_number})' if case_number else ''}:

    Deadline Type: {deadline_type}
    Date: {deadline_date}
    Details: {description}

Please ensure all required documents and information are submitted before this date. If you have questions or need assistance, please contact our office immediately.

Best regards,
{FIRM['name']}
{FIRM['address']}
{FIRM['phone']}
"""
    return subject, body


def send_email_smtp(sender_email, app_password, recipient, subject, body, attachment_path=None, is_html=False):
    """Send email via Gmail SMTP."""
    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html" if is_html else "plain"))

    if attachment_path and os.path.exists(attachment_path):
        with open(attachment_path, "rb") as f:
            part = MIMEBase("application", "octet-stream")
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header("Content-Disposition",
                          f"attachment; filename={os.path.basename(attachment_path)}")
            msg.attach(part)

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
    return True


def simulate_send_email(recipient, subject, body, attachment_path=None):
    """Simulate sending email (demo mode)."""
    att_info = f"\n    Attachment: {os.path.basename(attachment_path)}" if attachment_path else ""
    return f"""--- EMAIL PREVIEW ---
To: {recipient}
Subject: {subject}{att_info}

{body[:500]}{'...' if len(body) > 500 else ''}
--- END PREVIEW ---"""
