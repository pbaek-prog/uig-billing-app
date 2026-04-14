"""
e-Signature 모듈 - UIG Billing App
전자서명 기능: 서명 패드 캡처, PDF에 서명 삽입, 서명된 PDF 클라이언트 폴더 저장.

사용 라이브러리:
    - streamlit-drawable-canvas: 서명 패드
    - pypdf: PDF 조작
    - reportlab: 서명 이미지를 PDF 레이어로 변환
    - Pillow: 이미지 처리
"""

import io
import os
import hashlib
from datetime import datetime
from PIL import Image

try:
    from pypdf import PdfReader, PdfWriter
    from pypdf.generic import RectangleObject
except ImportError:
    PdfReader = None
    PdfWriter = None

try:
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.lib.pagesizes import letter
except ImportError:
    rl_canvas = None

try:
    from googleapiclient.http import MediaInMemoryUpload
except ImportError:
    MediaInMemoryUpload = None


def signature_canvas_component(key="signature_pad", height=200, width=600):
    """
    Streamlit UI에 서명 패드 렌더링.
    반환값: PIL Image 또는 None
    """
    try:
        from streamlit_drawable_canvas import st_canvas
        import streamlit as st
    except ImportError:
        import streamlit as st
        st.error("streamlit-drawable-canvas 패키지가 설치되어 있지 않습니다. requirements.txt 확인 후 재배포하세요.")
        return None

    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=2,
        stroke_color="#000000",
        background_color="#ffffff",
        height=height,
        width=width,
        drawing_mode="freedraw",
        key=key,
    )

    if canvas_result.image_data is not None:
        # numpy array -> PIL Image
        img_arr = canvas_result.image_data.astype("uint8")
        img = Image.fromarray(img_arr)
        # 투명 영역을 흰색으로 합성 (서명이 비어있으면 None 반환)
        if _is_blank_signature(img):
            return None
        return img
    return None


def _is_blank_signature(img, threshold=250):
    """서명이 비어있는지 판정 (거의 흰색/투명만 있는지)."""
    gray = img.convert("L")
    pixels = list(gray.getdata())
    dark_pixels = sum(1 for p in pixels if p < threshold)
    # 어두운 픽셀이 50개 미만이면 빈 서명으로 간주
    return dark_pixels < 50


def signature_to_png_bytes(pil_image, trim=True):
    """PIL 서명 이미지를 PNG 바이트로 변환. 투명 배경 유지."""
    img = pil_image.copy()

    # 흰 배경을 투명으로
    img = img.convert("RGBA")
    data = img.getdata()
    new_data = []
    for item in data:
        # 거의 흰색이면 투명
        if item[0] > 240 and item[1] > 240 and item[2] > 240:
            new_data.append((255, 255, 255, 0))
        else:
            new_data.append(item)
    img.putdata(new_data)

    if trim:
        img = _trim_transparent(img)

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf.getvalue()


def _trim_transparent(img):
    """투명 영역 잘라내기."""
    bbox = img.getbbox()
    if bbox:
        return img.crop(bbox)
    return img


def apply_signature_to_pdf(
    pdf_bytes,
    signature_png_bytes,
    page_num=None,
    x=100,
    y=100,
    width=150,
    height=50,
    add_metadata=True,
    signer_name="",
):
    """
    PDF에 서명 이미지 삽입.

    Args:
        pdf_bytes: 원본 PDF 바이트
        signature_png_bytes: 서명 PNG 바이트 (투명 배경)
        page_num: 삽입할 페이지 (0-indexed). None이면 마지막 페이지.
        x, y: PDF 좌하단 기준 좌표 (points; 72 = 1 inch)
        width, height: 서명 크기 (points)
        add_metadata: 서명 메타데이터 추가 여부
        signer_name: 서명자 이름 (메타데이터용)

    Returns:
        서명된 PDF 바이트
    """
    if not PdfReader or not rl_canvas:
        raise ImportError("pypdf 또는 reportlab이 설치되어 있지 않습니다.")

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()

    total_pages = len(reader.pages)
    if page_num is None:
        page_num = total_pages - 1
    if page_num < 0 or page_num >= total_pages:
        raise ValueError(f"잘못된 페이지 번호: {page_num} (총 {total_pages}페이지)")

    # 대상 페이지 크기 가져오기
    target_page = reader.pages[page_num]
    page_box = target_page.mediabox
    page_width = float(page_box.width)
    page_height = float(page_box.height)

    # 서명 레이어 PDF 생성
    sig_layer_buf = io.BytesIO()
    c = rl_canvas.Canvas(sig_layer_buf, pagesize=(page_width, page_height))

    # 서명 이미지를 임시 파일처럼 ImageReader로 읽기
    from reportlab.lib.utils import ImageReader
    sig_img = ImageReader(io.BytesIO(signature_png_bytes))
    c.drawImage(
        sig_img, x, y, width=width, height=height,
        mask="auto", preserveAspectRatio=True
    )

    # 서명 메타데이터 텍스트 (서명 아래)
    if add_metadata:
        c.setFont("Helvetica", 7)
        meta_y = y - 10
        if signer_name:
            c.drawString(x, meta_y, f"Signed by: {signer_name}")
            meta_y -= 8
        c.drawString(x, meta_y, f"Signed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} CT")
        sig_hash = hashlib.sha256(signature_png_bytes).hexdigest()[:16]
        c.drawString(x, meta_y - 8, f"Sig-ID: {sig_hash}")

    c.save()
    sig_layer_buf.seek(0)

    sig_reader = PdfReader(sig_layer_buf)
    sig_page = sig_reader.pages[0]

    # 모든 페이지를 복사하면서 대상 페이지에만 서명 병합
    for i, page in enumerate(reader.pages):
        if i == page_num:
            page.merge_page(sig_page)
        writer.add_page(page)

    # 문서 메타데이터
    if add_metadata:
        writer.add_metadata({
            "/Signer": signer_name or "Unknown",
            "/SignedAt": datetime.now().isoformat(),
            "/SignedBy": "UIG Billing App e-Signature",
        })

    out = io.BytesIO()
    writer.write(out)
    out.seek(0)
    return out.getvalue()


def save_signed_pdf_to_drive(
    drive_service,
    signed_pdf_bytes,
    file_name,
    client_folder_id,
    subfolder_name="Forms",
):
    """
    서명된 PDF를 클라이언트 Drive 폴더에 저장.
    client_portal.get_subfolder_id와 함께 사용.
    """
    if not MediaInMemoryUpload:
        raise ImportError("googleapiclient가 설치되어 있지 않습니다.")

    # 서명 완료 타임스탬프 파일명에 추가
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    base, ext = os.path.splitext(file_name)
    if not ext:
        ext = ".pdf"
    signed_name = f"{base}_SIGNED_{ts}{ext}"

    # 대상 폴더 결정
    target_folder_id = client_folder_id
    if subfolder_name:
        try:
            from client_portal import get_subfolder_id
            sub_id = get_subfolder_id(drive_service, client_folder_id, subfolder_name)
            if sub_id:
                target_folder_id = sub_id
        except Exception:
            pass

    metadata = {
        "name": signed_name,
        "parents": [target_folder_id],
    }
    media = MediaInMemoryUpload(signed_pdf_bytes, mimetype="application/pdf")
    file = drive_service.files().create(
        body=metadata,
        media_body=media,
        fields="id, webViewLink, name",
    ).execute()
    return {
        "file_id": file.get("id"),
        "web_link": file.get("webViewLink"),
        "name": file.get("name"),
    }


def create_signature_request(
    sheets_service,
    spreadsheet_id,
    client_name,
    client_id,
    document_name,
    document_drive_id,
    requested_by,
    notes="",
):
    """
    서명 요청 레코드 생성. Signature_Requests 시트에 저장.
    상태: pending -> signed / cancelled
    """
    ensure_signature_sheet(sheets_service, spreadsheet_id)

    request_id = f"SIG-{datetime.now().strftime('%Y%m%d%H%M%S')}-{hashlib.md5(client_id.encode()).hexdigest()[:6].upper()}"

    row = [
        request_id,
        datetime.now().isoformat(),
        client_id,
        client_name,
        document_name,
        document_drive_id,
        requested_by,
        "pending",
        "",  # signed_at
        "",  # signed_doc_drive_id
        "",  # signature_hash
        notes,
    ]

    sheets_service.spreadsheets().values().append(
        spreadsheetId=spreadsheet_id,
        range="Signature_Requests!A:L",
        valueInputOption="USER_ENTERED",
        insertDataOption="INSERT_ROWS",
        body={"values": [row]},
    ).execute()

    return request_id


def ensure_signature_sheet(sheets_service, spreadsheet_id):
    """Signature_Requests 시트 생성 (없으면)."""
    try:
        meta = sheets_service.spreadsheets().get(
            spreadsheetId=spreadsheet_id
        ).execute()
        sheet_names = [s["properties"]["title"] for s in meta.get("sheets", [])]

        if "Signature_Requests" not in sheet_names:
            sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=spreadsheet_id,
                body={
                    "requests": [{
                        "addSheet": {
                            "properties": {"title": "Signature_Requests"}
                        }
                    }]
                },
            ).execute()

            headers = [[
                "Request ID", "Created At", "Client ID", "Client Name",
                "Document Name", "Document Drive ID", "Requested By",
                "Status", "Signed At", "Signed Doc Drive ID",
                "Signature Hash", "Notes",
            ]]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="Signature_Requests!A1",
                valueInputOption="RAW",
                body={"values": headers},
            ).execute()
            return True
        return False
    except Exception:
        return False


def get_pending_signature_requests(sheets_service, spreadsheet_id, client_id=None):
    """pending 상태 서명 요청 조회. client_id 지정 시 해당 클라이언트만."""
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Signature_Requests!A:L",
        ).execute()
        rows = result.get("values", [])
    except Exception:
        return []

    if not rows or len(rows) < 2:
        return []

    headers = rows[0]
    pending = []
    for i, row in enumerate(rows[1:], start=2):
        while len(row) < len(headers):
            row.append("")
        record = dict(zip(headers, row))
        record["_row"] = i
        if record.get("Status") != "pending":
            continue
        if client_id and record.get("Client ID") != client_id:
            continue
        pending.append(record)
    return pending


def mark_signature_complete(
    sheets_service,
    spreadsheet_id,
    request_id,
    signed_doc_drive_id,
    signature_hash,
):
    """서명 요청을 'signed' 상태로 업데이트."""
    result = sheets_service.spreadsheets().values().get(
        spreadsheetId=spreadsheet_id,
        range="Signature_Requests!A:L",
    ).execute()
    rows = result.get("values", [])

    for i, row in enumerate(rows[1:], start=2):
        if row and row[0] == request_id:
            updates = [[
                "signed",
                datetime.now().isoformat(),
                signed_doc_drive_id,
                signature_hash,
            ]]
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"Signature_Requests!H{i}:K{i}",
                valueInputOption="RAW",
                body={"values": updates},
            ).execute()
            return True
    return False


def download_drive_pdf(drive_service, file_id):
    """Drive에서 PDF 바이트 다운로드."""
    from googleapiclient.http import MediaIoBaseDownload
    request = drive_service.files().get_media(fileId=file_id)
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    buf.seek(0)
    return buf.getvalue()
