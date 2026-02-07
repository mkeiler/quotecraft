"""Database schema and initialization functions for QuoteCraft."""

import sqlite3
from pathlib import Path
from typing import Optional, Tuple

from utils.debug import log_debug, log_info

DB_PATH = Path(__file__).parent.parent / "quotecraft.db"


def _get_bootstrap_credentials() -> Tuple[str, str]:
    """Get bootstrap admin credentials from secrets.toml or environment."""
    import os
    try:
        import streamlit as st
        username = st.secrets["auth"]["username"]
        password_hash = st.secrets["auth"]["password_hash"]
    except (KeyError, FileNotFoundError, Exception):
        username = os.getenv("ADMIN_USERNAME", "admin")
        password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    return username, password_hash


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
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                display_name TEXT,
                role TEXT CHECK(role IN ('admin', 'user')) DEFAULT 'user',
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by_user_id INTEGER REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS clients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                phone TEXT,
                company TEXT,
                address TEXT,
                created_by_user_id INTEGER REFERENCES users(id),
                is_public BOOLEAN DEFAULT 0,
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
                created_by_user_id INTEGER REFERENCES users(id),
                is_public BOOLEAN DEFAULT 0,
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
                created_by_user_id INTEGER REFERENCES users(id),
                is_public BOOLEAN DEFAULT 0,
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
    _migrate_to_multiuser()


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


def _migrate_to_multiuser() -> None:
    """Migrate existing data to multi-user schema with ownership columns."""
    conn = get_connection()
    try:
        # Check if users table has any data - if so, migration already done
        cursor = conn.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]

        if user_count > 0:
            return  # Already migrated

        # Get bootstrap admin credentials from secrets
        username, password_hash = _get_bootstrap_credentials()

        if not password_hash:
            log_info("Migration: No bootstrap credentials found, skipping user creation")
            return

        # Create bootstrap admin user
        conn.execute(
            """INSERT INTO users (username, email, password_hash, display_name, role)
               VALUES (?, ?, ?, ?, 'admin')""",
            (username, f"{username}@system.local", password_hash, "Administrador")
        )
        conn.commit()

        admin_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]
        log_info("Migration: Created bootstrap admin user", user_id=admin_id, username=username)

        # Add ownership columns to existing tables if missing
        for table in ['clients', 'services', 'quotes']:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            columns = [row[1] for row in cursor.fetchall()]

            if 'created_by_user_id' not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN created_by_user_id INTEGER REFERENCES users(id)")
                conn.commit()
                log_info(f"Migration: added created_by_user_id to {table}")

            if 'is_public' not in columns:
                conn.execute(f"ALTER TABLE {table} ADD COLUMN is_public BOOLEAN DEFAULT 0")
                conn.commit()
                log_info(f"Migration: added is_public to {table}")

        # Assign existing data to bootstrap admin and mark as public
        for table in ['clients', 'services', 'quotes']:
            cursor = conn.execute(
                f"UPDATE {table} SET created_by_user_id = ?, is_public = 1 WHERE created_by_user_id IS NULL",
                (admin_id,)
            )
            conn.commit()
            if cursor.rowcount > 0:
                log_info(f"Migration: assigned {cursor.rowcount} {table} to admin", admin_id=admin_id)

        log_info("Migration to multi-user completed successfully")
    except Exception as e:
        log_info(f"Migration error: {e}")
    finally:
        conn.close()
