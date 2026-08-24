"""Multi-tenant SIWES platform database. SQLite with WAL mode."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "platform.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS schools (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    full_name TEXT NOT NULL,
    logo_path TEXT,
    referral_prefix TEXT NOT NULL,
    paystack_secret_key TEXT,
    paystack_public_key TEXT,
    platform_cut_pct INTEGER NOT NULL DEFAULT 20,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS school_config (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL REFERENCES schools(id),
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    UNIQUE(school_id, key)
);

CREATE TABLE IF NOT EXISTS school_admins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    school_id INTEGER NOT NULL REFERENCES schools(id),
    username TEXT UNIQUE NOT NULL,
    pin_hash TEXT NOT NULL,
    display_name TEXT,
    active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS super_admin (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pin_hash TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    ip_address TEXT,
    role TEXT NOT NULL,
    school_admin_id INTEGER,
    school_id INTEGER
);
CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions(expires_at);

CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    school_id INTEGER NOT NULL REFERENCES schools(id),
    created_at TEXT NOT NULL,
    matric_no TEXT NOT NULL,
    student_name TEXT NOT NULL,
    student_email TEXT,
    package TEXT,
    amount INTEGER,
    platform_amount INTEGER NOT NULL DEFAULT 0,
    admin_amount INTEGER NOT NULL DEFAULT 0,
    express INTEGER NOT NULL DEFAULT 0,
    priority INTEGER NOT NULL DEFAULT 0,
    payload_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending_payment',
    reference TEXT,
    form_token TEXT,
    docx_path TEXT,
    pptx_path TEXT,
    error_message TEXT,
    delivered_at TEXT,
    printed_at TEXT,
    notes TEXT,
    test_mode INTEGER NOT NULL DEFAULT 0,
    referral_code TEXT,
    referral_code_used TEXT,
    referral_discount INTEGER NOT NULL DEFAULT 0,
    referral_credit_applied INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_orders_school ON orders(school_id);
CREATE INDEX IF NOT EXISTS idx_orders_matric ON orders(matric_no);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE UNIQUE INDEX IF NOT EXISTS idx_orders_referral_code ON orders(referral_code) WHERE referral_code IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_orders_reference ON orders(reference);
CREATE INDEX IF NOT EXISTS idx_orders_form_token ON orders(form_token);

CREATE TABLE IF NOT EXISTS school_prices (
    school_id INTEGER NOT NULL REFERENCES schools(id),
    package TEXT NOT NULL,
    amount INTEGER NOT NULL,
    express_addon INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (school_id, package)
);

CREATE TABLE IF NOT EXISTS platform_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS generation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER NOT NULL REFERENCES orders(id),
    timestamp TEXT NOT NULL,
    level TEXT NOT NULL,
    message TEXT NOT NULL,
    duration_ms INTEGER
);
CREATE INDEX IF NOT EXISTS idx_logs_order ON generation_logs(order_id);

CREATE TABLE IF NOT EXISTS referral_credits (
    school_id INTEGER NOT NULL REFERENCES schools(id),
    matric_no TEXT NOT NULL,
    balance INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (school_id, matric_no)
);
"""


@contextmanager
def get_conn():
    conn = sqlite3.connect(str(DB_PATH), timeout=15.0, isolation_level=None)
    try:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA foreign_keys=ON")
        yield conn
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.executescript(SCHEMA_SQL)
        # Normalise matric_no uppercase trim
        conn.execute("UPDATE orders SET matric_no = UPPER(TRIM(matric_no)) WHERE matric_no != UPPER(TRIM(matric_no))")
