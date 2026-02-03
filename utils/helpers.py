"""Formatting and calculation helpers for QuoteCraft."""

from __future__ import annotations

from datetime import date, datetime


def format_currency(value: float) -> str:
    """Format a number as Brazilian Real: R$ 1.234,56."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_date(d: date | datetime | str) -> str:
    """Format a date as DD/MM/YYYY."""
    if isinstance(d, str):
        d = datetime.fromisoformat(d)
    return d.strftime("%d/%m/%Y")


def format_quote_number(number: str) -> str:
    """Return the quote number as-is (already formatted by generate_quote_number)."""
    return number


def calculate_discount(
    subtotal: float,
    discount_type: str,
    discount_value: float,
) -> float:
    """Return the discount amount given a subtotal and discount parameters."""
    if discount_type == "percentage":
        return subtotal * (discount_value / 100)
    if discount_type == "fixed":
        return min(discount_value, subtotal)
    return 0.0
