"""CRUD operations for users."""

from __future__ import annotations

import hashlib
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from database.models import get_connection
from utils.debug import log_info, log_debug, log_warning


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def create_user(
    username: str,
    email: str,
    password: str,
    display_name: Optional[str] = None,
    role: str = "user",
    created_by_user_id: Optional[int] = None,
) -> int:
    """Create a new user. Returns user ID."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO users
               (username, email, password_hash, display_name, role, created_by_user_id)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (username, email.lower(), hash_password(password), display_name or username, role, created_by_user_id)
        )
        conn.commit()
        user_id = cursor.lastrowid
        log_info("User created", user_id=user_id, username=username, role=role)
        return user_id
    finally:
        conn.close()


def get_all_users() -> pd.DataFrame:
    """Return all users (excluding password hash)."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """SELECT id, username, email, display_name, role, is_active, created_at
               FROM users ORDER BY username""",
            conn
        )
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[dict[str, Any]]:
    """Get a single user by ID (excluding password hash)."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT id, username, email, display_name, role, is_active, created_at
               FROM users WHERE id = ?""",
            (user_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_username(username: str) -> Optional[dict[str, Any]]:
    """Get a single user by username (excluding password hash)."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT id, username, email, display_name, role, is_active, created_at
               FROM users WHERE username = ?""",
            (username,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def get_user_by_credentials(username: str, password: str) -> Optional[dict[str, Any]]:
    """Authenticate user and return user data if valid."""
    password_hash = hash_password(password)
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT id, username, email, display_name, role, is_active
               FROM users
               WHERE username = ? AND password_hash = ? AND is_active = 1""",
            (username, password_hash)
        ).fetchone()
        if row:
            log_debug("User authenticated via database", username=username)
            return dict(row)
        return None
    finally:
        conn.close()


def update_user(user_id: int, **kwargs: Any) -> bool:
    """Update user fields. Use 'password' key to update password."""
    if not kwargs:
        return False

    # Handle password separately
    if "password" in kwargs:
        kwargs["password_hash"] = hash_password(kwargs.pop("password"))

    kwargs["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [user_id]

    conn = get_connection()
    try:
        cursor = conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
        conn.commit()
        if cursor.rowcount > 0:
            log_info("User updated", user_id=user_id, fields=list(kwargs.keys()))
        return cursor.rowcount > 0
    finally:
        conn.close()


def toggle_user_status(user_id: int) -> bool:
    """Toggle user active status."""
    conn = get_connection()
    try:
        conn.execute(
            """UPDATE users SET is_active = NOT is_active, updated_at = ? WHERE id = ?""",
            (datetime.now().isoformat(), user_id)
        )
        conn.commit()
        log_info("User status toggled", user_id=user_id)
        return True
    finally:
        conn.close()


def delete_user(user_id: int) -> bool:
    """Delete a user permanently."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        if cursor.rowcount > 0:
            log_info("User deleted", user_id=user_id)
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_user_display_name(user_id: Optional[int]) -> str:
    """Get display name for a user ID. Returns 'Sistema' if None."""
    if user_id is None:
        return "Sistema"
    user = get_user_by_id(user_id)
    return user["display_name"] if user else "Desconhecido"


def count_users_by_role(role: str) -> int:
    """Count users by role."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role = ?",
            (role,)
        ).fetchone()
        return row[0] if row else 0
    finally:
        conn.close()


def is_last_admin(user_id: int) -> bool:
    """Check if user is the last active admin."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT COUNT(*) FROM users
               WHERE role = 'admin' AND is_active = 1 AND id != ?""",
            (user_id,)
        ).fetchone()
        return row[0] == 0
    finally:
        conn.close()
