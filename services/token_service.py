"""Token service for passwordless quote access."""

from __future__ import annotations

import os
import secrets
from datetime import datetime, timedelta
from typing import Optional

import streamlit as st

from database.models import get_connection
from utils.debug import log_debug, log_info, log_warning


def generate_token(length: int = 32) -> str:
    """Generate a cryptographically secure URL-safe token."""
    return secrets.token_urlsafe(length)


def get_token_expiry_days() -> int:
    """Get token expiry configuration."""
    try:
        return int(st.secrets["app"]["token_expiry_days"])
    except (KeyError, FileNotFoundError):
        return int(os.getenv("TOKEN_EXPIRY_DAYS", "30"))


def create_quote_token(quote_id: int) -> str:
    """Generate and store a new token for a quote.

    Returns the generated token.
    """
    token = generate_token()
    expiry_days = get_token_expiry_days()
    expires_at = datetime.now() + timedelta(days=expiry_days)

    conn = get_connection()
    try:
        conn.execute(
            """UPDATE quotes
               SET view_token = ?, token_expires_at = ?, updated_at = ?
               WHERE id = ?""",
            (token, expires_at.isoformat(), datetime.now().isoformat(), quote_id),
        )
        conn.commit()
        log_info("Token created", quote_id=quote_id, expires_in_days=expiry_days)
        return token
    finally:
        conn.close()


def get_quote_by_token(token: str) -> Optional[int]:
    """Retrieve quote ID by token if valid and not expired.

    Returns quote_id or None if token is invalid/expired.
    """
    if not token:
        log_debug("Token validation failed - empty token")
        return None

    conn = get_connection()
    try:
        row = conn.execute(
            """SELECT id, token_expires_at FROM quotes WHERE view_token = ?""",
            (token,),
        ).fetchone()

        if not row:
            log_warning("Token validation failed - token not found", token=token[:8] + "...")
            return None

        # Check expiration if set
        expires_at = row["token_expires_at"]
        if expires_at:
            expiry_dt = datetime.fromisoformat(expires_at)
            if datetime.now() > expiry_dt:
                log_warning("Token validation failed - expired", quote_id=row["id"])
                return None  # Token expired

        log_debug("Token validated", quote_id=row["id"])
        return row["id"]
    finally:
        conn.close()


def get_token_for_quote(quote_id: int) -> Optional[str]:
    """Get existing token for a quote, or None if not set."""
    conn = get_connection()
    try:
        row = conn.execute(
            "SELECT view_token FROM quotes WHERE id = ?",
            (quote_id,),
        ).fetchone()
        return row["view_token"] if row else None
    finally:
        conn.close()


def ensure_quote_token(quote_id: int) -> str:
    """Get existing token or create new one if not exists."""
    existing = get_token_for_quote(quote_id)
    if existing:
        return existing
    return create_quote_token(quote_id)
