"""
US Immigration Group - Legal Billing Database
SQLite database with Google Sheets sync capability.
Adapted from Yun & Rose Properties rent management for immigration law practice.
"""
import sqlite3
import os
from datetime import datetime, date
from contextlib import contextmanager

DB_PATH = os.path.join(os.path.dirname(__file__), "uig_billing.db")

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            name_korean TEXT,
            email TEXT,
            phone TEXT,
            address TEXT,
            case_type TEXT,
            case_number TEXT,
            visa_type TEXT,
            retainer_amount REAL DEFAULT 0,
            balance REAL DEFAULT 0,
            retainer_date DATE,
            retainer_end DATE,
            contact_person TEXT,
            is_active INTEGER DEFAULT 1,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            invoice_number TEXT NOT NULL UNIQUE,
            invoice_date DATE NOT NULL,
            due_date DATE NOT NULL,
            description TEXT,
            legal_fees REAL DEFAULT 0,
            filing_fees REAL DEFAULT 0,
            other_expenses REAL DEFAULT 0,
            total_amount REAL NOT NULL,
            retainer_applied REAL DEFAULT 0,
            amount_due REAL NOT NULL,
            status TEXT DEFAULT 'Unpaid',
            sent_at TIMESTAMP,
            paid_at TIMESTAMP,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            invoice_id INTEGER,
            date_received DATE NOT NULL,
            amount REAL NOT NULL,
            check_number TEXT,
            payment_method TEXT DEFAULT 'Check',
            deposit_to TEXT DEFAULT 'Operating',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );

        CREATE TABLE IF NOT EXISTS trust_account (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            date DATE NOT NULL,
            transaction_type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            balance_after REAL,
            reference TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS expenses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            date DATE NOT NULL,
            category TEXT NOT NULL,
            vendor TEXT,
            description TEXT,
            amount REAL NOT NULL,
            is_billable INTEGER DEFAULT 1,
            document_path TEXT,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );

        CREATE TABLE IF NOT EXISTS email_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER,
            invoice_id INTEGER,
            email_type TEXT NOT NULL,
            recipient TEXT,
            subject TEXT,
            sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'Sent',
            FOREIGN KEY (client_id) REFERENCES clients(id),
            FOREIGN KEY (invoice_id) REFERENCES invoices(id)
        );

        CREATE TABLE IF NOT EXISTS case_deadlines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            client_id INTEGER NOT NULL,
            deadline_type TEXT NOT NULL,
            deadline_date DATE NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'Pending',
            reminder_sent INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (client_id) REFERENCES clients(id)
        );
        """)


def migrate_db():
    """Add new columns to existing tables if they don't exist."""
    migrations = [
        ("clients", "name_korean", "TEXT"),
        ("clients", "visa_type", "TEXT"),
        ("clients", "retainer_amount", "REAL DEFAULT 0"),
        ("clients", "retainer_date", "DATE"),
        ("clients", "retainer_end", "DATE"),
        ("invoices", "retainer_applied", "REAL DEFAULT 0"),
        ("invoices", "amount_due", "REAL NOT NULL DEFAULT 0"),
        ("payments", "deposit_to", "TEXT DEFAULT 'Operating'"),
    ]
    with get_db() as conn:
        for table, column, col_type in migrations:
            try:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            except Exception:
                pass


def seed_sample_clients():
    """Seed with sample clients if DB is empty. Only for demo purposes."""
    sample_clients = [
        ("Yun, Soo-Jin", "윤수진", "soojin.yun@email.com", "(847) 555-0101",
         "123 Main St, Des Plaines, IL 60016", "Employment-Based", "UIG-2026-001",
         "H-1B", 1500.00, "2026-01-15", "2027-01-15", "Yun Soo-Jin"),
        ("Kim, Min-Ho", "김민호", "minho.kim@email.com", "(847) 555-0102",
         "456 Oak Ave, Mount Prospect, IL 60056", "Family-Based", "UIG-2026-002",
         "I-130/I-485", 3500.00, "2026-02-01", "2027-02-01", "Kim Min-Ho"),
        ("Park, Ji-Yeon", "박지연", "jiyeon.park@email.com", "(847) 555-0103",
         "789 Elm St, Arlington Heights, IL 60004", "Employment-Based", "UIG-2026-003",
         "EB-2 NIW", 5000.00, "2026-03-10", "2027-03-10", "Park Ji-Yeon"),
        ("Lee, Dong-Hyun", "이동현", "dhlee@email.com", "(312) 555-0104",
         "321 Pine Rd, Chicago, IL 60601", "Humanitarian", "UIG-2026-004",
         "Asylum", 4000.00, "2025-11-01", "2026-11-01", "Lee Dong-Hyun"),
        ("Choi, Hye-Won", "최혜원", "hwchoi@email.com", "(847) 555-0105",
         "654 Maple Dr, Schaumburg, IL 60193", "Naturalization", "UIG-2026-005",
         "N-400", 1200.00, "2026-04-01", "2027-04-01", "Choi Hye-Won"),
    ]
    with get_db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        if count == 0:
            for (name, name_kr, email, phone, addr, case_type, case_num,
                 visa, retainer, ret_date, ret_end, contact) in sample_clients:
                conn.execute(
                    """INSERT INTO clients (name, name_korean, email, phone, address,
                       case_type, case_number, visa_type, retainer_amount,
                       retainer_date, retainer_end, contact_person)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (name, name_kr, email, phone, addr, case_type, case_num,
                     visa, retainer, ret_date, ret_end, contact)
                )


# === Client CRUD ===

def get_all_clients(active_only=True):
    with get_db() as conn:
        if active_only:
            rows = conn.execute("SELECT * FROM clients WHERE is_active = 1 ORDER BY name").fetchall()
        else:
            rows = conn.execute("SELECT * FROM clients ORDER BY name").fetchall()
        return [dict(r) for r in rows]


def get_client(client_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        return dict(row) if row else None


def add_client(name, name_korean="", email="", phone="", address="",
               case_type="", case_number="", visa_type="", retainer_amount=0,
               retainer_date=None, retainer_end=None, contact_person="", notes=""):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO clients (name, name_korean, email, phone, address,
               case_type, case_number, visa_type, retainer_amount,
               retainer_date, retainer_end, contact_person, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (name, name_korean, email, phone, address, case_type, case_number,
             visa_type, retainer_amount, retainer_date, retainer_end, contact_person, notes)
        )


def update_client(client_id, **kwargs):
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs.keys())
    values = list(kwargs.values()) + [client_id]
    with get_db() as conn:
        conn.execute(f"UPDATE clients SET {set_clause} WHERE id = ?", values)


def update_client_balance(client_id):
    """Recalculate client balance from invoices and payments."""
    with get_db() as conn:
        total_billed = conn.execute(
            "SELECT COALESCE(SUM(amount_due), 0) FROM invoices WHERE client_id = ?",
            (client_id,)
        ).fetchone()[0]
        total_paid = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE client_id = ?",
            (client_id,)
        ).fetchone()[0]
        balance = total_billed - total_paid
        conn.execute("UPDATE clients SET balance = ? WHERE id = ?", (balance, client_id))
        return balance


def recalculate_all_balances():
    clients = get_all_clients(active_only=False)
    for c in clients:
        update_client_balance(c["id"])


# === Invoice CRUD ===

def get_next_invoice_number(year):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ?",
            (f"INV-{year}-%",)
        ).fetchall()
        max_num = 0
        for row in rows:
            parts = row["invoice_number"].split("-")
            if len(parts) == 3:
                try:
                    num = int(parts[2])
                    if num > max_num:
                        max_num = num
                except ValueError:
                    continue
        return f"INV-{year}-{max_num + 1:03d}"


def create_invoice(client_id, invoice_date, due_date, description,
                   legal_fees=0, filing_fees=0, other_expenses=0,
                   retainer_applied=0, notes=""):
    total = legal_fees + filing_fees + other_expenses
    amount_due = total - retainer_applied
    year = invoice_date.year if isinstance(invoice_date, date) else int(str(invoice_date)[:4])
    inv_num = get_next_invoice_number(year)
    inv_date_str = invoice_date.isoformat() if isinstance(invoice_date, date) else str(invoice_date)
    due_date_str = due_date.isoformat() if isinstance(due_date, date) else str(due_date)
    with get_db() as conn:
        conn.execute(
            """INSERT INTO invoices (client_id, invoice_number, invoice_date, due_date,
               description, legal_fees, filing_fees, other_expenses,
               total_amount, retainer_applied, amount_due, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, inv_num, inv_date_str, due_date_str, description,
             legal_fees, filing_fees, other_expenses, total, retainer_applied, amount_due, notes)
        )
    return inv_num


def get_invoices(client_id=None, status=None):
    with get_db() as conn:
        query = """SELECT i.*, c.name as client_name, c.email as client_email,
                   c.case_number, c.visa_type
                   FROM invoices i JOIN clients c ON i.client_id = c.id WHERE 1=1"""
        params = []
        if client_id:
            query += " AND i.client_id = ?"
            params.append(client_id)
        if status:
            query += " AND i.status = ?"
            params.append(status)
        query += " ORDER BY i.invoice_date DESC, c.name"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def mark_invoice_sent(invoice_id):
    with get_db() as conn:
        conn.execute("UPDATE invoices SET sent_at = ? WHERE id = ?",
                     (datetime.now().isoformat(), invoice_id))


# === Payment CRUD ===

def record_payment(client_id, invoice_id, date_received, amount,
                   check_number="", payment_method="Check", deposit_to="Operating", notes=""):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO payments (client_id, invoice_id, date_received, amount,
               check_number, payment_method, deposit_to, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, invoice_id, date_received, amount, check_number,
             payment_method, deposit_to, notes)
        )
        if invoice_id:
            inv = conn.execute("SELECT amount_due FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
            paid = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE invoice_id = ?",
                (invoice_id,)
            ).fetchone()["total"]
            if inv and paid >= inv["amount_due"]:
                conn.execute("UPDATE invoices SET status = 'Paid', paid_at = ? WHERE id = ?",
                             (datetime.now().isoformat(), invoice_id))
            else:
                conn.execute("UPDATE invoices SET status = 'Partial' WHERE id = ?", (invoice_id,))


def get_payments(client_id=None):
    with get_db() as conn:
        query = """SELECT p.*, c.name as client_name, i.invoice_number
                   FROM payments p
                   JOIN clients c ON p.client_id = c.id
                   LEFT JOIN invoices i ON p.invoice_id = i.id WHERE 1=1"""
        params = []
        if client_id:
            query += " AND p.client_id = ?"
            params.append(client_id)
        query += " ORDER BY p.date_received DESC"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


# === Trust Account (IOLTA) ===

def trust_deposit(client_id, date_str, amount, description="", reference=""):
    with get_db() as conn:
        last = conn.execute(
            "SELECT balance_after FROM trust_account WHERE client_id = ? ORDER BY id DESC LIMIT 1",
            (client_id,)
        ).fetchone()
        prev_balance = last["balance_after"] if last else 0
        new_balance = prev_balance + amount
        conn.execute(
            """INSERT INTO trust_account (client_id, date, transaction_type, amount,
               description, balance_after, reference) VALUES (?, ?, 'deposit', ?, ?, ?, ?)""",
            (client_id, date_str, amount, description, new_balance, reference)
        )
        return new_balance


def trust_withdrawal(client_id, date_str, amount, description="", reference=""):
    with get_db() as conn:
        last = conn.execute(
            "SELECT balance_after FROM trust_account WHERE client_id = ? ORDER BY id DESC LIMIT 1",
            (client_id,)
        ).fetchone()
        prev_balance = last["balance_after"] if last else 0
        new_balance = prev_balance - amount
        conn.execute(
            """INSERT INTO trust_account (client_id, date, transaction_type, amount,
               description, balance_after, reference) VALUES (?, ?, 'withdrawal', ?, ?, ?, ?)""",
            (client_id, date_str, amount, description, new_balance, reference)
        )
        return new_balance


def get_trust_transactions(client_id=None):
    with get_db() as conn:
        query = """SELECT t.*, c.name as client_name FROM trust_account t
                   JOIN clients c ON t.client_id = c.id WHERE 1=1"""
        params = []
        if client_id:
            query += " AND t.client_id = ?"
            params.append(client_id)
        query += " ORDER BY t.date DESC, t.id DESC"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def get_trust_balance(client_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT balance_after FROM trust_account WHERE client_id = ? ORDER BY id DESC LIMIT 1",
            (client_id,)
        ).fetchone()
        return row["balance_after"] if row else 0


# === Expenses ===

def add_expense(date_str, category, vendor="", description="", amount=0,
                client_id=None, is_billable=1, document_path="", notes=""):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO expenses (client_id, date, category, vendor, description,
               amount, is_billable, document_path, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (client_id, date_str, category, vendor, description, amount,
             is_billable, document_path, notes)
        )


def get_expenses(client_id=None, category=None, start_date=None, end_date=None):
    with get_db() as conn:
        query = """SELECT e.*, c.name as client_name FROM expenses e
                   LEFT JOIN clients c ON e.client_id = c.id WHERE 1=1"""
        params = []
        if client_id:
            query += " AND e.client_id = ?"
            params.append(client_id)
        if category:
            query += " AND e.category = ?"
            params.append(category)
        if start_date:
            query += " AND e.date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND e.date <= ?"
            params.append(end_date)
        query += " ORDER BY e.date DESC"
        return [dict(r) for r in conn.execute(query, params).fetchall()]


# === Dashboard Stats ===

def get_dashboard_stats():
    with get_db() as conn:
        total_clients = conn.execute(
            "SELECT COUNT(*) FROM clients WHERE is_active = 1"
        ).fetchone()[0]
        total_billed = conn.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM invoices"
        ).fetchone()[0]
        outstanding = conn.execute(
            "SELECT COALESCE(SUM(amount_due), 0) FROM invoices WHERE status != 'Paid'"
        ).fetchone()[0]
        total_collected = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments"
        ).fetchone()[0]
        total_trust = conn.execute(
            "SELECT COALESCE(SUM(CASE WHEN transaction_type='deposit' THEN amount ELSE -amount END), 0) FROM trust_account"
        ).fetchone()[0]
        total_expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses"
        ).fetchone()[0]
        unpaid_count = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE status != 'Paid'"
        ).fetchone()[0]
        past_due_count = conn.execute(
            "SELECT COUNT(*) FROM invoices WHERE status != 'Paid' AND due_date < date('now')"
        ).fetchone()[0]
        return {
            "total_clients": total_clients,
            "total_billed": total_billed,
            "outstanding": outstanding,
            "total_collected": total_collected,
            "trust_balance": total_trust,
            "total_expenses": total_expenses,
            "net_income": total_collected - total_expenses,
            "unpaid_count": unpaid_count,
            "past_due_count": past_due_count,
        }


# === Alerts ===

def get_past_due_invoices():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT i.*, c.name as client_name, c.email as client_email,
               c.case_number, c.visa_type, c.phone,
               CAST(julianday('now') - julianday(i.due_date) AS INTEGER) as days_overdue
               FROM invoices i JOIN clients c ON i.client_id = c.id
               WHERE i.status != 'Paid' AND i.due_date < date('now')
               ORDER BY i.due_date ASC"""
        ).fetchall()
        return [dict(r) for r in rows]


def get_upcoming_deadlines(days_ahead=30):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT d.*, c.name as client_name, c.case_number
               FROM case_deadlines d JOIN clients c ON d.client_id = c.id
               WHERE d.status = 'Pending'
                 AND d.deadline_date >= date('now')
                 AND d.deadline_date <= date('now', '+' || ? || ' days')
               ORDER BY d.deadline_date ASC""", (days_ahead,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_retainer_alerts(days_ahead=60):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT *,
               CAST(julianday(retainer_end) - julianday('now') AS INTEGER) as days_remaining
               FROM clients
               WHERE is_active = 1 AND retainer_end IS NOT NULL
                 AND julianday(retainer_end) - julianday('now') <= ?
                 AND julianday(retainer_end) - julianday('now') > 0
               ORDER BY retainer_end ASC""", (days_ahead,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_expired_retainers():
    with get_db() as conn:
        rows = conn.execute(
            """SELECT *,
               CAST(julianday('now') - julianday(retainer_end) AS INTEGER) as days_expired
               FROM clients
               WHERE is_active = 1 AND retainer_end IS NOT NULL AND retainer_end < date('now')
               ORDER BY retainer_end ASC"""
        ).fetchall()
        return [dict(r) for r in rows]


# === Email Log ===

def log_email(client_id, invoice_id, email_type, recipient, subject):
    with get_db() as conn:
        conn.execute(
            "INSERT INTO email_log (client_id, invoice_id, email_type, recipient, subject) VALUES (?, ?, ?, ?, ?)",
            (client_id, invoice_id, email_type, recipient, subject)
        )


def get_email_log(limit=50):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT e.*, c.name as client_name FROM email_log e
               LEFT JOIN clients c ON e.client_id = c.id
               ORDER BY e.sent_at DESC LIMIT ?""", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]


# === P&L / Reports ===

def get_monthly_pnl(year, month):
    start = f"{year}-{month:02d}-01"
    if month == 12:
        end = f"{year + 1}-01-01"
    else:
        end = f"{year}-{month + 1:02d}-01"
    with get_db() as conn:
        income = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE date_received >= ? AND date_received < ?",
            (start, end)
        ).fetchone()[0]
        expenses_total = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE date >= ? AND date < ?",
            (start, end)
        ).fetchone()[0]
        expense_breakdown = [dict(r) for r in conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses WHERE date >= ? AND date < ? GROUP BY category ORDER BY total DESC",
            (start, end)
        ).fetchall()]
        payment_details = [dict(r) for r in conn.execute(
            """SELECT p.date_received, c.name as client_name, p.amount, p.payment_method
               FROM payments p JOIN clients c ON p.client_id = c.id
               WHERE p.date_received >= ? AND p.date_received < ?
               ORDER BY p.date_received""",
            (start, end)
        ).fetchall()]
        invoiced = conn.execute(
            "SELECT COALESCE(SUM(total_amount), 0) FROM invoices WHERE invoice_date >= ? AND invoice_date < ?",
            (start, end)
        ).fetchone()[0]
    return {
        "income": income,
        "expenses": expenses_total,
        "net": income - expenses_total,
        "invoiced": invoiced,
        "expense_breakdown": expense_breakdown,
        "payment_details": payment_details,
    }


# === Case Deadlines ===

def add_deadline(client_id, deadline_type, deadline_date, description=""):
    with get_db() as conn:
        conn.execute(
            """INSERT INTO case_deadlines (client_id, deadline_type, deadline_date, description)
               VALUES (?, ?, ?, ?)""",
            (client_id, deadline_type, deadline_date, description)
        )


def complete_deadline(deadline_id):
    with get_db() as conn:
        conn.execute("UPDATE case_deadlines SET status = 'Completed' WHERE id = ?", (deadline_id,))


if __name__ == "__main__":
    init_db()
    migrate_db()
    seed_sample_clients()
    print("UIG Billing database initialized and seeded.")
