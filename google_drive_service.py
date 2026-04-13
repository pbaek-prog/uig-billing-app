"""
US Immigration Group - Google Drive File Service
Handles uploading invoices, reports, and documents to Google Drive.
Creates per-client folder structures automatically.
"""
import os
import io
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, MediaIoBaseUpload
from google_sheets_db import get_credentials
from config import (
    DRIVE_CLIENTS_FOLDER_ID, DRIVE_REPORTS_FOLDER_ID,
    DRIVE_MONTHLY_PNL_FOLDER_ID, DRIVE_ANNUAL_FOLDER_ID,
    DRIVE_TEMPLATES_FOLDER_ID,
)


def get_drive_service():
    creds = get_credentials()
    if not creds:
        return None
    return build("drive", "v3", credentials=creds)


def _find_or_create_folder(name, parent_id, service=None):
    """Find a folder by name under parent, or create it."""
    if service is None:
        service = get_drive_service()
    if not service:
        return None

    # Search for existing folder
    query = (f"name = '{name}' and '{parent_id}' in parents "
             f"and mimeType = 'application/vnd.google-apps.folder' and trashed = false")
    results = service.files().list(q=query, spaces="drive", fields="files(id, name)").execute()
    files = results.get("files", [])
    if files:
        return files[0]["id"]

    # Create new folder
    metadata = {
        "name": name,
        "mimeType": "application/vnd.google-apps.folder",
        "parents": [parent_id]
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")


def get_client_folder(client_name, case_number="", service=None):
    """Get or create a client's folder structure in Google Drive.
    Returns dict with folder IDs: {root, invoices, retainer, documents}
    """
    if service is None:
        service = get_drive_service()
    if not service:
        return None

    # Sanitize folder name
    safe_name = client_name.replace(",", "").replace(" ", "_")
    if case_number:
        safe_name = f"{safe_name}_{case_number}"

    # Create client root folder
    root_id = _find_or_create_folder(safe_name, DRIVE_CLIENTS_FOLDER_ID, service)
    if not root_id:
        return None

    # Create sub-folders
    invoices_id = _find_or_create_folder("Invoices", root_id, service)
    retainer_id = _find_or_create_folder("Retainer_Billing", root_id, service)
    documents_id = _find_or_create_folder("Documents", root_id, service)

    return {
        "root": root_id,
        "invoices": invoices_id,
        "retainer": retainer_id,
        "documents": documents_id,
    }


def upload_file(filepath, folder_id, filename=None, mime_type=None, service=None):
    """Upload a local file to Google Drive.
    Returns the Drive file ID and web view link.
    """
    if service is None:
        service = get_drive_service()
    if not service:
        return None

    if filename is None:
        filename = os.path.basename(filepath)

    if mime_type is None:
        ext = os.path.splitext(filepath)[1].lower()
        mime_map = {
            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".pdf": "application/pdf",
            ".csv": "text/csv",
            ".png": "image/png",
            ".jpg": "image/jpeg",
        }
        mime_type = mime_map.get(ext, "application/octet-stream")

    metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    media = MediaFileUpload(filepath, mimetype=mime_type, resumable=True)
    file = service.files().create(
        body=metadata, media_body=media, fields="id, webViewLink"
    ).execute()

    return {
        "id": file.get("id"),
        "link": file.get("webViewLink"),
    }


def upload_invoice(filepath, client_name, case_number=""):
    """Upload an invoice to the client's Invoices folder on Drive.
    Returns Drive file info dict or None.
    """
    service = get_drive_service()
    if not service:
        return None

    folders = get_client_folder(client_name, case_number, service)
    if not folders or not folders.get("invoices"):
        return None

    return upload_file(filepath, folders["invoices"], service=service)


def upload_report(filepath, report_type="monthly"):
    """Upload a report to the Reports folder.
    report_type: 'monthly' or 'annual'
    """
    service = get_drive_service()
    if not service:
        return None

    folder_id = DRIVE_MONTHLY_PNL_FOLDER_ID if report_type == "monthly" else DRIVE_ANNUAL_FOLDER_ID
    return upload_file(filepath, folder_id, service=service)


def upload_document(filepath, client_name, case_number="", subfolder="documents"):
    """Upload a general document to a client's folder.
    subfolder: 'documents', 'retainer', or 'invoices'
    """
    service = get_drive_service()
    if not service:
        return None

    folders = get_client_folder(client_name, case_number, service)
    if not folders:
        return None

    folder_id = folders.get(subfolder, folders.get("documents"))
    return upload_file(filepath, folder_id, service=service)


def list_client_files(client_name, case_number="", subfolder=None):
    """List files in a client's Drive folder."""
    service = get_drive_service()
    if not service:
        return []

    folders = get_client_folder(client_name, case_number, service)
    if not folders:
        return []

    folder_id = folders.get(subfolder, folders.get("root")) if subfolder else folders["root"]

    # If listing root, search recursively
    if subfolder:
        query = f"'{folder_id}' in parents and trashed = false"
    else:
        query = f"('{folders['root']}' in parents or '{folders['invoices']}' in parents or '{folders['retainer']}' in parents or '{folders['documents']}' in parents) and trashed = false"

    results = service.files().list(
        q=query, spaces="drive",
        fields="files(id, name, mimeType, modifiedTime, webViewLink, size)",
        orderBy="modifiedTime desc"
    ).execute()

    return results.get("files", [])


def get_file_link(file_id):
    """Get the web view link for a Drive file."""
    service = get_drive_service()
    if not service:
        return None
    try:
        f = service.files().get(fileId=file_id, fields="webViewLink").execute()
        return f.get("webViewLink")
    except Exception:
        return None
