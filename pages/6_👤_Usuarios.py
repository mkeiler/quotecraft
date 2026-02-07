"""QuoteCraft - Gerenciamento de Usuarios (Admin only)."""

from __future__ import annotations

import streamlit as st

from database.models import init_database
from database.user_operations import (
    create_user,
    delete_user,
    get_all_users,
    get_user_by_id,
    is_last_admin,
    toggle_user_status,
    update_user,
)
from services.auth import require_admin, render_logout_button, get_current_user_id
from utils.validators import validate_email, sanitize_text
from utils.debug import log_info

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Usuarios - QuoteCraft", page_icon="👤", layout="wide")
init_database()

# Admin-only access
if not require_admin():
    st.stop()

render_logout_button()

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1,h2,h3,h4,h5,h6 { font-family: 'Space Grotesk', sans-serif; color: #2E5266; }
    .stButton > button { background-color: #73A580; color: white; border-radius: 8px; padding: 0.5rem 1rem; font-weight: 500; border: none; }
    .stButton > button:hover { background-color: #5E8A6A; }
    </style>
""", unsafe_allow_html=True)

st.title("👤 Gerenciamento de Usuarios")

log_info("User management page accessed")

current_user_id = get_current_user_id()

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------

if "editing_user_id" not in st.session_state:
    st.session_state.editing_user_id = None

# ---------------------------------------------------------------------------
# Form for new user
# ---------------------------------------------------------------------------

with st.expander("➕ Novo Usuario", expanded=False):
    with st.form("new_user_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            new_username = st.text_input("Nome de usuario *", key="new_username")
            new_email = st.text_input("E-mail *", key="new_email")
            new_password = st.text_input("Senha *", type="password", key="new_password")
        with col2:
            new_display_name = st.text_input("Nome de exibicao", key="new_display_name")
            new_role = st.selectbox(
                "Papel",
                ["user", "admin"],
                format_func=lambda x: "Usuario" if x == "user" else "Administrador",
                key="new_role"
            )

        submitted = st.form_submit_button("Criar Usuario", use_container_width=True)

    if submitted:
        errors = []
        if not new_username or not new_username.strip():
            errors.append("Nome de usuario e obrigatorio.")
        if not new_email or not validate_email(new_email):
            errors.append("E-mail invalido.")
        if not new_password or len(new_password) < 4:
            errors.append("Senha deve ter pelo menos 4 caracteres.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            try:
                user_id = create_user(
                    username=sanitize_text(new_username.strip()),
                    email=new_email.strip().lower(),
                    password=new_password,
                    display_name=sanitize_text(new_display_name.strip()) if new_display_name else None,
                    role=new_role,
                    created_by_user_id=current_user_id,
                )
                st.success(f"Usuario '{new_username}' criado com sucesso!")
                st.rerun()
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    st.error("Nome de usuario ou e-mail ja existe.")
                else:
                    st.error(f"Erro ao criar usuario: {e}")

# ---------------------------------------------------------------------------
# List users
# ---------------------------------------------------------------------------

users_df = get_all_users()

if users_df.empty:
    st.info("Nenhum usuario cadastrado.")
else:
    st.subheader(f"Usuarios ({len(users_df)})")

    for _, row in users_df.iterrows():
        user_id = int(row["id"])

        with st.container(border=True):
            # Header with status
            status_icon = "✅" if row["is_active"] else "❌"
            role_label = "🔑 Admin" if row["role"] == "admin" else "👤 Usuario"

            col_info, col_actions = st.columns([3, 1])

            with col_info:
                st.markdown(f"**{row['username']}**")
                st.caption(f"{row['display_name'] or '-'} — {row['email']}")
                st.caption(f"{status_icon} Ativo  |  {role_label}")

            with col_actions:
                # Edit button
                if st.button("✏️", key=f"edit_user_{user_id}", help="Editar"):
                    st.session_state.editing_user_id = user_id
                    st.rerun()

        # Edit form (inline)
        if st.session_state.editing_user_id == user_id:
            user_data = get_user_by_id(user_id)
            if user_data:
                with st.form(f"edit_user_form_{user_id}"):
                    st.markdown(f"**Editando: {user_data['username']}**")

                    col1, col2 = st.columns(2)
                    with col1:
                        edit_email = st.text_input("E-mail", value=user_data["email"])
                        edit_display_name = st.text_input("Nome de exibicao", value=user_data["display_name"] or "")
                        edit_password = st.text_input("Nova senha (deixe vazio para manter)", type="password")
                    with col2:
                        edit_role = st.selectbox(
                            "Papel",
                            ["user", "admin"],
                            index=0 if user_data["role"] == "user" else 1,
                            format_func=lambda x: "Usuario" if x == "user" else "Administrador",
                        )
                        edit_active = st.checkbox("Ativo", value=bool(user_data["is_active"]))

                    col_save, col_cancel, col_delete = st.columns(3)

                    with col_save:
                        save_clicked = st.form_submit_button("💾 Salvar", use_container_width=True)

                    with col_cancel:
                        cancel_clicked = st.form_submit_button("Cancelar", use_container_width=True)

                    with col_delete:
                        delete_clicked = st.form_submit_button("🗑️ Excluir", use_container_width=True)

                if save_clicked:
                    # Check if trying to demote/deactivate last admin
                    if user_data["role"] == "admin" and (edit_role != "admin" or not edit_active):
                        if is_last_admin(user_id):
                            st.error("Nao e possivel remover o ultimo administrador ativo.")
                            st.stop()

                    update_data = {
                        "email": edit_email.strip().lower(),
                        "display_name": edit_display_name.strip() or None,
                        "role": edit_role,
                        "is_active": int(edit_active),
                    }
                    if edit_password:
                        update_data["password"] = edit_password

                    try:
                        update_user(user_id, **update_data)
                        st.success("Usuario atualizado!")
                        st.session_state.editing_user_id = None
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao atualizar: {e}")

                if cancel_clicked:
                    st.session_state.editing_user_id = None
                    st.rerun()

                if delete_clicked:
                    # Cannot delete yourself
                    if user_id == current_user_id:
                        st.error("Voce nao pode excluir seu proprio usuario.")
                    elif is_last_admin(user_id) and user_data["role"] == "admin":
                        st.error("Nao e possivel excluir o ultimo administrador.")
                    else:
                        st.session_state[f"confirm_delete_user_{user_id}"] = True

        # Delete confirmation
        if st.session_state.get(f"confirm_delete_user_{user_id}"):
            st.warning(f"Tem certeza que deseja excluir o usuario **{row['username']}**?")
            col1, col2, _ = st.columns([1, 1, 4])
            if col1.button("Sim, excluir", key=f"yes_del_user_{user_id}"):
                delete_user(user_id)
                st.success("Usuario excluido.")
                del st.session_state[f"confirm_delete_user_{user_id}"]
                st.session_state.editing_user_id = None
                st.rerun()
            if col2.button("Cancelar", key=f"no_del_user_{user_id}"):
                del st.session_state[f"confirm_delete_user_{user_id}"]
                st.rerun()
