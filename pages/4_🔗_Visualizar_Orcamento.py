"""QuoteCraft - Visualizacao Publica de Orcamento (sem login)."""

from __future__ import annotations

import streamlit as st

from database.models import init_database
from database.operations import get_quote_details
from services.token_service import get_quote_by_token
from utils.helpers import format_currency, format_date

# ---------------------------------------------------------------------------
# Page config - NO authentication required (public page)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="Visualizar Orcamento - QuoteCraft",
    page_icon="🔗",
    layout="centered",
)
init_database()

# Custom CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1,h2,h3,h4,h5,h6 { font-family: 'Space Grotesk', sans-serif; color: #2E5266; }
    .quote-header { background-color: #2E5266; color: white; padding: 20px; border-radius: 8px; text-align: center; margin-bottom: 20px; }
    .quote-section { background-color: #f9f9f9; padding: 15px; border-radius: 8px; margin: 10px 0; }
    .total-box { background-color: #2E5266; color: white; padding: 15px; border-radius: 8px; text-align: center; margin-top: 15px; }
    .item-card { background-color: white; padding: 15px; border-radius: 8px; margin: 8px 0; border: 1px solid #e0e0e0; }
    </style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Get token from query params
# ---------------------------------------------------------------------------

token = st.query_params.get("token", "")

if not token:
    st.error("Link invalido. Nenhum token fornecido.")
    st.info("Se voce recebeu um orcamento por email, clique no link enviado.")
    st.stop()

# ---------------------------------------------------------------------------
# Validate token and get quote
# ---------------------------------------------------------------------------

quote_id = get_quote_by_token(token)

if not quote_id:
    st.error("Orcamento nao encontrado ou link expirado.")
    st.info("Entre em contato conosco para solicitar um novo link.")
    st.stop()

details = get_quote_details(quote_id)

if not details:
    st.error("Erro ao carregar orcamento.")
    st.stop()

# ---------------------------------------------------------------------------
# Render Quote View
# ---------------------------------------------------------------------------

quote = details["quote"]
client = details["client"]
items = details["items"]
totals = details["totals"]

STATUS_LABELS = {
    "draft": "Rascunho",
    "sent": "Enviado",
    "approved": "Aprovado",
    "rejected": "Rejeitado",
}

# Header
st.markdown(f"""
<div class="quote-header">
    <h1 style="color: white; margin: 0;">ORCAMENTO</h1>
    <h2 style="color: white; margin: 5px 0;">{quote['quote_number']}</h2>
    <p style="margin: 0; color: #ccc;">Emissao: {format_date(quote['issue_date'])} | Validade: {format_date(quote['valid_until'])}</p>
</div>
""", unsafe_allow_html=True)

# Client Info
st.subheader("Dados do Cliente")

client_info = f"**{client['name']}**"
if client.get("company"):
    client_info += f"\n\n{client['company']}"
client_info += f"\n\n{client['email']}"
if client.get("phone"):
    client_info += f"\n\n{client['phone']}"
if client.get("address"):
    client_info += f"\n\n{client['address']}"

with st.container(border=True):
    st.markdown(client_info)

# Items
st.subheader("Servicos")

for item in items:
    line_total = item["quantity"] * item["unit_price"]
    with st.container(border=True):
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**{item['service_name']}**")
            if item.get("service_description"):
                st.caption(item["service_description"])
        with col2:
            st.markdown(f"{item['quantity']}x {format_currency(item['unit_price'])}")
            st.markdown(f"**{format_currency(line_total)}**")

st.markdown("---")

# Totals
col1, col2 = st.columns(2)
with col1:
    st.markdown("**Subtotal:**")
    if totals["discount"] > 0:
        st.markdown("**Desconto:**")
with col2:
    st.markdown(f"{format_currency(totals['subtotal'])}")
    if totals["discount"] > 0:
        st.markdown(f"- {format_currency(totals['discount'])}")

st.markdown(f"""
<div class="total-box">
    <h2 style="color: white; margin: 0;">TOTAL: {format_currency(totals['total'])}</h2>
</div>
""", unsafe_allow_html=True)

# Notes
if quote.get("notes"):
    st.markdown("---")
    st.subheader("Observacoes")
    st.info(quote["notes"])

# Status and validity info
st.markdown("---")
status_label = STATUS_LABELS.get(quote["status"], quote["status"])
st.caption(f"Status do orcamento: **{status_label}**")
st.caption(f"Este orcamento e valido ate {format_date(quote['valid_until'])}.")
