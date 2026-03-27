"""
core/database.py
SQLite persistence layer for the Instagram Graph API CRM.

Tables
------
  Contacts  — one row per Instagram user (keyed on IGSID)
  Messages  — individual messages in each thread
  Snippets  — saved reply text snippets for the Inbox UI

WAL mode is enabled on every connection so that the FastAPI webhook process and
the Streamlit UI process can both write/read concurrently without locking errors.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Optional
from config.settings import DB_PATH


# ─────────────────────────────────────────────────────────────────────────────
# Connection helper
# ─────────────────────────────────────────────────────────────────────────────

def _get_conn() -> sqlite3.Connection:
    """Open a connection with WAL journal mode and row_factory set."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn


# ─────────────────────────────────────────────────────────────────────────────
# Schema initialisation
# ─────────────────────────────────────────────────────────────────────────────

def init_db() -> None:
    """Create all tables if they don't already exist."""
    conn = _get_conn()
    with conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS Contacts (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                igsid            TEXT    UNIQUE NOT NULL,
                ig_username      TEXT,
                last_inbound_at  DATETIME,
                pipeline_stage   TEXT    NOT NULL DEFAULT 'New Lead',
                created_at       DATETIME NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS Messages (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                contact_id       INTEGER NOT NULL REFERENCES Contacts(id) ON DELETE CASCADE,
                meta_message_id  TEXT    UNIQUE,
                direction        TEXT    NOT NULL CHECK(direction IN ('inbound', 'outbound')),
                body             TEXT    NOT NULL,
                timestamp        DATETIME NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_messages_contact
                ON Messages(contact_id, timestamp);

            CREATE TABLE IF NOT EXISTS Snippets (
                id   INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                body TEXT NOT NULL
            );
        """)
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Contact helpers
# ─────────────────────────────────────────────────────────────────────────────

def upsert_contact(igsid: str, ig_username: Optional[str] = None) -> int:
    """
    Insert a new contact or update ig_username if already exists.
    Returns the contact's integer id.
    """
    conn = _get_conn()
    with conn:
        conn.execute(
            """
            INSERT INTO Contacts (igsid, ig_username)
            VALUES (?, ?)
            ON CONFLICT(igsid) DO UPDATE SET
                ig_username = COALESCE(EXCLUDED.ig_username, Contacts.ig_username)
            """,
            (igsid, ig_username),
        )
        row = conn.execute(
            "SELECT id FROM Contacts WHERE igsid = ?", (igsid,)
        ).fetchone()
    conn.close()
    return row["id"]


def get_contacts() -> list[dict]:
    """Return all contacts ordered by most recent inbound message."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT id, igsid, ig_username, last_inbound_at, pipeline_stage, created_at
        FROM Contacts
        ORDER BY COALESCE(last_inbound_at, created_at) DESC
        """
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_contact_by_igsid(igsid: str) -> Optional[dict]:
    """Return a single contact dict or None."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM Contacts WHERE igsid = ?", (igsid,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def update_pipeline_stage(contact_id: int, stage: str) -> None:
    """Change the pipeline_stage for a contact."""
    conn = _get_conn()
    with conn:
        conn.execute(
            "UPDATE Contacts SET pipeline_stage = ? WHERE id = ?",
            (stage, contact_id),
        )
    conn.close()


def _touch_last_inbound(contact_id: int, ts: datetime) -> None:
    """Update last_inbound_at — called only on inbound messages."""
    conn = _get_conn()
    with conn:
        conn.execute(
            "UPDATE Contacts SET last_inbound_at = ? WHERE id = ?",
            (ts.strftime("%Y-%m-%d %H:%M:%S"), contact_id),
        )
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Message helpers
# ─────────────────────────────────────────────────────────────────────────────

def save_message(
    contact_id: int,
    meta_message_id: Optional[str],
    direction: str,
    body: str,
    timestamp: datetime,
) -> bool:
    """
    Persist a message.  Uses INSERT OR IGNORE so duplicate mid's are silently
    dropped (handles webhook retries).

    Returns True if the row was inserted, False if it was a duplicate.
    """
    conn = _get_conn()
    with conn:
        cur = conn.execute(
            """
            INSERT OR IGNORE INTO Messages
                (contact_id, meta_message_id, direction, body, timestamp)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                contact_id,
                meta_message_id,
                direction,
                body,
                timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            ),
        )
        inserted = cur.rowcount > 0
    conn.close()

    # Only update the 24-hour window clock for real inbound messages
    if inserted and direction == "inbound":
        _touch_last_inbound(contact_id, timestamp)

    return inserted


def get_thread(contact_id: int) -> list[dict]:
    """Return all messages for a contact in chronological order."""
    conn = _get_conn()
    rows = conn.execute(
        """
        SELECT id, meta_message_id, direction, body, timestamp
        FROM Messages
        WHERE contact_id = ?
        ORDER BY timestamp ASC
        """,
        (contact_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Snippets helpers
# ─────────────────────────────────────────────────────────────────────────────

def get_snippets() -> list[dict]:
    """Return all snippets ordered by name."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM Snippets ORDER BY name ASC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_snippet(name: str, body: str) -> None:
    """Insert or replace a snippet by name."""
    conn = _get_conn()
    with conn:
        conn.execute(
            "INSERT OR REPLACE INTO Snippets (name, body) VALUES (?, ?)",
            (name, body),
        )
    conn.close()


def delete_snippet(snippet_id: int) -> None:
    """Delete a snippet by primary key."""
    conn = _get_conn()
    with conn:
        conn.execute("DELETE FROM Snippets WHERE id = ?", (snippet_id,))
    conn.close()


# ─────────────────────────────────────────────────────────────────────────────
# Scraper interop
# ─────────────────────────────────────────────────────────────────────────────

def import_scraped_leads(scraper_db_path: str = "C:/IG_scraper/scraped_leads.db") -> int:
    """
    Connects to the Scraper DB, dynamically finds the table with a 'username' column,
    extracts all usernames, and inserts them safely into the CRM's Contacts table
    with a placeholder IGSID and 'New Lead' status.

    Returns the integer count of *newly* imported leads.
    """
    import os
    if not os.path.exists(scraper_db_path):
        return 0

    # 1. Connect to the scraper DB
    try:
        scraper_conn = sqlite3.connect(scraper_db_path)
        cursor = scraper_conn.cursor()

        # Find all table names
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [row[0] for row in cursor.fetchall()]

        target_table = None
        for tbl in tables:
            cursor.execute(f"PRAGMA table_info({tbl})")
            columns = [col[1] for col in cursor.fetchall()]
            if 'username' in columns:
                target_table = tbl
                break

        if not target_table:
            scraper_conn.close()
            return 0

        # Fetch all usernames (filter out nulls or empty strings)
        cursor.execute(f"SELECT username FROM {target_table} WHERE username IS NOT NULL AND username != ''")
        usernames = [row[0] for row in cursor.fetchall()]
        scraper_conn.close()

    except Exception:
        return 0

    if not usernames:
        return 0

    # 2. Insert into the CRM DB 
    conn = _get_conn()
    new_inserts_count = 0
    with conn:
        for uname in usernames:
            igsid = f"PENDING_{uname}"
            # INSERT OR IGNORE safely skips them if the igsid is already present
            cur = conn.execute(
                """
                INSERT OR IGNORE INTO Contacts (igsid, ig_username, pipeline_stage)
                VALUES (?, ?, 'New Lead')
                """,
                (igsid, uname),
            )
            if cur.rowcount > 0:
                new_inserts_count += 1

    conn.close()
    return new_inserts_count
