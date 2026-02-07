"""CRUD operations for clients, services, and quotes with ownership support."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Optional

import pandas as pd

from database.models import get_connection


# ---------------------------------------------------------------------------
# Permission Helpers
# ---------------------------------------------------------------------------

def can_modify_item(table: str, item_id: int, user_id: Optional[int], user_is_admin: bool) -> bool:
    """Check if user can modify (edit/delete) an item.

    Admin can modify anything. Regular users can only modify items they own.
    """
    if user_is_admin:
        return True

    if user_id is None:
        return False

    conn = get_connection()
    try:
        row = conn.execute(
            f"SELECT created_by_user_id FROM {table} WHERE id = ?",
            (item_id,)
        ).fetchone()
        return row is not None and row["created_by_user_id"] == user_id
    finally:
        conn.close()


def toggle_item_visibility(table: str, item_id: int) -> bool:
    """Toggle the is_public flag of an item."""
    conn = get_connection()
    try:
        conn.execute(
            f"UPDATE {table} SET is_public = NOT is_public, updated_at = ? WHERE id = ?",
            (datetime.now().isoformat(), item_id)
        )
        conn.commit()
        return True
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Clients
# ---------------------------------------------------------------------------

def create_client(
    name: str,
    email: str,
    phone: Optional[str] = None,
    company: Optional[str] = None,
    address: Optional[str] = None,
    created_by_user_id: Optional[int] = None,
    is_public: bool = False,
) -> int:
    """Insert a new client and return its id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO clients (name, email, phone, company, address, created_by_user_id, is_public)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (name, email, phone, company, address, created_by_user_id, int(is_public)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_clients(
    user_id: Optional[int] = None,
    include_public: bool = True,
) -> pd.DataFrame:
    """Return clients visible to the user.

    If user_id is None, returns all clients (admin view).
    Otherwise, returns user's own clients + public clients (if include_public).
    """
    conn = get_connection()
    try:
        if user_id is None:
            # Admin view - return all
            query = "SELECT * FROM clients ORDER BY name"
            df = pd.read_sql_query(query, conn)
        else:
            # User view - own + public
            if include_public:
                query = """SELECT * FROM clients
                           WHERE created_by_user_id = ? OR is_public = 1
                           ORDER BY name"""
            else:
                query = """SELECT * FROM clients
                           WHERE created_by_user_id = ?
                           ORDER BY name"""
            df = pd.read_sql_query(query, conn, params=(user_id,))
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


def search_clients(
    query: str,
    user_id: Optional[int] = None,
    include_public: bool = True,
) -> pd.DataFrame:
    """Search clients by name or email (case-insensitive), with ownership filter."""
    conn = get_connection()
    try:
        if user_id is None:
            # Admin view
            sql = """SELECT * FROM clients
                     WHERE name LIKE ? OR email LIKE ?
                     ORDER BY name"""
            df = pd.read_sql_query(sql, conn, params=(f"%{query}%", f"%{query}%"))
        else:
            # User view
            if include_public:
                sql = """SELECT * FROM clients
                         WHERE (name LIKE ? OR email LIKE ?)
                         AND (created_by_user_id = ? OR is_public = 1)
                         ORDER BY name"""
                df = pd.read_sql_query(sql, conn, params=(f"%{query}%", f"%{query}%", user_id))
            else:
                sql = """SELECT * FROM clients
                         WHERE (name LIKE ? OR email LIKE ?)
                         AND created_by_user_id = ?
                         ORDER BY name"""
                df = pd.read_sql_query(sql, conn, params=(f"%{query}%", f"%{query}%", user_id))
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
    created_by_user_id: Optional[int] = None,
    is_public: bool = False,
) -> int:
    """Insert a new service and return its id."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO services (name, description, base_price, category, created_by_user_id, is_public)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (name, description, base_price, category, created_by_user_id, int(is_public)),
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_all_services(
    active_only: bool = True,
    user_id: Optional[int] = None,
    include_public: bool = True,
) -> pd.DataFrame:
    """Return services visible to the user, optionally filtering active only."""
    conn = get_connection()
    try:
        conditions = []
        params = []

        if active_only:
            conditions.append("is_active = 1")

        if user_id is not None:
            if include_public:
                conditions.append("(created_by_user_id = ? OR is_public = 1)")
            else:
                conditions.append("created_by_user_id = ?")
            params.append(user_id)

        query = "SELECT * FROM services"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY name"

        df = pd.read_sql_query(query, conn, params=params if params else None)
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


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------

def generate_quote_number() -> str:
    """Generate the next quote number in the format QT-YYYY-NNNN."""
    year = date.today().year
    prefix = f"QT-{year}-"
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT quote_number FROM quotes WHERE quote_number LIKE ? ORDER BY id DESC LIMIT 1",
            (f"{prefix}%",),
        ).fetchone()
        if row:
            last_seq = int(row["quote_number"].split("-")[-1])
            next_seq = last_seq + 1
        else:
            next_seq = 1
        return f"{prefix}{next_seq:04d}"
    finally:
        conn.close()


def create_quote(
    client_id: int,
    items_list: list[dict[str, Any]],
    valid_days: int = 30,
    discount_type: str = "none",
    discount_value: float = 0,
    notes: str = "",
    status: str = "draft",
    created_by_user_id: Optional[int] = None,
    is_public: bool = False,
) -> int:
    """Create a quote with its items in a single transaction.

    *items_list* example: [{'service_id': 1, 'quantity': 2, 'unit_price': 100.0}, ...]
    Returns the new quote id.
    """
    quote_number = generate_quote_number()
    issue = date.today()
    valid_until = issue + timedelta(days=valid_days)

    conn = get_connection()
    try:
        cursor = conn.execute(
            """INSERT INTO quotes
               (quote_number, client_id, issue_date, valid_until,
                discount_type, discount_value, notes, status, created_by_user_id, is_public)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                quote_number,
                client_id,
                issue.isoformat(),
                valid_until.isoformat(),
                discount_type,
                discount_value,
                notes or None,
                status,
                created_by_user_id,
                int(is_public),
            ),
        )
        quote_id = cursor.lastrowid

        for item in items_list:
            conn.execute(
                """INSERT INTO quote_items (quote_id, service_id, quantity, unit_price)
                   VALUES (?, ?, ?, ?)""",
                (quote_id, item["service_id"], item["quantity"], item["unit_price"]),
            )

        conn.commit()
        return quote_id
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def get_all_quotes(
    status_filter: Optional[str] = None,
    user_id: Optional[int] = None,
    include_public: bool = True,
) -> pd.DataFrame:
    """Return quotes joined with client name, with ownership filtering."""
    conn = get_connection()
    try:
        conditions = []
        params: list[Any] = []

        if status_filter:
            conditions.append("q.status = ?")
            params.append(status_filter)

        if user_id is not None:
            if include_public:
                conditions.append("(q.created_by_user_id = ? OR q.is_public = 1)")
            else:
                conditions.append("q.created_by_user_id = ?")
            params.append(user_id)

        query = """
            SELECT q.*, c.name AS client_name
            FROM quotes q
            JOIN clients c ON q.client_id = c.id
        """
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY q.id DESC"

        return pd.read_sql_query(query, conn, params=params if params else None)
    finally:
        conn.close()


def get_quote_details(quote_id: int) -> Optional[dict[str, Any]]:
    """Return full quote data: quote info, client, items list, and totals."""
    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT q.*, c.name AS client_name, c.email AS client_email,
                      c.phone AS client_phone, c.company AS client_company,
                      c.address AS client_address
               FROM quotes q
               JOIN clients c ON q.client_id = c.id
               WHERE q.id = ?""",
            (quote_id,),
        ).fetchone()
        if not row:
            return None

        quote = dict(row)
        client = {
            "id": quote["client_id"],
            "name": quote["client_name"],
            "email": quote["client_email"],
            "phone": quote["client_phone"],
            "company": quote["client_company"],
            "address": quote["client_address"],
        }

        items_rows = conn.execute(
            """SELECT qi.*, s.name AS service_name, s.description AS service_description
               FROM quote_items qi
               JOIN services s ON qi.service_id = s.id
               WHERE qi.quote_id = ?""",
            (quote_id,),
        ).fetchall()
        items = [dict(r) for r in items_rows]

        totals = _calculate_totals(items, quote["discount_type"], quote["discount_value"])

        return {"quote": quote, "client": client, "items": items, "totals": totals}
    finally:
        conn.close()


def _calculate_totals(
    items: list[dict[str, Any]],
    discount_type: str,
    discount_value: float,
) -> dict[str, float]:
    """Compute subtotal, discount amount, and total from a list of item dicts."""
    subtotal = sum(i["quantity"] * i["unit_price"] for i in items)
    if discount_type == "percentage":
        discount = subtotal * (discount_value / 100)
    elif discount_type == "fixed":
        discount = min(discount_value, subtotal)
    else:
        discount = 0.0
    return {"subtotal": subtotal, "discount": discount, "total": subtotal - discount}


def calculate_quote_totals(quote_id: int) -> dict[str, float]:
    """Return subtotal, discount, and total for a given quote."""
    conn = get_connection()
    try:
        quote_row = conn.execute(
            "SELECT discount_type, discount_value FROM quotes WHERE id = ?",
            (quote_id,),
        ).fetchone()
        if not quote_row:
            return {"subtotal": 0, "discount": 0, "total": 0}

        items_rows = conn.execute(
            "SELECT quantity, unit_price FROM quote_items WHERE quote_id = ?",
            (quote_id,),
        ).fetchall()
        items = [dict(r) for r in items_rows]

        return _calculate_totals(items, quote_row["discount_type"], quote_row["discount_value"])
    finally:
        conn.close()


def update_quote_status(quote_id: int, new_status: str) -> bool:
    """Update the status of a quote. Returns True if a row was affected."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "UPDATE quotes SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, datetime.now().isoformat(), quote_id),
        )
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def update_quote(
    quote_id: int,
    client_id: int,
    items_list: list[dict[str, Any]],
    discount_type: str = "none",
    discount_value: float = 0,
    notes: str = "",
    status: str = "draft",
) -> bool:
    """Replace all editable fields and items of an existing quote.

    Deletes old items and inserts the new list in a single transaction.
    Returns True if the quote was updated.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            """UPDATE quotes
               SET client_id = ?, discount_type = ?, discount_value = ?,
                   notes = ?, status = ?, updated_at = ?
               WHERE id = ?""",
            (
                client_id,
                discount_type,
                discount_value,
                notes or None,
                status,
                datetime.now().isoformat(),
                quote_id,
            ),
        )
        if cursor.rowcount == 0:
            return False

        conn.execute("DELETE FROM quote_items WHERE quote_id = ?", (quote_id,))
        for item in items_list:
            conn.execute(
                """INSERT INTO quote_items (quote_id, service_id, quantity, unit_price)
                   VALUES (?, ?, ?, ?)""",
                (quote_id, item["service_id"], item["quantity"], item["unit_price"]),
            )

        conn.commit()
        return True
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def delete_quote(quote_id: int) -> bool:
    """Delete a quote and its items (cascade). Returns True if removed."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM quotes WHERE id = ?", (quote_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def get_quotes_by_client(
    client_id: int,
    user_id: Optional[int] = None,
    include_public: bool = True,
) -> pd.DataFrame:
    """Return all quotes for a given client, with ownership filtering."""
    conn = get_connection()
    try:
        conditions = ["client_id = ?"]
        params: list[Any] = [client_id]

        if user_id is not None:
            if include_public:
                conditions.append("(created_by_user_id = ? OR is_public = 1)")
            else:
                conditions.append("created_by_user_id = ?")
            params.append(user_id)

        query = "SELECT * FROM quotes WHERE " + " AND ".join(conditions) + " ORDER BY id DESC"
        return pd.read_sql_query(query, conn, params=params)
    finally:
        conn.close()
