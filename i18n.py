"""
Internationalization (i18n) Module
Multi-language support for UIG Billing System.
Supports: English, Korean, Spanish, Chinese (Simplified)
"""

TRANSLATIONS = {
    "en": {
        # Navigation
        "nav_dashboard": "Dashboard",
        "nav_invoice": "Invoice & Email",
        "nav_past_due": "Past Due & Alerts",
        "nav_payment": "Payment Tracking",
        "nav_trust": "Trust Account (IOLTA)",
        "nav_expenses": "Expenses",
        "nav_clients": "Clients & Cases",
        "nav_reports": "Reports & P&L",
        "nav_audit": "Audit Log",
        "nav_backup": "Backup & Export",
        "nav_ai": "AI Assistant",
        "nav_gmail": "Gmail Setup",
        "nav_uscis": "USCIS Tracker",
        "nav_court": "Court Cases",
        "nav_portal": "Client Portal",

        # Dashboard
        "dashboard_title": "Dashboard",
        "dashboard_subtitle": "Billing Overview",
        "active_clients": "Active Clients",
        "total_billed": "Total Billed",
        "outstanding": "Outstanding",
        "net_income": "Net Income",
        "trust_balance": "Trust Balance (IOLTA)",
        "refresh": "Refresh",
        "client_billing_summary": "Client Billing Summary",
        "revenue_by_client": "Revenue by Client",

        # Invoice
        "create_invoice": "Create Invoice",
        "select_client": "Select Client",
        "invoice_amount": "Amount",
        "invoice_description": "Description",
        "due_date": "Due Date",
        "generate_invoice": "Generate Invoice",
        "send_invoice": "Send Invoice",

        # Payments
        "record_payment": "Record Payment",
        "payment_amount": "Payment Amount",
        "payment_method": "Payment Method",
        "payment_date": "Payment Date",
        "payment_reference": "Reference Number",

        # Trust Account
        "trust_deposit": "Deposit",
        "trust_withdrawal": "Withdrawal",
        "trust_description": "Description",
        "trust_reference": "Reference",

        # Clients
        "add_client": "Add Client",
        "client_name": "Client Name",
        "client_email": "Email",
        "client_phone": "Phone",
        "case_type": "Case Type",
        "case_number": "Case Number",

        # USCIS
        "uscis_title": "USCIS Case Tracker",
        "receipt_number": "Receipt Number",
        "check_status": "Check Status",
        "case_status": "Case Status",
        "last_checked": "Last Checked",

        # Court
        "court_title": "Court Cases & e-Filing",
        "add_case": "Add Court Case",
        "case_name": "Case Name",
        "court_name": "Court",
        "judge": "Judge",
        "filing_deadline": "Filing Deadline",

        # Client Portal
        "portal_title": "Client Portal Management",
        "generate_code": "Generate Access Code",
        "portal_access": "Portal Access",

        # Common
        "save": "Save",
        "cancel": "Cancel",
        "delete": "Delete",
        "edit": "Edit",
        "search": "Search",
        "filter": "Filter",
        "export": "Export",
        "status": "Status",
        "date": "Date",
        "amount": "Amount",
        "notes": "Notes",
        "actions": "Actions",
        "no_data": "No data available",
        "success": "Success",
        "error": "Error",
        "confirm": "Confirm",
        "loading": "Loading...",

        # Login
        "login_title": "Legal Billing System",
        "password": "Password",
        "login": "Login",
        "forgot_password": "Forgot Password?",
        "client_login": "Client Portal Login",
        "access_code": "Access Code",
        "enter_access_code": "Enter your access code",
    },

    "ko": {
        # Navigation
        "nav_dashboard": "대시보드",
        "nav_invoice": "인보이스 & 이메일",
        "nav_past_due": "미납 & 알림",
        "nav_payment": "결제 관리",
        "nav_trust": "신탁계좌 (IOLTA)",
        "nav_expenses": "비용",
        "nav_clients": "고객 & 케이스",
        "nav_reports": "보고서 & 손익",
        "nav_audit": "감사 로그",
        "nav_backup": "백업 & 내보내기",
        "nav_ai": "AI 어시스턴트",
        "nav_gmail": "Gmail 설정",
        "nav_uscis": "USCIS 추적",
        "nav_court": "법원 케이스",
        "nav_portal": "고객 포털",

        # Dashboard
        "dashboard_title": "대시보드",
        "dashboard_subtitle": "빌링 개요",
        "active_clients": "활성 고객",
        "total_billed": "총 청구액",
        "outstanding": "미수금",
        "net_income": "순수익",
        "trust_balance": "신탁잔액 (IOLTA)",
        "refresh": "새로고침",
        "client_billing_summary": "고객별 빌링 요약",
        "revenue_by_client": "고객별 수익",

        # Invoice
        "create_invoice": "인보이스 생성",
        "select_client": "고객 선택",
        "invoice_amount": "금액",
        "invoice_description": "설명",
        "due_date": "납부기한",
        "generate_invoice": "인보이스 생성",
        "send_invoice": "인보이스 전송",

        # Payments
        "record_payment": "결제 기록",
        "payment_amount": "결제 금액",
        "payment_method": "결제 방법",
        "payment_date": "결제 일자",
        "payment_reference": "참조 번호",

        # Trust Account
        "trust_deposit": "입금",
        "trust_withdrawal": "출금",
        "trust_description": "설명",
        "trust_reference": "참조",

        # Clients
        "add_client": "고객 추가",
        "client_name": "고객명",
        "client_email": "이메일",
        "client_phone": "전화번호",
        "case_type": "케이스 유형",
        "case_number": "케이스 번호",

        # USCIS
        "uscis_title": "USCIS 케이스 추적",
        "receipt_number": "접수 번호",
        "check_status": "상태 확인",
        "case_status": "케이스 상태",
        "last_checked": "마지막 확인",

        # Court
        "court_title": "법원 케이스 & 전자제출",
        "add_case": "법원 케이스 추가",
        "case_name": "케이스명",
        "court_name": "법원",
        "judge": "판사",
        "filing_deadline": "제출 기한",

        # Client Portal
        "portal_title": "고객 포털 관리",
        "generate_code": "접근 코드 생성",
        "portal_access": "포털 접근",

        # Common
        "save": "저장",
        "cancel": "취소",
        "delete": "삭제",
        "edit": "편집",
        "search": "검색",
        "filter": "필터",
        "export": "내보내기",
        "status": "상태",
        "date": "날짜",
        "amount": "금액",
        "notes": "메모",
        "actions": "작업",
        "no_data": "데이터가 없습니다",
        "success": "성공",
        "error": "오류",
        "confirm": "확인",
        "loading": "로딩 중...",

        # Login
        "login_title": "법률 빌링 시스템",
        "password": "비밀번호",
        "login": "로그인",
        "forgot_password": "비밀번호를 잊으셨나요?",
        "client_login": "고객 포털 로그인",
        "access_code": "접근 코드",
        "enter_access_code": "접근 코드를 입력하세요",
    },

    "es": {
        # Navigation
        "nav_dashboard": "Tablero",
        "nav_invoice": "Facturas y Correo",
        "nav_past_due": "Vencidos y Alertas",
        "nav_payment": "Seguimiento de Pagos",
        "nav_trust": "Cuenta Fiduciaria (IOLTA)",
        "nav_expenses": "Gastos",
        "nav_clients": "Clientes y Casos",
        "nav_reports": "Informes y P&L",
        "nav_audit": "Registro de Auditoría",
        "nav_backup": "Respaldo y Exportar",
        "nav_ai": "Asistente IA",
        "nav_gmail": "Configurar Gmail",
        "nav_uscis": "Rastreo USCIS",
        "nav_court": "Casos Judiciales",
        "nav_portal": "Portal de Clientes",

        # Dashboard
        "dashboard_title": "Tablero",
        "dashboard_subtitle": "Resumen de Facturación",
        "active_clients": "Clientes Activos",
        "total_billed": "Total Facturado",
        "outstanding": "Pendiente",
        "net_income": "Ingreso Neto",
        "trust_balance": "Saldo Fiduciario (IOLTA)",
        "refresh": "Actualizar",
        "client_billing_summary": "Resumen de Facturación por Cliente",
        "revenue_by_client": "Ingresos por Cliente",

        # Common
        "save": "Guardar",
        "cancel": "Cancelar",
        "delete": "Eliminar",
        "edit": "Editar",
        "search": "Buscar",
        "filter": "Filtrar",
        "export": "Exportar",
        "status": "Estado",
        "date": "Fecha",
        "amount": "Monto",
        "notes": "Notas",
        "no_data": "No hay datos disponibles",
        "success": "Éxito",
        "error": "Error",
        "loading": "Cargando...",

        # Login
        "login_title": "Sistema de Facturación Legal",
        "password": "Contraseña",
        "login": "Iniciar Sesión",
        "forgot_password": "¿Olvidó su contraseña?",
        "client_login": "Portal de Clientes",
        "access_code": "Código de Acceso",
        "enter_access_code": "Ingrese su código de acceso",

        # Remaining keys default to English
        "create_invoice": "Crear Factura",
        "select_client": "Seleccionar Cliente",
        "invoice_amount": "Monto",
        "record_payment": "Registrar Pago",
        "add_client": "Agregar Cliente",
        "client_name": "Nombre del Cliente",
        "uscis_title": "Rastreo de Casos USCIS",
        "receipt_number": "Número de Recibo",
        "check_status": "Verificar Estado",
        "court_title": "Casos Judiciales y e-Filing",
        "portal_title": "Gestión del Portal de Clientes",
        "generate_code": "Generar Código de Acceso",
    },

    "zh": {
        # Navigation
        "nav_dashboard": "仪表板",
        "nav_invoice": "发票和邮件",
        "nav_past_due": "逾期和提醒",
        "nav_payment": "付款跟踪",
        "nav_trust": "信托账户 (IOLTA)",
        "nav_expenses": "费用",
        "nav_clients": "客户和案件",
        "nav_reports": "报告和损益",
        "nav_audit": "审计日志",
        "nav_backup": "备份和导出",
        "nav_ai": "AI助手",
        "nav_gmail": "Gmail设置",
        "nav_uscis": "USCIS追踪",
        "nav_court": "法院案件",
        "nav_portal": "客户门户",

        # Dashboard
        "dashboard_title": "仪表板",
        "dashboard_subtitle": "账单概览",
        "active_clients": "活跃客户",
        "total_billed": "总账单",
        "outstanding": "未付款",
        "net_income": "净收入",
        "trust_balance": "信托余额 (IOLTA)",
        "refresh": "刷新",

        # Common
        "save": "保存",
        "cancel": "取消",
        "delete": "删除",
        "edit": "编辑",
        "search": "搜索",
        "no_data": "暂无数据",
        "success": "成功",
        "error": "错误",
        "loading": "加载中...",

        # Login
        "login_title": "法律账单系统",
        "password": "密码",
        "login": "登录",
        "forgot_password": "忘记密码？",
        "client_login": "客户门户登录",
        "access_code": "访问代码",
        "enter_access_code": "请输入您的访问代码",

        # Other
        "create_invoice": "创建发票",
        "select_client": "选择客户",
        "record_payment": "记录付款",
        "add_client": "添加客户",
        "client_name": "客户姓名",
        "uscis_title": "USCIS案件追踪",
        "receipt_number": "收据号码",
        "check_status": "检查状态",
        "court_title": "法院案件和电子提交",
        "portal_title": "客户门户管理",
        "generate_code": "生成访问代码",
    },
}

# Language display names
LANGUAGE_NAMES = {
    "en": "English",
    "ko": "한국어",
    "es": "Español",
    "zh": "中文",
}


def t(key, lang="en"):
    """Translate a key to the specified language. Falls back to English."""
    translations = TRANSLATIONS.get(lang, TRANSLATIONS["en"])
    result = translations.get(key)
    if result is None:
        # Fallback to English
        result = TRANSLATIONS["en"].get(key, key)
    return result


def get_available_languages():
    """Return list of available languages."""
    return LANGUAGE_NAMES
