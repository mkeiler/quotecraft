"""QuoteCraft - Gerenciamento de Clientes."""

from __future__ import annotations

import streamlit as st

from database.models import init_database
from database.operations import (
    create_client,
    delete_client,
    get_all_clients,
    get_client_by_id,
    search_clients,
    update_client,
)
from utils.validators import sanitize_text, validate_email, validate_phone

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Clientes - QuoteCraft", page_icon="👥", layout="wide")
init_database()

# Re-apply custom CSS (each page is a separate script)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1,h2,h3,h4,h5,h6 { font-family: 'Space Grotesk', sans-serif; color: #2E5266; }
    .stButton > button { background-color: #73A580; color: white; border-radius: 8px; padding: 0.5rem 1.5rem; font-weight: 500; border: none; }
    .stButton > button:hover { background-color: #5E8A6A; }
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
            address = st.text_area("Endereço", height=120)

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

df = search_clients(query) if query else get_all_clients()

if df.empty:
    st.info("Nenhum cliente cadastrado." if not query else "Nenhum resultado encontrado.")
else:
    st.subheader(f"Clientes ({len(df)})")
    for _, row in df.iterrows():
        with st.container():
            cols = st.columns([3, 3, 2, 2, 1, 1])
            cols[0].write(f"**{row['name']}**")
            cols[1].write(row["email"])
            cols[2].write(row.get("phone") or "—")
            cols[3].write(row.get("company") or "—")

            if cols[4].button("✏️", key=f"edit_{row['id']}", help="Editar"):
                st.session_state[f"editing_client"] = int(row["id"])
            if cols[5].button("🗑️", key=f"del_{row['id']}", help="Deletar"):
                st.session_state[f"confirm_delete_client"] = int(row["id"])

        st.divider()

# ---------------------------------------------------------------------------
# D) Confirmação de Exclusão
# ---------------------------------------------------------------------------

if "confirm_delete_client" in st.session_state:
    cid = st.session_state["confirm_delete_client"]
    client = get_client_by_id(cid)
    if client:
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
        st.subheader(f"Editando: {client['name']}")
        with st.form("edit_client_form"):
            col1, col2 = st.columns(2)
            with col1:
                e_name = st.text_input("Nome *", value=client["name"])
                e_email = st.text_input("E-mail *", value=client["email"])
                e_phone = st.text_input("Telefone", value=client.get("phone") or "")
            with col2:
                e_company = st.text_input("Empresa", value=client.get("company") or "")
                e_address = st.text_area("Endereço", value=client.get("address") or "", height=120)

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
                    )
                    st.success("Cliente atualizado com sucesso!")
                    del st.session_state["editing_client"]
                    st.rerun()
                except Exception as e:
                    if "UNIQUE constraint" in str(e):
                        st.error("Já existe outro cliente com este e-mail.")
                    else:
                        st.error(f"Erro ao atualizar: {e}")
