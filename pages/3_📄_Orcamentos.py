"""QuoteCraft - Gerenciamento de Orçamentos."""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from database.models import init_database
from database.operations import (
    can_modify_item,
    create_quote,
    delete_quote,
    get_all_clients,
    get_all_quotes,
    get_all_services,
    get_quote_details,
    toggle_item_visibility,
    update_quote,
    update_quote_status,
)
from services.auth import require_auth, render_logout_button, get_current_user_id, is_admin, hide_admin_pages_css
from services.email_service import send_quote_email
from services.pdf_generator import QuotePDFGenerator
from services.token_service import ensure_quote_token
from utils.debug import log_info, log_debug, log_error
from utils.helpers import calculate_discount, format_currency, format_date

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Orçamentos - QuoteCraft", page_icon="📄", layout="wide")
init_database()

# Authentication check
if not require_auth():
    st.stop()

render_logout_button()
hide_admin_pages_css()

# Get user context
current_user_id = get_current_user_id()
user_is_admin = is_admin()

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

st.title("📄 Orçamentos")

# ---------------------------------------------------------------------------
# Session state defaults
# ---------------------------------------------------------------------------

if "page_view" not in st.session_state:
    st.session_state.page_view = "list"
if "selected_services" not in st.session_state:
    st.session_state.selected_services: list[dict[str, Any]] = []
if "editing_quote_id" not in st.session_state:
    st.session_state.editing_quote_id = None
if "viewing_quote_id" not in st.session_state:
    st.session_state.viewing_quote_id = None

STATUS_LABELS = {
    "draft": "📝 Rascunho",
    "sent": "📨 Enviado",
    "approved": "✅ Aprovado",
    "rejected": "❌ Rejeitado",
}


# ---------------------------------------------------------------------------
# Navigation helper
# ---------------------------------------------------------------------------

def navigate_to(view: str, **kwargs: Any) -> None:
    """Switch the active view and clean up stale state."""
    st.session_state.page_view = view

    if view == "list":
        st.session_state.editing_quote_id = None
        st.session_state.viewing_quote_id = None
        st.session_state.selected_services = []
        for k in list(st.session_state.keys()):
            if k.startswith("_edit_") or k == "_loaded_edit_id":
                del st.session_state[k]

    elif view == "form":
        st.session_state.viewing_quote_id = None
        if "quote_id" in kwargs:
            st.session_state.editing_quote_id = kwargs["quote_id"]
        else:
            st.session_state.editing_quote_id = None
            st.session_state.selected_services = []
            for k in list(st.session_state.keys()):
                if k.startswith("_edit_") or k == "_loaded_edit_id":
                    del st.session_state[k]

    elif view == "detail":
        st.session_state.editing_quote_id = None
        st.session_state.selected_services = []
        if "quote_id" in kwargs:
            st.session_state.viewing_quote_id = kwargs["quote_id"]

    st.rerun()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

# Get data with ownership filtering (admin sees all, users see own + public)
filter_user_id = None if user_is_admin else current_user_id
clients_df = get_all_clients(user_id=filter_user_id)
services_df = get_all_services(active_only=True, user_id=filter_user_id)


# ---------------------------------------------------------------------------
# Dialog: add service
# ---------------------------------------------------------------------------

@st.dialog("Adicionar Serviço")
def add_service_dialog(services_df: pd.DataFrame) -> None:
    """Modal for selecting a service, quantity and price."""
    svc_options = {
        row["id"]: row for _, row in services_df.iterrows()
    }
    svc_ids = list(svc_options.keys())
    selected_id = st.selectbox(
        "Serviço",
        options=svc_ids,
        format_func=lambda x: f"{svc_options[x]['name']} ({format_currency(svc_options[x]['base_price'])})",
    )
    svc = svc_options[selected_id]

    col1, col2 = st.columns(2)
    with col1:
        qty = st.number_input("Quantidade", min_value=1, value=1)
    with col2:
        price = st.number_input(
            "Preço unitário (R$)",
            min_value=0.0,
            value=float(svc["base_price"]),
            step=0.01,
            format="%.2f",
        )

    st.markdown(f"**Subtotal do item:** {format_currency(qty * price)}")

    if st.button("Confirmar", use_container_width=True):
        st.session_state.selected_services.append({
            "service_id": int(selected_id),
            "name": svc["name"],
            "quantity": int(qty),
            "unit_price": float(price),
        })
        st.rerun()


# ---------------------------------------------------------------------------
# VIEW: List
# ---------------------------------------------------------------------------

def render_list_view(clients_df: pd.DataFrame) -> None:
    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.subheader("Orçamentos")
    with header_right:
        if st.button("➕ Novo Orçamento", use_container_width=True):
            navigate_to("form")

    # -- Filters --
    f1, f2 = st.columns(2)
    with f1:
        status_filter = st.selectbox(
            "Status",
            ["Todos", "draft", "sent", "approved", "rejected"],
            format_func=lambda x: "Todos" if x == "Todos" else STATUS_LABELS[x],
        )
    with f2:
        client_filter = st.selectbox(
            "Cliente",
            ["Todos"] + [row["name"] for _, row in clients_df.iterrows()],
        )

    quotes_df = get_all_quotes(
        status_filter=status_filter if status_filter != "Todos" else None,
        user_id=filter_user_id,
    )
    if client_filter != "Todos":
        quotes_df = quotes_df[quotes_df["client_name"] == client_filter]

    if quotes_df.empty:
        st.info("Nenhum orçamento encontrado.")
        return

    for _, qrow in quotes_df.iterrows():
        qid = int(qrow["id"])
        is_owner = qrow.get("created_by_user_id") == current_user_id
        can_edit = can_modify_item("quotes", qid, current_user_id, user_is_admin)
        visibility_icon = "🌐" if qrow.get("is_public") else "🔒"

        with st.container(border=True):
            st.markdown(f"**{qrow['quote_number']}** — {qrow['client_name']} {visibility_icon}")
            caption_parts = [format_date(qrow['issue_date']), STATUS_LABELS.get(qrow['status'], qrow['status'])]
            if not is_owner and not user_is_admin:
                caption_parts.append("👤 De outro usuario")
            st.caption("  \u2022  ".join(caption_parts))

            # View button available to all who can see, other actions only for owners/admin
            if can_edit:
                b1, b2, b3, b4, b5 = st.columns(5)
                if b1.button("👁️", key=f"view_{qid}", use_container_width=True, help="Ver detalhes"):
                    navigate_to("detail", quote_id=qid)
                if b2.button("📄", key=f"pdf_{qid}", use_container_width=True, help="Gerar PDF"):
                    st.session_state[f"gen_pdf_{qid}"] = True
                if b3.button("📧", key=f"email_{qid}", use_container_width=True, help="Enviar por email"):
                    st.session_state[f"send_email_{qid}"] = True
                if b4.button("✏️", key=f"edit_{qid}", use_container_width=True, help="Editar"):
                    navigate_to("form", quote_id=qid)
                if b5.button("🗑️", key=f"del_{qid}", use_container_width=True, help="Excluir"):
                    st.session_state[f"confirm_del_quote_{qid}"] = True
            else:
                # Read-only actions for public quotes from other users
                b1, b2 = st.columns(2)
                if b1.button("👁️", key=f"view_{qid}", use_container_width=True, help="Ver detalhes"):
                    navigate_to("detail", quote_id=qid)
                if b2.button("📄", key=f"pdf_{qid}", use_container_width=True, help="Gerar PDF"):
                    st.session_state[f"gen_pdf_{qid}"] = True

        # -- PDF generation --
        if st.session_state.get(f"gen_pdf_{qid}"):
            details = get_quote_details(qid)
            if details:
                with st.spinner("Gerando PDF..."):
                    gen = QuotePDFGenerator(details)
                    pdf_path = gen.generate()
                with open(pdf_path, "rb") as f:
                    st.download_button(
                        f"⬇️ Baixar {details['quote']['quote_number']}",
                        data=f,
                        file_name=pdf_path.name,
                        mime="application/pdf",
                        key=f"dl_pdf_{qid}",
                    )
            del st.session_state[f"gen_pdf_{qid}"]

        # -- Delete confirmation --
        if st.session_state.get(f"confirm_del_quote_{qid}"):
            st.warning(f"Excluir orçamento **{qrow['quote_number']}**?")
            dc1, dc2, _ = st.columns([1, 1, 4])
            if dc1.button("Sim", key=f"yes_del_q_{qid}"):
                delete_quote(qid)
                log_info("Quote deleted", quote_id=qid, quote_number=qrow['quote_number'])
                st.success("Orçamento excluído.")
                del st.session_state[f"confirm_del_quote_{qid}"]
                st.rerun()
            if dc2.button("Cancelar", key=f"no_del_q_{qid}"):
                del st.session_state[f"confirm_del_quote_{qid}"]
                st.rerun()

        # -- Email sending --
        if st.session_state.get(f"send_email_{qid}"):
            log_info("Preparing to send quote email", quote_id=qid)
            details = get_quote_details(qid)
            if details:
                st.info(f"Enviar orcamento para: **{details['client']['email']}**")
                attach_pdf = st.checkbox("Anexar PDF", value=True, key=f"attach_pdf_{qid}")

                ec1, ec2, _ = st.columns([1, 1, 4])
                if ec1.button("Enviar", key=f"confirm_email_{qid}"):
                    token = ensure_quote_token(qid)

                    pdf_path = None
                    if attach_pdf:
                        gen = QuotePDFGenerator(details)
                        pdf_path = gen.generate()

                    success, message = send_quote_email(
                        to_email=details["client"]["email"],
                        quote_data=details,
                        view_token=token,
                        attach_pdf=attach_pdf,
                        pdf_path=pdf_path,
                    )

                    if success:
                        if details["quote"]["status"] == "draft":
                            update_quote_status(qid, "sent")
                        st.success(message)
                    else:
                        st.error(message)

                    del st.session_state[f"send_email_{qid}"]
                    st.rerun()

                if ec2.button("Cancelar", key=f"cancel_email_{qid}"):
                    del st.session_state[f"send_email_{qid}"]
                    st.rerun()


# ---------------------------------------------------------------------------
# VIEW: Form (create / edit)
# ---------------------------------------------------------------------------

def render_form_view(clients_df: pd.DataFrame, services_df: pd.DataFrame) -> None:
    is_editing = st.session_state.editing_quote_id is not None

    # -- Pre-load edit data --
    if is_editing and st.session_state.get("_loaded_edit_id") != st.session_state.editing_quote_id:
        details = get_quote_details(st.session_state.editing_quote_id)
        if details:
            st.session_state.selected_services = [
                {
                    "service_id": it["service_id"],
                    "name": it["service_name"],
                    "quantity": it["quantity"],
                    "unit_price": it["unit_price"],
                }
                for it in details["items"]
            ]
            st.session_state["_edit_client_id"] = details["quote"]["client_id"]
            st.session_state["_edit_discount_type"] = details["quote"]["discount_type"]
            st.session_state["_edit_discount_value"] = float(details["quote"]["discount_value"])
            st.session_state["_edit_notes"] = details["quote"].get("notes") or ""
            st.session_state["_edit_status"] = details["quote"]["status"]
            st.session_state["_loaded_edit_id"] = st.session_state.editing_quote_id
        else:
            st.error("Orçamento não encontrado.")
            navigate_to("list")

    # -- Header --
    h_left, h_right = st.columns([4, 1])
    with h_left:
        title = "✏️ Editando Orçamento" if is_editing else "➕ Novo Orçamento"
        st.subheader(title)
    with h_right:
        if st.button("← Voltar", use_container_width=True, key="form_back"):
            navigate_to("list")

    # -- Client selection --
    if clients_df.empty:
        st.warning("Cadastre pelo menos um cliente antes de criar orçamentos.")
        return

    client_options = {row["id"]: row["name"] for _, row in clients_df.iterrows()}
    client_ids = list(client_options.keys())
    default_client_idx = 0
    if is_editing:
        edit_cid = st.session_state.get("_edit_client_id")
        if edit_cid in client_ids:
            default_client_idx = client_ids.index(edit_cid)

    selected_client_id = st.selectbox(
        "Cliente *",
        options=client_ids,
        index=default_client_idx,
        format_func=lambda x: client_options[x],
    )

    # -- Add services --
    st.markdown("**Serviços**")
    if services_df.empty:
        st.warning("Cadastre pelo menos um serviço ativo.")
    else:
        if st.button("➕ Adicionar Serviço", use_container_width=True):
            add_service_dialog(services_df)

    # -- Display selected services --
    if st.session_state.selected_services:
        st.markdown("---")
        for idx, item in enumerate(st.session_state.selected_services):
            with st.container(border=True):
                st.markdown(f"**{item['name']}**")
                c1, c2, c3 = st.columns(3)
                new_qty = c1.number_input(
                    "Qtd",
                    min_value=1,
                    value=item["quantity"],
                    key=f"qty_{idx}",
                )
                if new_qty != item["quantity"]:
                    st.session_state.selected_services[idx]["quantity"] = int(new_qty)

                new_price = c2.number_input(
                    "Preço (R$)",
                    min_value=0.0,
                    value=item["unit_price"],
                    step=0.01,
                    format="%.2f",
                    key=f"price_{idx}",
                )
                if new_price != item["unit_price"]:
                    st.session_state.selected_services[idx]["unit_price"] = float(new_price)

                if c3.button("❌", key=f"rm_{idx}", use_container_width=True, help="Remover"):
                    st.session_state.selected_services.pop(idx)
                    st.rerun()

    # -- Discount --
    st.markdown("**Desconto**")
    discount_types = ["none", "percentage", "fixed"]
    default_disc_idx = 0
    if is_editing:
        edt = st.session_state.get("_edit_discount_type", "none")
        if edt in discount_types:
            default_disc_idx = discount_types.index(edt)
    discount_type = st.radio(
        "Tipo de desconto",
        discount_types,
        index=default_disc_idx,
        format_func=lambda x: {"none": "Sem desconto", "percentage": "Percentual (%)", "fixed": "Valor fixo (R$)"}[x],
        horizontal=True,
        label_visibility="collapsed",
    )
    discount_value = 0.0
    default_dv = float(st.session_state.get("_edit_discount_value", 0)) if is_editing else 0.0
    if discount_type == "percentage":
        discount_value = st.number_input("Desconto (%)", min_value=0.0, max_value=100.0, value=default_dv, step=1.0)
    elif discount_type == "fixed":
        discount_value = st.number_input("Desconto (R$)", min_value=0.0, value=default_dv, step=10.0)

    # -- Config --
    st.markdown("**Configurações**")
    valid_days = 30
    if not is_editing:
        valid_days = st.number_input("Validade (dias)", min_value=1, value=30)
    default_notes = st.session_state.get("_edit_notes", "") if is_editing else ""
    notes = st.text_area("Observações", value=default_notes, height=80)

    all_statuses = ["draft", "sent", "approved", "rejected"]
    if is_editing:
        default_status_idx = all_statuses.index(st.session_state.get("_edit_status", "draft"))
        form_status = st.selectbox("Status", all_statuses, index=default_status_idx, format_func=lambda x: STATUS_LABELS[x])
    else:
        form_status = st.selectbox("Status inicial", ["draft", "sent"], format_func=lambda x: STATUS_LABELS[x])

    # -- Preview totals --
    subtotal = sum(i["quantity"] * i["unit_price"] for i in st.session_state.selected_services)
    disc_amount = calculate_discount(subtotal, discount_type, discount_value)
    total = subtotal - disc_amount

    st.markdown("---")
    t1, t2 = st.columns(2)
    t1.write("Subtotal:")
    t2.write(f"**{format_currency(subtotal)}**")
    if disc_amount > 0:
        t1_d, t2_d = st.columns(2)
        t1_d.write("Desconto:")
        t2_d.write(f"**- {format_currency(disc_amount)}**")
    tot1, tot2 = st.columns(2)
    tot1.markdown("### TOTAL:")
    tot2.markdown(f"### {format_currency(total)}")

    # -- Action buttons --
    st.markdown("---")
    btn1, btn2, btn3 = st.columns(3)
    save_clicked = btn1.button(
        "💾 Salvar Alterações" if is_editing else "💾 Salvar",
        use_container_width=True,
    )
    pdf_clicked = btn2.button("📄 Salvar + PDF", use_container_width=True)
    if is_editing:
        if btn3.button("Cancelar Edição", use_container_width=True):
            navigate_to("list")
    else:
        if btn3.button("🔄 Limpar", use_container_width=True):
            st.session_state.selected_services = []
            st.rerun()

    if save_clicked or pdf_clicked:
        if clients_df.empty:
            st.error("Selecione um cliente.")
        elif not st.session_state.selected_services:
            st.error("Adicione pelo menos um serviço.")
        elif discount_type == "fixed" and discount_value > subtotal:
            st.error("Desconto não pode ser maior que o subtotal.")
        else:
            try:
                items_for_db = [
                    {"service_id": i["service_id"], "quantity": i["quantity"], "unit_price": i["unit_price"]}
                    for i in st.session_state.selected_services
                ]

                if is_editing:
                    update_quote(
                        quote_id=st.session_state.editing_quote_id,
                        client_id=selected_client_id,
                        items_list=items_for_db,
                        discount_type=discount_type,
                        discount_value=discount_value,
                        notes=notes,
                        status=form_status,
                    )
                    qid = st.session_state.editing_quote_id
                    log_info("Quote updated", quote_id=qid)
                else:
                    qid = create_quote(
                        client_id=selected_client_id,
                        items_list=items_for_db,
                        valid_days=valid_days,
                        discount_type=discount_type,
                        discount_value=discount_value,
                        notes=notes,
                        status=form_status,
                        created_by_user_id=current_user_id,
                    )
                    log_info("Quote created", quote_id=qid, client_id=selected_client_id)

                if pdf_clicked:
                    details = get_quote_details(qid)
                    with st.spinner("Gerando PDF..."):
                        gen = QuotePDFGenerator(details)
                        pdf_path = gen.generate()
                    msg = "Orçamento atualizado" if is_editing else "Orçamento criado"
                    st.success(f"{msg} e PDF gerado: {pdf_path.name}")
                    with open(pdf_path, "rb") as f:
                        st.download_button(
                            "⬇️ Baixar PDF",
                            data=f,
                            file_name=pdf_path.name,
                            mime="application/pdf",
                        )
                    if st.button("← Voltar para lista"):
                        navigate_to("list")
                else:
                    msg = "Orçamento atualizado com sucesso!" if is_editing else "Orçamento salvo com sucesso!"
                    st.success(msg)
                    navigate_to("list")
            except Exception as e:
                log_error("Failed to save quote", error=str(e))
                st.error(f"Erro ao salvar orçamento: {e}")


# ---------------------------------------------------------------------------
# VIEW: Detail
# ---------------------------------------------------------------------------

def render_detail_view() -> None:
    qid = st.session_state.viewing_quote_id
    if not qid:
        navigate_to("list")
        return

    details = get_quote_details(qid)
    if not details:
        st.error("Orçamento não encontrado.")
        if st.button("← Voltar"):
            navigate_to("list")
        return

    # -- Header --
    h1, h2, h3 = st.columns([4, 1, 1])
    with h1:
        st.subheader(f"Detalhes: {details['quote']['quote_number']}")
    with h2:
        if st.button("✏️ Editar", use_container_width=True, key="detail_edit"):
            navigate_to("form", quote_id=qid)
    with h3:
        if st.button("← Fechar", use_container_width=True, key="detail_close"):
            navigate_to("list")

    # -- Client info --
    c = details["client"]
    st.markdown(f"**Cliente:** {c['name']}  |  {c['email']}  |  {c.get('phone') or '—'}")
    if c.get("company"):
        st.markdown(f"**Empresa:** {c['company']}")
    st.markdown(
        f"**Emissão:** {format_date(details['quote']['issue_date'])}  |  "
        f"**Validade:** {format_date(details['quote']['valid_until'])}  |  "
        f"**Status:** {STATUS_LABELS.get(details['quote']['status'], details['quote']['status'])}"
    )

    # -- Items --
    st.markdown("**Itens:**")
    for item in details["items"]:
        line_total = item["quantity"] * item["unit_price"]
        st.markdown(
            f"- {item['service_name']} — {item['quantity']}x {format_currency(item['unit_price'])} = **{format_currency(line_total)}**"
        )

    # -- Totals --
    st.markdown("---")
    t = details["totals"]
    st.write(f"**Subtotal:** {format_currency(t['subtotal'])}")
    if t["discount"] > 0:
        st.write(f"**Desconto:** - {format_currency(t['discount'])}")
    st.markdown(f"### Total: {format_currency(t['total'])}")

    if details["quote"].get("notes"):
        st.markdown(f"**Observações:** {details['quote']['notes']}")

    # -- PDF download --
    with st.spinner("Gerando PDF..."):
        gen = QuotePDFGenerator(details)
        pdf_path = gen.generate()

    col_pdf, col_email = st.columns(2)
    with col_pdf:
        with open(pdf_path, "rb") as f:
            st.download_button(
                "⬇️ Baixar PDF",
                data=f,
                file_name=pdf_path.name,
                mime="application/pdf",
                key="dl_pdf_detail",
                use_container_width=True,
            )
    with col_email:
        if st.button("📧 Enviar por Email", use_container_width=True, key="email_detail"):
            token = ensure_quote_token(qid)
            log_debug("Email button clicked", quote_id=qid, token=token[:8] + "...")
            success, message = send_quote_email(
                to_email=details["client"]["email"],
                quote_data=details,
                view_token=token,
                attach_pdf=True,
                pdf_path=pdf_path,
            )
            if success:
                if details["quote"]["status"] == "draft":
                    update_quote_status(qid, "sent")
                st.success(message)
            else:
                st.error(message)


# ---------------------------------------------------------------------------
# View dispatcher
# ---------------------------------------------------------------------------

view = st.session_state.page_view

if view == "form":
    render_form_view(clients_df, services_df)
elif view == "detail":
    render_detail_view()
else:
    render_list_view(clients_df)
