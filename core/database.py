import sqlite3
from datetime import datetime
import os

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "leads.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_db():
    """Run ALL migrations — safe to call repeatedly."""
    conn = get_connection()
    c = conn.cursor()

    # ── Leads (original) ─────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS Leads (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            name             TEXT    NOT NULL,
            phone_number     TEXT    NOT NULL UNIQUE,
            city             TEXT,
            sim_assignment   TEXT    DEFAULT 'Unassigned',
            is_contacted     BOOLEAN DEFAULT 0,
            contact_timestamp DATETIME,
            template_used    INTEGER,
            lead_status      TEXT    DEFAULT 'Uncontacted',
            reply_notes      TEXT
        )
    ''')

    # Safe column additions for existing databases
    _add_column(c, "Leads", "lead_status",    "TEXT DEFAULT 'Uncontacted'")
    _add_column(c, "Leads", "reply_notes",    "TEXT")
    _add_column(c, "Leads", "follow_up_date", "DATE")
    _add_column(c, "Leads", "priority",       "TEXT DEFAULT 'Medium'")

    # ── Templates ────────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS Templates (
            id          INTEGER  PRIMARY KEY AUTOINCREMENT,
            name        TEXT     NOT NULL,
            body        TEXT     NOT NULL,
            category    TEXT     DEFAULT 'General',
            usage_count INTEGER  DEFAULT 0,
            created_at  DATETIME DEFAULT (datetime('now')),
            updated_at  DATETIME DEFAULT (datetime('now'))
        )
    ''')

    # ── DailyStats ───────────────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS DailyStats (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            date             DATE    NOT NULL UNIQUE,
            leads_imported   INTEGER DEFAULT 0,
            messages_sent    INTEGER DEFAULT 0,
            replies_received INTEGER DEFAULT 0,
            calls_booked     INTEGER DEFAULT 0
        )
    ''')

    # ── Settings (key-value) ─────────────────────────────────────────────
    c.execute('''
        CREATE TABLE IF NOT EXISTS Settings (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    # Seed defaults
    for k, v in [
        ('google_sheet_name', 'Viber Outreach Sync'),
        ('sim1_daily_limit',  '40'),
        ('sim2_daily_limit',  '40'),
        ('credentials_path',  'credentials.json'),
    ]:
        c.execute("INSERT OR IGNORE INTO Settings (key, value) VALUES (?, ?)", (k, v))

    conn.commit()
    conn.close()


# ── helper ───────────────────────────────────────────────────────────────
def _add_column(cursor, table, column, definition):
    try:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
    except sqlite3.OperationalError:
        pass  # already exists


# ── Leads CRUD ───────────────────────────────────────────────────────────

def add_lead(name, phone_number, city):
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO Leads (name, phone_number, city) VALUES (?, ?, ?)",
            (name, phone_number, city),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()


def get_all_leads(filter_query=None, filter_params=()):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    q = "SELECT * FROM Leads"
    if filter_query:
        q += f" WHERE {filter_query}"
    rows = conn.execute(q, filter_params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def update_sim_assignment(lead_id, sim_assignment):
    conn = get_connection()
    conn.execute("UPDATE Leads SET sim_assignment = ? WHERE id = ?", (sim_assignment, lead_id))
    conn.commit()
    conn.close()


def update_contact_status(lead_id, is_contacted, template_used=None):
    conn = get_connection()
    ts = datetime.now().isoformat() if is_contacted else None
    status = 'Contacted' if is_contacted else 'Uncontacted'
    conn.execute(
        "UPDATE Leads SET is_contacted=?, contact_timestamp=?, template_used=?, lead_status=? WHERE id=?",
        (is_contacted, ts, template_used, status, lead_id),
    )
    conn.commit()
    conn.close()


def update_lead_reply(lead_id, lead_status, reply_notes):
    conn = get_connection()
    ts = datetime.now().isoformat()
    conn.execute(
        "UPDATE Leads SET lead_status=?, reply_notes=?, contact_timestamp=? WHERE id=?",
        (lead_status, reply_notes, ts, lead_id),
    )
    conn.commit()
    conn.close()


def update_follow_up(lead_id, follow_up_date, priority="Medium"):
    conn = get_connection()
    conn.execute(
        "UPDATE Leads SET follow_up_date=?, priority=? WHERE id=?",
        (follow_up_date, priority, lead_id),
    )
    conn.commit()
    conn.close()


# ── Templates CRUD ───────────────────────────────────────────────────────

def get_all_templates():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM Templates ORDER BY updated_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_template(name, body, category="General"):
    conn = get_connection()
    conn.execute(
        "INSERT INTO Templates (name, body, category) VALUES (?, ?, ?)",
        (name, body, category),
    )
    conn.commit()
    conn.close()


def update_template(template_id, name, body, category):
    conn = get_connection()
    conn.execute(
        "UPDATE Templates SET name=?, body=?, category=?, updated_at=datetime('now') WHERE id=?",
        (name, body, category, template_id),
    )
    conn.commit()
    conn.close()


def delete_template(template_id):
    conn = get_connection()
    conn.execute("DELETE FROM Templates WHERE id=?", (template_id,))
    conn.commit()
    conn.close()


def increment_template_usage(template_id):
    conn = get_connection()
    conn.execute("UPDATE Templates SET usage_count = usage_count + 1 WHERE id=?", (template_id,))
    conn.commit()
    conn.close()


# ── DailyStats CRUD ─────────────────────────────────────────────────────

def get_daily_stats(limit=30):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM DailyStats ORDER BY date DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def increment_daily_stat(column):
    """Increment a counter for today. Column must be one of the stat columns."""
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_connection()
    conn.execute(
        "INSERT INTO DailyStats (date) VALUES (?) ON CONFLICT(date) DO NOTHING", (today,)
    )
    conn.execute(
        f"UPDATE DailyStats SET {column} = {column} + 1 WHERE date = ?", (today,)
    )
    conn.commit()
    conn.close()


# ── Settings CRUD ────────────────────────────────────────────────────────

def get_setting(key, default=None):
    conn = get_connection()
    row = conn.execute("SELECT value FROM Settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row[0] if row else default


def set_setting(key, value):
    conn = get_connection()
    conn.execute(
        "INSERT INTO Settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=?",
        (key, value, value),
    )
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_db()
    print("Database initialized with all Phase 7 migrations.")
