"""Debug and logging utilities for QuoteCraft."""

from __future__ import annotations

import logging
import os
import sys
from datetime import datetime
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import streamlit as st

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

LOG_DIR = Path(__file__).parent.parent / "logs"
LOG_FILE = LOG_DIR / "quotecraft.log"


def is_debug_mode() -> bool:
    """Check if debug mode is enabled."""
    try:
        return st.secrets.get("app", {}).get("debug", False)
    except (KeyError, FileNotFoundError):
        return os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")


def get_log_level() -> int:
    """Get logging level from config."""
    if is_debug_mode():
        return logging.DEBUG
    return logging.INFO


# ---------------------------------------------------------------------------
# Logger Setup
# ---------------------------------------------------------------------------

def setup_logger(name: str = "quotecraft") -> logging.Logger:
    """Configure and return a logger instance."""
    logger = logging.getLogger(name)

    if logger.handlers:
        return logger

    logger.setLevel(get_log_level())

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(get_log_level())
    console_format = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # File handler (if logs directory exists or can be created)
    try:
        LOG_DIR.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        file_format = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(funcName)s:%(lineno)d | %(message)s"
        )
        file_handler.setFormatter(file_format)
        logger.addHandler(file_handler)
    except (PermissionError, OSError):
        pass  # Skip file logging if not possible

    return logger


# Global logger instance
logger = setup_logger()


# ---------------------------------------------------------------------------
# Logging Functions
# ---------------------------------------------------------------------------

def log_debug(message: str, **kwargs: Any) -> None:
    """Log debug message."""
    extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.debug(f"{message} {extra}".strip())


def log_info(message: str, **kwargs: Any) -> None:
    """Log info message."""
    extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"{message} {extra}".strip())


def log_warning(message: str, **kwargs: Any) -> None:
    """Log warning message."""
    extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.warning(f"{message} {extra}".strip())


def log_error(message: str, **kwargs: Any) -> None:
    """Log error message."""
    extra = " | ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.error(f"{message} {extra}".strip())


def log_exception(message: str) -> None:
    """Log exception with traceback."""
    logger.exception(message)


# ---------------------------------------------------------------------------
# Decorators
# ---------------------------------------------------------------------------

def log_function_call(func: Callable) -> Callable:
    """Decorator to log function calls with arguments and return values."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        func_name = func.__name__
        log_debug(f"CALL {func_name}", args=args[:3], kwargs=list(kwargs.keys()))
        try:
            result = func(*args, **kwargs)
            log_debug(f"RETURN {func_name}", result_type=type(result).__name__)
            return result
        except Exception as e:
            log_error(f"ERROR {func_name}", error=str(e))
            raise
    return wrapper


# ---------------------------------------------------------------------------
# Session State Debug
# ---------------------------------------------------------------------------

def get_session_state_summary() -> dict[str, Any]:
    """Get a summary of current session state."""
    summary = {}
    for key, value in st.session_state.items():
        if key.startswith("_"):
            continue
        if isinstance(value, (str, int, float, bool, type(None))):
            summary[key] = value
        elif isinstance(value, list):
            summary[key] = f"list[{len(value)}]"
        elif isinstance(value, dict):
            summary[key] = f"dict[{len(value)}]"
        else:
            summary[key] = type(value).__name__
    return summary


def log_session_state() -> None:
    """Log current session state."""
    summary = get_session_state_summary()
    log_debug("Session State", **summary)


# ---------------------------------------------------------------------------
# Database Debug
# ---------------------------------------------------------------------------

def get_database_stats() -> dict[str, int]:
    """Get row counts for all tables."""
    from database.models import get_connection

    stats = {}
    conn = get_connection()
    try:
        for table in ["clients", "services", "quotes", "quote_items"]:
            try:
                count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                stats[table] = count
            except Exception:
                stats[table] = -1
    finally:
        conn.close()
    return stats


# ---------------------------------------------------------------------------
# Log Reader
# ---------------------------------------------------------------------------

def read_recent_logs(lines: int = 100) -> list[str]:
    """Read recent log entries from file."""
    if not LOG_FILE.exists():
        return ["No log file found."]

    try:
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            all_lines = f.readlines()
            return all_lines[-lines:]
    except Exception as e:
        return [f"Error reading logs: {e}"]


def clear_logs() -> bool:
    """Clear the log file."""
    try:
        if LOG_FILE.exists():
            LOG_FILE.unlink()
        return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Request Timing
# ---------------------------------------------------------------------------

class Timer:
    """Simple timer context manager for measuring execution time."""

    def __init__(self, name: str = "Operation"):
        self.name = name
        self.start_time: datetime | None = None
        self.end_time: datetime | None = None

    def __enter__(self) -> "Timer":
        self.start_time = datetime.now()
        return self

    def __exit__(self, *args: Any) -> None:
        self.end_time = datetime.now()
        elapsed = (self.end_time - self.start_time).total_seconds() * 1000
        log_debug(f"TIMER {self.name}", elapsed_ms=f"{elapsed:.2f}")

    @property
    def elapsed_ms(self) -> float:
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds() * 1000
        return 0.0
