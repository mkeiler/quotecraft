"""Authentication service for QuoteCraft with multi-user support."""

from __future__ import annotations

import hashlib
import os
from typing import Optional

import streamlit as st

from utils.debug import log_info, log_warning, log_debug


def get_credentials() -> tuple[str, str]:
    """Retrieve bootstrap admin credentials from secrets or environment."""
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


def get_current_user_id() -> Optional[int]:
    """Get the current authenticated user's ID."""
    return st.session_state.get("user_id")


def get_current_user_role() -> Optional[str]:
    """Get the current authenticated user's role."""
    return st.session_state.get("user_role")


def is_admin() -> bool:
    """Check if current user is an admin."""
    return get_current_user_role() == "admin"


def _try_database_login(username: str, password: str) -> Optional[dict]:
    """Try to authenticate against the database."""
    try:
        from database.user_operations import get_user_by_credentials
        return get_user_by_credentials(username, password)
    except Exception as e:
        log_debug("Database login failed", error=str(e))
        return None


def _try_secrets_login(username: str, password: str) -> bool:
    """Try to authenticate against secrets.toml (fallback)."""
    stored_username, stored_hash = get_credentials()
    if not stored_hash:
        return False
    return username == stored_username and verify_password(password, stored_hash)


def _get_or_create_bootstrap_user(username: str) -> Optional[dict]:
    """Get or create the bootstrap admin user in database."""
    try:
        from database.user_operations import get_user_by_username
        user = get_user_by_username(username)
        if user:
            return user
        return None
    except Exception:
        return None


def login(username: str, password: str) -> bool:
    """Attempt to log in. Try database first, then fallback to secrets.

    Returns True on success.
    """
    log_debug("Login attempt", username=username)

    # Try database authentication first
    user = _try_database_login(username, password)
    if user:
        st.session_state["authenticated"] = True
        st.session_state["user_id"] = user["id"]
        st.session_state["user_role"] = user["role"]
        st.session_state["admin_username"] = user["display_name"] or user["username"]
        log_info("Login successful (database)", username=username, user_id=user["id"], role=user["role"])
        return True

    # Fallback to secrets.toml for bootstrap admin
    if _try_secrets_login(username, password):
        # Find the bootstrap user in database
        bootstrap_user = _get_or_create_bootstrap_user(username)
        if bootstrap_user:
            st.session_state["authenticated"] = True
            st.session_state["user_id"] = bootstrap_user["id"]
            st.session_state["user_role"] = bootstrap_user["role"]
            st.session_state["admin_username"] = bootstrap_user["display_name"] or username
            log_info("Login successful (secrets fallback)", username=username, user_id=bootstrap_user["id"])
            return True
        else:
            # No database user found, use legacy session (admin role)
            st.session_state["authenticated"] = True
            st.session_state["user_id"] = None
            st.session_state["user_role"] = "admin"
            st.session_state["admin_username"] = username
            log_info("Login successful (legacy mode)", username=username)
            return True

    log_warning("Login failed - invalid credentials", username=username)
    return False


def logout() -> None:
    """Log out the current user."""
    username = st.session_state.get("admin_username", "unknown")
    st.session_state["authenticated"] = False
    st.session_state.pop("admin_username", None)
    st.session_state.pop("user_id", None)
    st.session_state.pop("user_role", None)
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


def require_admin() -> bool:
    """Check auth and require admin role.

    Returns True if authenticated as admin, False otherwise.
    Shows error message if user is not admin.
    """
    if not require_auth():
        return False

    if not is_admin():
        st.error("Acesso restrito a administradores.")
        st.stop()
        return False

    return True


def render_logout_button() -> None:
    """Render user info and logout button in sidebar."""
    if check_authentication():
        with st.sidebar:
            username = st.session_state.get('admin_username', 'Usuario')
            role = st.session_state.get('user_role', 'user')
            role_badge = "🔑 Admin" if role == "admin" else "👤 Usuario"

            st.markdown(f"**{username}**")
            st.caption(role_badge)

            if st.button("🚪 Sair", use_container_width=True, key="logout_btn"):
                logout()
                st.rerun()


def hide_admin_pages_css() -> None:
    """Inject CSS to hide admin-only pages from sidebar for non-admin users."""
    if not is_admin():
        st.markdown("""
            <style>
            /* Hide Debug and Usuarios pages for non-admin users */
            [data-testid="stSidebarNav"] li:has(a[href*="Debug"]),
            [data-testid="stSidebarNav"] li:has(a[href*="Usuarios"]) {
                display: none !important;
            }
            </style>
        """, unsafe_allow_html=True)
