"""QuoteCraft - Gerenciamento de Serviços."""

from __future__ import annotations

import streamlit as st

from database.models import init_database
from database.operations import (
    create_service,
    delete_service,
    get_all_services,
    get_service_by_id,
    toggle_service_status,
    update_service,
)
from services.auth import require_auth, render_logout_button
from utils.validators import sanitize_text, validate_price

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Serviços - QuoteCraft", page_icon="🛠️", layout="wide")
init_database()

# Authentication check
if not require_auth():
    st.stop()

render_logout_button()

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

st.title("🛠️ Serviços")


def format_brl(value: float) -> str:
    """Format a float as Brazilian Real (R$ 1.234,56)."""
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------------------------------------------------------------------------
# A) Formulário de Cadastro
# ---------------------------------------------------------------------------

with st.expander("➕ Novo Serviço", expanded=False):
    with st.form("new_service_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Nome *")
            base_price = st.text_input("Preço Base (R$) *", placeholder="0,00")
        with col2:
            description = st.text_area("Descrição", height=80)
            category = st.text_input("Categoria")

        submitted = st.form_submit_button("Adicionar Serviço", use_container_width=True)

    if submitted:
        name = sanitize_text(name)
        description = sanitize_text(description)
        category = sanitize_text(category)

        # Parse price: accept both "1234.56" and "1234,56"
        price_str = base_price.replace(".", "").replace(",", ".")
        try:
            price_val = float(price_str)
        except ValueError:
            price_val = -1

        if not name:
            st.error("O nome é obrigatório.")
        elif not validate_price(price_val):
            st.error("Preço inválido. Informe um valor numérico >= 0.")
        else:
            try:
                create_service(
                    name=name,
                    description=description or None,
                    base_price=price_val,
                    category=category or None,
                )
                st.success(f"Serviço **{name}** adicionado com sucesso!")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao cadastrar serviço: {e}")

# ---------------------------------------------------------------------------
# B) Filtros
# ---------------------------------------------------------------------------

st.subheader("Filtros")
fcol1, fcol2 = st.columns([1, 3])
with fcol1:
    active_only = st.checkbox("Apenas ativos", value=True)

df = get_all_services(active_only=active_only)

# Category filter (dynamic)
if not df.empty and "category" in df.columns:
    categories = sorted(df["category"].dropna().unique().tolist())
    if categories:
        with fcol2:
            selected_cat = st.selectbox("Categoria", ["Todas"] + categories)
        if selected_cat != "Todas":
            df = df[df["category"] == selected_cat]

# ---------------------------------------------------------------------------
# C) Listagem
# ---------------------------------------------------------------------------

if df.empty:
    st.info("Nenhum serviço cadastrado." if not active_only else "Nenhum serviço ativo encontrado.")
else:
    st.subheader(f"Serviços ({len(df)})")
    for _, row in df.iterrows():
        with st.container(border=True):
            st.markdown(f"**{row['name']}** — {format_brl(row['base_price'])}")
            desc = row.get("description") or "—"
            desc_truncated = desc[:60] + ("..." if len(str(desc)) > 60 else "")
            status_label = "✅ Ativo" if row["is_active"] else "❌ Inativo"
            st.caption(f"{desc_truncated}  •  {status_label}")
            b1, b2, b3 = st.columns(3)
            if b1.button("✏️", key=f"edit_svc_{row['id']}", use_container_width=True, help="Editar"):
                st.session_state["editing_service"] = int(row["id"])
            if b2.button("🔄", key=f"toggle_svc_{row['id']}", use_container_width=True, help="Ativar/Desativar"):
                toggle_service_status(int(row["id"]))
                st.rerun()
            if b3.button("🗑️", key=f"del_svc_{row['id']}", use_container_width=True, help="Excluir"):
                st.session_state["confirm_delete_service"] = int(row["id"])

# ---------------------------------------------------------------------------
# D) Confirmação de Exclusão (soft-delete)
# ---------------------------------------------------------------------------

if "confirm_delete_service" in st.session_state:
    sid = st.session_state["confirm_delete_service"]
    svc = get_service_by_id(sid)
    if svc:
        st.warning(f"Tem certeza que deseja excluir o serviço **{svc['name']}**?")
        c1, c2, _ = st.columns([1, 1, 4])
        if c1.button("Sim, excluir", key="confirm_svc_del_yes"):
            delete_service(sid)
            st.success("Serviço excluído.")
            del st.session_state["confirm_delete_service"]
            st.rerun()
        if c2.button("Cancelar", key="confirm_svc_del_no"):
            del st.session_state["confirm_delete_service"]
            st.rerun()

# ---------------------------------------------------------------------------
# E) Modal de Edição
# ---------------------------------------------------------------------------

if "editing_service" in st.session_state:
    sid = st.session_state["editing_service"]
    svc = get_service_by_id(sid)
    if svc:
        st.subheader(f"Editando: {svc['name']}")
        with st.form("edit_service_form"):
            col1, col2 = st.columns(2)
            with col1:
                e_name = st.text_input("Nome *", value=svc["name"])
                e_price = st.text_input(
                    "Preço Base (R$) *",
                    value=str(svc["base_price"]).replace(".", ","),
                )
            with col2:
                e_desc = st.text_area("Descrição", value=svc.get("description") or "", height=80)
                e_cat = st.text_input("Categoria", value=svc.get("category") or "")

            btn1, btn2, _ = st.columns([1, 1, 4])
            update_btn = btn1.form_submit_button("Atualizar")
            cancel_btn = btn2.form_submit_button("Cancelar")

        if cancel_btn:
            del st.session_state["editing_service"]
            st.rerun()

        if update_btn:
            e_name = sanitize_text(e_name)
            price_str = e_price.replace(".", "").replace(",", ".")
            try:
                price_val = float(price_str)
            except ValueError:
                price_val = -1

            if not e_name:
                st.error("O nome é obrigatório.")
            elif not validate_price(price_val):
                st.error("Preço inválido.")
            else:
                try:
                    update_service(
                        sid,
                        name=e_name,
                        description=sanitize_text(e_desc) or None,
                        base_price=price_val,
                        category=sanitize_text(e_cat) or None,
                    )
                    st.success("Serviço atualizado com sucesso!")
                    del st.session_state["editing_service"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao atualizar: {e}")
