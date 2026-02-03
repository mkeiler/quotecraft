"""Database schema and initialization functions for QuoteCraft."""

import sqlite3
from pathlib import Path

from utils.debug import log_debug, log_info

DB_PATH = Path(__file__).parent.parent / "quotecraft.db"


def get_connection() -> sqlite3.Connection:
    """Return a SQLite connection with row_factory set to sqlite3.Row."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_database() -> None:
    """Create all tables if they don't exist."""
    log_debug("Initializing database", path=str(DB_PATH))
    conn = get_connection()
    try:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                company TEXT,
                address TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                base_price REAL NOT NULL,
                category TEXT,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS quotes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_number TEXT UNIQUE NOT NULL,
                client_id INTEGER NOT NULL,
                issue_date DATE NOT NULL,
                valid_until DATE,
                discount_type TEXT CHECK(discount_type IN ('percentage', 'fixed', 'none')) DEFAULT 'none',
                discount_value REAL DEFAULT 0,
                notes TEXT,
                status TEXT CHECK(status IN ('draft', 'sent', 'approved', 'rejected')) DEFAULT 'draft',
                view_token TEXT UNIQUE,
                token_expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (client_id) REFERENCES clients (id)
            );

            CREATE TABLE IF NOT EXISTS quote_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                quote_id INTEGER NOT NULL,
                service_id INTEGER NOT NULL,
                quantity INTEGER DEFAULT 1,
                unit_price REAL NOT NULL,
                FOREIGN KEY (quote_id) REFERENCES quotes (id) ON DELETE CASCADE,
                FOREIGN KEY (service_id) REFERENCES services (id)
            );
        """)
        conn.commit()
    finally:
        conn.close()

    # Run migrations for existing databases
    _migrate_database()


def _migrate_database() -> None:
    """Apply database migrations for new columns on existing databases."""
    conn = get_connection()
    try:
        cursor = conn.execute("PRAGMA table_info(quotes)")
        columns = [row[1] for row in cursor.fetchall()]

        if "view_token" not in columns:
            conn.execute("ALTER TABLE quotes ADD COLUMN view_token TEXT")
            conn.commit()
            log_info("Migration: added view_token column")

        if "token_expires_at" not in columns:
            conn.execute("ALTER TABLE quotes ADD COLUMN token_expires_at TIMESTAMP")
            conn.commit()
            log_info("Migration: added token_expires_at column")

        # Create unique index for view_token (works even if column already exists)
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_quotes_view_token ON quotes(view_token)")
        conn.commit()
    finally:
        conn.close()
