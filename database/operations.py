"""CRUD operations for clients, services, and quotes."""

from __future__ import annotations

import sqlite3
from datetime import date, datetime, timedelta
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
                discount_type, discount_value, notes, status)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                quote_number,
                client_id,
                issue.isoformat(),
                valid_until.isoformat(),
                discount_type,
                discount_value,
                notes or None,
                status,
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


def get_all_quotes(status_filter: Optional[str] = None) -> pd.DataFrame:
    """Return quotes joined with client name, optionally filtered by status."""
    conn = get_connection()
    try:
        query = """
            SELECT q.*, c.name AS client_name
            FROM quotes q
            JOIN clients c ON q.client_id = c.id
        """
        params: list[Any] = []
        if status_filter:
            query += " WHERE q.status = ?"
            params.append(status_filter)
        query += " ORDER BY q.id DESC"
        return pd.read_sql_query(query, conn, params=params)
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


def get_quotes_by_client(client_id: int) -> pd.DataFrame:
    """Return all quotes for a given client."""
    conn = get_connection()
    try:
        return pd.read_sql_query(
            "SELECT * FROM quotes WHERE client_id = ? ORDER BY id DESC",
            conn,
            params=(client_id,),
        )
    finally:
        conn.close()
