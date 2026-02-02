"""CRUD operations for clients and services."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from database.models import get_connection


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

def create_client(
    name: str,
    email: str,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    address: Optional[str] = None,
) -> int:
    """Insert a new client and return its id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO clients (name, email, phone, company, address)
               VALUES (?, ?, ?, ?, ?)""",
            (name, email, phone, company, address),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_clients() -> pd.DataFrame:
    """Return all clients as a DataFrame."""
    conn = get_connection()
    try:
        df = pd.read_sql_query("SELECT * FROM clients ORDER BY name", conn)
        return df
    finally:
        conn.close()


def get_client_by_id(client_id: int) -> Optional[dict[str, Any]]:
    """Return a single client as a dict, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM clients WHERE id = ?", (client_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_client(client_id: int, **kwargs: Any) -> bool:
    """Update client fields. Returns True if a row was affected."""
    if not kwargs:
        return False
    kwargs["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [client_id]
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"UPDATE clients SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_client(client_id: int) -> bool:
    """Delete a client permanently. Returns True if a row was removed."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM clients WHERE id = ?", (client_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def search_clients(query: str) -> pd.DataFrame:
    """Search clients by name or email (case-insensitive)."""
    conn = get_connection()
    try:
        df = pd.read_sql_query(
            """SELECT * FROM clients
               WHERE name LIKE ? OR email LIKE ?
               ORDER BY name""",
            conn,
            params=(f"%{query}%", f"%{query}%"),
        )
        return df
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Services
# ---------------------------------------------------------------------------

def create_service(
    name: str,
    description: Optional[str],
    base_price: float,
    category: Optional[str] = None,
) -> int:
    """Insert a new service and return its id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO services (name, description, base_price, category)
               VALUES (?, ?, ?, ?)""",
            (name, description, base_price, category),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_services(active_only: bool = True) -> pd.DataFrame:
    """Return services as a DataFrame, optionally filtering active only."""
    conn = get_connection()
    try:
        query = "SELECT * FROM services"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY name"
        df = pd.read_sql_query(query, conn)
        return df
    finally:
        conn.close()


def get_service_by_id(service_id: int) -> Optional[dict[str, Any]]:
    """Return a single service as a dict, or None."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT * FROM services WHERE id = ?", (service_id,)
        ).fetchone()
        return dict(row) if row else None
    finally:
        conn.close()


def update_service(service_id: int, **kwargs: Any) -> bool:
    """Update service fields. Returns True if a row was affected."""
    if not kwargs:
        return False
    kwargs["updated_at"] = datetime.now().isoformat()
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [service_id]
    conn = get_connection()
    try:
        cursor = conn.execute(
            f"UPDATE services SET {set_clause} WHERE id = ?", values
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def delete_service(service_id: int) -> bool:
    """Permanently delete a service. Returns True if a row was removed."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM services WHERE id = ?", (service_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def toggle_service_status(service_id: int, active: Optional[bool] = None) -> bool:
    """Toggle or explicitly set the active status of a service.

    If *active* is None the current value is flipped.
    Returns True if a row was affected.
    """
    conn = get_connection()
    try:
        if active is None:
            row = conn.execute(
                "SELECT is_active FROM services WHERE id = ?", (service_id,)
            ).fetchone()
            if not row:
                return False
            active = not bool(row["is_active"])
        cursor = conn.execute(
            "UPDATE services SET is_active = ?, updated_at = ? WHERE id = ?",
            (int(active), datetime.now().isoformat(), service_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()
