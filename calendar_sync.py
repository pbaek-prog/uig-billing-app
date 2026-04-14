"""
Google Calendar 동기화 모듈 - UIG Billing App
데드라인과 법정 기일을 자동으로 Google Calendar에 동기화합니다.

주의: OAuth 재인증 필요 — scope 추가:
    https://www.googleapis.com/auth/calendar
"""

from datetime import datetime, timedelta
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


CALENDAR_SCOPE = "https://www.googleapis.com/auth/calendar"
DEFAULT_TIMEZONE = "America/Chicago"  # Illinois (Mount Prospect)


def get_calendar_service(credentials):
    """Google Calendar API 서비스 객체 반환."""
    return build("calendar", "v3", credentials=credentials, cache_discovery=False)


def create_calendar_event(
    credentials,
    title,
    event_date,
    description="",
    client_name="",
    case_number="",
    location="",
    reminder_minutes=(1440, 60),  # 하루 전, 한 시간 전
    calendar_id="primary",
    all_day=True,
):
    """
    캘린더 이벤트 생성.

    Args:
        credentials: Google OAuth2 credentials
        title: 이벤트 제목 (예: "USCIS Filing Deadline")
        event_date: date 또는 datetime 객체, 또는 'YYYY-MM-DD' 문자열
        description: 상세 설명
        client_name: 클라이언트 이름 (제목에 자동 추가)
        case_number: 케이스 번호
        location: 장소 (법원 주소 등)
        reminder_minutes: 알림 시간 (분 단위 튜플)
        calendar_id: 대상 캘린더 ID, 기본값 'primary'
        all_day: True면 종일 이벤트

    Returns:
        dict with 'event_id' and 'html_link'
    """
    service = get_calendar_service(credentials)

    # 날짜 처리
    if isinstance(event_date, str):
        dt = datetime.strptime(event_date, "%Y-%m-%d")
    elif isinstance(event_date, datetime):
        dt = event_date
    else:
        dt = datetime.combine(event_date, datetime.min.time())

    # 제목 구성
    full_title = title
    if client_name:
        full_title = f"[{client_name}] {title}"
    if case_number:
        full_title += f" ({case_number})"

    # 설명에 자동 태그 추가
    desc_parts = [description] if description else []
    desc_parts.append("\n--- Auto-synced from UIG Billing App ---")
    if client_name:
        desc_parts.append(f"Client: {client_name}")
    if case_number:
        desc_parts.append(f"Case: {case_number}")
    full_desc = "\n".join(desc_parts)

    event_body = {
        "summary": full_title,
        "description": full_desc,
        "reminders": {
            "useDefault": False,
            "overrides": [
                {"method": "popup", "minutes": m} for m in reminder_minutes
            ] + [
                {"method": "email", "minutes": reminder_minutes[0]}
            ],
        },
    }

    if location:
        event_body["location"] = location

    if all_day:
        date_str = dt.strftime("%Y-%m-%d")
        end_str = (dt + timedelta(days=1)).strftime("%Y-%m-%d")
        event_body["start"] = {"date": date_str}
        event_body["end"] = {"date": end_str}
    else:
        event_body["start"] = {
            "dateTime": dt.isoformat(),
            "timeZone": DEFAULT_TIMEZONE,
        }
        event_body["end"] = {
            "dateTime": (dt + timedelta(hours=1)).isoformat(),
            "timeZone": DEFAULT_TIMEZONE,
        }

    try:
        created = service.events().insert(
            calendarId=calendar_id, body=event_body
        ).execute()
        return {
            "success": True,
            "event_id": created.get("id"),
            "html_link": created.get("htmlLink"),
        }
    except HttpError as e:
        return {"success": False, "error": str(e)}


def update_calendar_event(
    credentials, event_id, updates, calendar_id="primary"
):
    """기존 이벤트 업데이트. updates는 Google Calendar API 필드."""
    service = get_calendar_service(credentials)
    try:
        event = service.events().get(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        event.update(updates)
        updated = service.events().update(
            calendarId=calendar_id, eventId=event_id, body=event
        ).execute()
        return {"success": True, "event_id": updated.get("id")}
    except HttpError as e:
        return {"success": False, "error": str(e)}


def delete_calendar_event(credentials, event_id, calendar_id="primary"):
    """이벤트 삭제 (데드라인 완료/취소 시)."""
    service = get_calendar_service(credentials)
    try:
        service.events().delete(
            calendarId=calendar_id, eventId=event_id
        ).execute()
        return {"success": True}
    except HttpError as e:
        # 이미 삭제된 이벤트면 무시
        if e.resp.status in (404, 410):
            return {"success": True, "note": "already_deleted"}
        return {"success": False, "error": str(e)}


def list_calendars(credentials):
    """사용자가 접근 가능한 캘린더 목록."""
    service = get_calendar_service(credentials)
    try:
        result = service.calendarList().list().execute()
        return [
            {
                "id": c["id"],
                "summary": c.get("summary", ""),
                "primary": c.get("primary", False),
            }
            for c in result.get("items", [])
        ]
    except HttpError as e:
        return []


def sync_deadline_to_calendar(
    credentials,
    sheets_service,
    spreadsheet_id,
    deadline_row_index,
    deadline_data,
    calendar_id="primary",
):
    """
    단일 데드라인을 캘린더에 동기화하고 Sheet에 event_id 저장.

    deadline_data 예시:
        {
            "client_name": "John Doe",
            "case_number": "I-130-2026-001",
            "deadline_type": "USCIS RFE Response",
            "due_date": "2026-05-15",
            "description": "Respond to RFE regarding...",
        }
    deadline_row_index: Sheets 행 번호 (1-based, 헤더 포함)
    """
    title = deadline_data.get("deadline_type", "Legal Deadline")
    result = create_calendar_event(
        credentials=credentials,
        title=title,
        event_date=deadline_data.get("due_date"),
        description=deadline_data.get("description", ""),
        client_name=deadline_data.get("client_name", ""),
        case_number=deadline_data.get("case_number", ""),
        calendar_id=calendar_id,
    )

    if result.get("success") and sheets_service and spreadsheet_id:
        # event_id를 Deadlines 시트의 해당 행에 기록
        try:
            # Deadlines 시트에 calendar_event_id 열이 있다고 가정 (M열)
            range_name = f"Deadlines!M{deadline_row_index}"
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=range_name,
                valueInputOption="RAW",
                body={"values": [[result["event_id"]]]},
            ).execute()
        except Exception:
            pass

    return result


def sync_all_pending_deadlines(
    credentials, sheets_service, spreadsheet_id, calendar_id="primary"
):
    """
    Deadlines 시트에서 미동기화(event_id 비어있음) & 미완료 항목을 모두 동기화.
    """
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Deadlines!A:N",
        ).execute()
        rows = result.get("values", [])
    except Exception as e:
        return {"synced": 0, "failed": 0, "error": str(e)}

    if not rows or len(rows) < 2:
        return {"synced": 0, "failed": 0}

    headers = rows[0]
    # 열 인덱스 찾기
    def col_idx(name):
        try:
            return headers.index(name)
        except ValueError:
            return -1

    idx_client = col_idx("Client Name")
    idx_case = col_idx("Case Number")
    idx_type = col_idx("Deadline Type")
    idx_due = col_idx("Due Date")
    idx_desc = col_idx("Description")
    idx_status = col_idx("Status")
    idx_event = col_idx("Calendar Event ID")

    synced, failed, skipped = 0, 0, 0
    errors = []

    for i, row in enumerate(rows[1:], start=2):
        def safe(idx):
            return row[idx] if idx >= 0 and idx < len(row) else ""

        status = safe(idx_status).lower()
        existing_event = safe(idx_event)

        if status in ("completed", "cancelled", "done"):
            skipped += 1
            continue
        if existing_event:
            skipped += 1
            continue

        due_date = safe(idx_due)
        if not due_date:
            skipped += 1
            continue

        deadline_data = {
            "client_name": safe(idx_client),
            "case_number": safe(idx_case),
            "deadline_type": safe(idx_type),
            "due_date": due_date,
            "description": safe(idx_desc),
        }

        res = sync_deadline_to_calendar(
            credentials=credentials,
            sheets_service=sheets_service,
            spreadsheet_id=spreadsheet_id,
            deadline_row_index=i,
            deadline_data=deadline_data,
            calendar_id=calendar_id,
        )
        if res.get("success"):
            synced += 1
        else:
            failed += 1
            errors.append(f"Row {i}: {res.get('error', 'unknown')}")

    return {
        "synced": synced,
        "failed": failed,
        "skipped": skipped,
        "errors": errors,
    }


def ensure_calendar_event_id_column(sheets_service, spreadsheet_id):
    """Deadlines 시트에 'Calendar Event ID' 열이 없으면 추가."""
    try:
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Deadlines!1:1",
        ).execute()
        headers = result.get("values", [[]])[0]
        if "Calendar Event ID" not in headers:
            new_col = len(headers) + 1
            # 마지막 열 다음에 추가
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=f"Deadlines!{_col_letter(new_col)}1",
                valueInputOption="RAW",
                body={"values": [["Calendar Event ID"]]},
            ).execute()
            return True
        return False
    except Exception:
        return False


def _col_letter(col_num):
    """1 -> A, 27 -> AA 등 변환."""
    letters = ""
    while col_num > 0:
        col_num, rem = divmod(col_num - 1, 26)
        letters = chr(65 + rem) + letters
    return letters
