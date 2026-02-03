"""Authentication service for QuoteCraft admin access."""

from __future__ import annotations

import hashlib
import os
from typing import Optional

import streamlit as st

from utils.debug import log_info, log_warning, log_debug


def get_credentials() -> tuple[str, str]:
    """Retrieve admin credentials from secrets or environment."""
    try:
        username = st.secrets["auth"]["username"]
        password_hash = st.secrets["auth"]["password_hash"]
    except (KeyError, FileNotFoundError):
        username = os.getenv("ADMIN_USERNAME", "admin")
        password_hash = os.getenv("ADMIN_PASSWORD_HASH", "")
    return username, password_hash


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against stored hash."""
    return hash_password(password) == stored_hash


def check_authentication() -> bool:
    """Return True if user is authenticated."""
    return st.session_state.get("authenticated", False)


def login(username: str, password: str) -> bool:
    """Attempt to log in. Returns True on success."""
    log_debug("Login attempt", username=username)
    stored_username, stored_hash = get_credentials()

    if not stored_hash:
        log_warning("Login failed - no credentials configured")
        st.error("Credenciais de admin nao configuradas. Verifique secrets.toml.")
        return False

    if username == stored_username and verify_password(password, stored_hash):
        st.session_state["authenticated"] = True
        st.session_state["admin_username"] = username
        log_info("Login successful", username=username)
        return True

    log_warning("Login failed - invalid credentials", username=username)
    return False


def logout() -> None:
    """Log out the current user."""
    username = st.session_state.get("admin_username", "unknown")
    st.session_state["authenticated"] = False
    st.session_state.pop("admin_username", None)
    log_info("Logout", username=username)


def require_auth() -> bool:
    """Check auth and show login form if not authenticated.

    Returns True if authenticated, False otherwise.
    Call after st.set_page_config() on each protected page.
    """
    if check_authentication():
        return True

    st.title("🔐 QuoteCraft")
    st.markdown("Acesso restrito. Por favor, faca login.")

    with st.form("login_form"):
        username = st.text_input("Usuario")
        password = st.text_input("Senha", type="password")
        submitted = st.form_submit_button("Entrar", use_container_width=True)

    if submitted:
        if login(username, password):
            st.success("Login realizado com sucesso!")
            st.rerun()
        else:
            st.error("Usuario ou senha invalidos.")

    return False


def render_logout_button() -> None:
    """Render logout button in sidebar."""
    if check_authentication():
        with st.sidebar:
            st.markdown(f"👤 **{st.session_state.get('admin_username', 'Admin')}**")
            if st.button("🚪 Sair", use_container_width=True, key="logout_btn"):
                logout()
                st.rerun()
