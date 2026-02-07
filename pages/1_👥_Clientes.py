"""QuoteCraft - Gerenciamento de Clientes."""

from __future__ import annotations

import streamlit as st

from database.models import init_database
from database.operations import (
    can_modify_item,
    create_client,
    delete_client,
    get_all_clients,
    get_client_by_id,
    search_clients,
    toggle_item_visibility,
    update_client,
)
from services.auth import require_auth, render_logout_button, get_current_user_id, is_admin, hide_admin_pages_css
from utils.validators import sanitize_text, validate_email, validate_phone

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Clientes - QuoteCraft", page_icon="👥", layout="wide")
init_database()

# Authentication check
if not require_auth():
    st.stop()

render_logout_button()
hide_admin_pages_css()

# Get user context
current_user_id = get_current_user_id()
user_is_admin = is_admin()

# Re-apply custom CSS (each page is a separate script)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1,h2,h3,h4,h5,h6 { font-family: 'Space Grotesk', sans-serif; color: #2E5266; }
    .stButton > button { background-color: #73A580; color: white; border-radius: 8px; padding: 0.5rem 1rem; font-weight: 500; border: none; }
    .stButton > button:hover { background-color: #5E8A6A; }
    /* Prevent columns from stacking on mobile */
    [data-testid="stHorizontalBlock"] {
        flex-wrap: nowrap !important;
        gap: 0.5rem;
    }
    [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
        flex: 1 1 0 !important;
        min-width: 0 !important;
    }
    /* Compact buttons on mobile */
    @media (max-width: 640px) {
        .stButton > button { padding: 0.4rem 0.5rem; font-size: 0.85rem; }
    }
    </style>
""", unsafe_allow_html=True)

st.title("👥 Clientes")

# ---------------------------------------------------------------------------
# A) Formulário de Cadastro
# ---------------------------------------------------------------------------

with st.expander("➕ Novo Cliente", expanded=False):
    with st.form("new_client_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nome *")
            email = st.text_input("E-mail *")
            phone = st.text_input("Telefone")
        with col2:
            company = st.text_input("Empresa")
            address = st.text_area("Endereço", height=80)

        # Visibility option
        is_public = st.checkbox(
            "🌐 Visivel para todos os usuarios",
            value=False,
            help="Marque para que outros usuarios possam ver este cliente"
        )

        submitted = st.form_submit_button("Salvar Cliente", use_container_width=True)

    if submitted:
        name = sanitize_text(name)
        email = sanitize_text(email).lower()
        phone = sanitize_text(phone)

        if not name:
            st.error("O nome é obrigatório.")
        elif not validate_email(email):
            st.error("E-mail inválido.")
        elif phone and not validate_phone(phone):
            st.error("Telefone inválido. Use um formato brasileiro válido.")
        else:
            try:
                create_client(
                    name=name,
                    email=email,
                    phone=phone or None,
                    company=sanitize_text(company) or None,
                    address=sanitize_text(address) or None,
                    created_by_user_id=current_user_id,
                    is_public=is_public,
                )
                st.success(f"Cliente **{name}** cadastrado com sucesso!")
                st.rerun()
            except Exception as e:
                if "UNIQUE constraint" in str(e):
                    st.error("Já existe um cliente com este e-mail.")
                else:
                    st.error(f"Erro ao cadastrar cliente: {e}")

# ---------------------------------------------------------------------------
# B) Busca / Filtro
# ---------------------------------------------------------------------------

st.subheader("Buscar Clientes")
search_col, btn_col = st.columns([4, 1])
with search_col:
    query = st.text_input("Buscar por nome ou e-mail", label_visibility="collapsed", placeholder="Buscar por nome ou e-mail...")
with btn_col:
    clear = st.button("Limpar Filtro", use_container_width=True)

if clear:
    query = ""

# ---------------------------------------------------------------------------
# C) Listagem
# ---------------------------------------------------------------------------

# Get clients with ownership filtering (admin sees all, users see own + public)
filter_user_id = None if user_is_admin else current_user_id

if query:
    df = search_clients(query, user_id=filter_user_id)
else:
    df = get_all_clients(user_id=filter_user_id)

if df.empty:
    st.info("Nenhum cliente cadastrado." if not query else "Nenhum resultado encontrado.")
else:
    st.subheader(f"Clientes ({len(df)})")
    for _, row in df.iterrows():
        client_id = int(row['id'])
        is_owner = row.get("created_by_user_id") == current_user_id
        can_edit = can_modify_item("clients", client_id, current_user_id, user_is_admin)
        visibility_icon = "🌐" if row.get("is_public") else "🔒"

        with st.container(border=True):
            # Header with visibility and ownership info
            header_parts = [f"**{row['name']}**", f"— {row['email']}", visibility_icon]
            st.markdown(" ".join(header_parts))

            phone_info = row.get("phone") or "—"
            company_info = row.get("company") or "—"
            caption_parts = [f"📱 {phone_info}", f"🏢 {company_info}"]

            # Show ownership indicator for non-owners
            if not is_owner and not user_is_admin:
                caption_parts.append("👤 De outro usuario")

            st.caption("  •  ".join(caption_parts))

            # Action buttons - only for owners or admin
            if can_edit:
                b1, b2, b3 = st.columns(3)
                if b1.button("✏️", key=f"edit_{client_id}", use_container_width=True, help="Editar"):
                    st.session_state["editing_client"] = client_id
                if b2.button(visibility_icon, key=f"vis_{client_id}", use_container_width=True, help="Alternar visibilidade"):
                    toggle_item_visibility("clients", client_id)
                    st.rerun()
                if b3.button("🗑️", key=f"del_{client_id}", use_container_width=True, help="Excluir"):
                    st.session_state["confirm_delete_client"] = client_id

# ---------------------------------------------------------------------------
# D) Confirmação de Exclusão
# ---------------------------------------------------------------------------

if "confirm_delete_client" in st.session_state:
    cid = st.session_state["confirm_delete_client"]
    client = get_client_by_id(cid)
    if client:
        # Verify permission again
        if not can_modify_item("clients", cid, current_user_id, user_is_admin):
            st.error("Voce nao tem permissao para excluir este cliente.")
            del st.session_state["confirm_delete_client"]
        else:
            st.warning(f"Tem certeza que deseja excluir **{client['name']}**?")
            c1, c2, _ = st.columns([1, 1, 4])
            if c1.button("Sim, excluir", key="confirm_del_yes"):
                try:
                    delete_client(cid)
                    st.success("Cliente excluído.")
                except Exception as e:
                    st.error(f"Erro ao excluir: {e}")
                del st.session_state["confirm_delete_client"]
                st.rerun()
            if c2.button("Cancelar", key="confirm_del_no"):
                del st.session_state["confirm_delete_client"]
                st.rerun()

# ---------------------------------------------------------------------------
# E) Modal de Edição
# ---------------------------------------------------------------------------

if "editing_client" in st.session_state:
    cid = st.session_state["editing_client"]
    client = get_client_by_id(cid)
    if client:
        # Verify permission
        if not can_modify_item("clients", cid, current_user_id, user_is_admin):
            st.error("Voce nao tem permissao para editar este cliente.")
            del st.session_state["editing_client"]
        else:
            st.subheader(f"Editando: {client['name']}")
            with st.form("edit_client_form"):
                col1, col2 = st.columns(2)
                with col1:
                    e_name = st.text_input("Nome *", value=client["name"])
                    e_email = st.text_input("E-mail *", value=client["email"])
                    e_phone = st.text_input("Telefone", value=client.get("phone") or "")
                with col2:
                    e_company = st.text_input("Empresa", value=client.get("company") or "")
                    e_address = st.text_area("Endereço", value=client.get("address") or "", height=80)

                # Visibility toggle in edit form
                e_is_public = st.checkbox(
                    "🌐 Visivel para todos os usuarios",
                    value=bool(client.get("is_public")),
                    help="Marque para que outros usuarios possam ver este cliente"
                )

                btn_col1, btn_col2, _ = st.columns([1, 1, 4])
                update_btn = btn_col1.form_submit_button("Atualizar")
                cancel_btn = btn_col2.form_submit_button("Cancelar")

            if cancel_btn:
                del st.session_state["editing_client"]
                st.rerun()

            if update_btn:
                e_name = sanitize_text(e_name)
                e_email = sanitize_text(e_email).lower()
                e_phone = sanitize_text(e_phone)

                if not e_name:
                    st.error("O nome é obrigatório.")
                elif not validate_email(e_email):
                    st.error("E-mail inválido.")
                elif e_phone and not validate_phone(e_phone):
                    st.error("Telefone inválido.")
                else:
                    try:
                        update_client(
                            cid,
                            name=e_name,
                            email=e_email,
                            phone=e_phone or None,
                            company=sanitize_text(e_company) or None,
                            address=sanitize_text(e_address) or None,
                            is_public=int(e_is_public),
                        )
                        st.success("Cliente atualizado com sucesso!")
                        del st.session_state["editing_client"]
                        st.rerun()
                    except Exception as e:
                        if "UNIQUE constraint" in str(e):
                            st.error("Já existe outro cliente com este e-mail.")
                        else:
                            st.error(f"Erro ao atualizar: {e}")
