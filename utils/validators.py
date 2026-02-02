"""Input validation helpers for QuoteCraft."""

from __future__ import annotations

import re


def validate_email(email: str) -> bool:
    """Return True if *email* looks like a valid e-mail address."""
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email.strip()))


def validate_phone(phone: str) -> bool:
    """Return True if *phone* matches common Brazilian formats.

    Accepted examples:
        (11) 91234-5678, 11912345678, +55 11 91234-5678,
        (11) 1234-5678, 1112345678
    """
    cleaned = re.sub(r"[\s\-().+]", "", phone)
    # With country code 55: 12 or 13 digits; without: 10 or 11 digits
    return bool(re.match(r"^(55)?\d{10,11}$", cleaned))


def validate_price(price: float | int | str) -> bool:
    """Return True if *price* is a number >= 0."""
    try:
        return float(price) >= 0
    except (ValueError, TypeError):
        return False


def sanitize_text(text: str) -> str:
    """Remove potentially dangerous characters from user input."""
    if not text:
        return ""
    # Strip HTML/script tags
    text = re.sub(r"<[^>]*>", "", text)
    # Remove null bytes
    text = text.replace("\x00", "")
    return text.strip()
