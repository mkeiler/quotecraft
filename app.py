"""QuoteCraft - Homepage."""

import streamlit as st

from database.models import init_database, get_connection
from services.auth import require_auth, render_logout_button


def apply_custom_css() -> None:
    """Inject custom fonts and styling."""
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Space+Grotesk:wght@500;600;700&display=swap');

        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: 'Space Grotesk', sans-serif;
            color: #2E5266;
        }

        .stButton > button {
            background-color: #73A580;
            color: white;
            border-radius: 8px;
            padding: 0.5rem 1.5rem;
            font-weight: 500;
            border: none;
        }

        .stButton > button:hover {
            background-color: #5E8A6A;
        }

        [data-testid="stMetricValue"] {
            color: #2E5266;
            font-family: 'Space Grotesk', sans-serif;
        }
        </style>
    """, unsafe_allow_html=True)


def get_stats() -> dict:
    """Fetch summary statistics from the database."""
    conn = get_connection()
    try:
        clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        services = conn.execute(
            "SELECT COUNT(*) FROM services WHERE is_active = 1"
        ).fetchone()[0]
        quotes = conn.execute("SELECT COUNT(*) FROM quotes").fetchone()[0]
        approved_total = conn.execute("""
            SELECT COALESCE(SUM(qi.quantity * qi.unit_price), 0)
            FROM quotes q
            JOIN quote_items qi ON qi.quote_id = q.id
            WHERE q.status = 'approved'
        """).fetchone()[0]
        conversion = (
            conn.execute("SELECT COUNT(*) FROM quotes WHERE status = 'approved'").fetchone()[0]
            / quotes * 100
            if quotes > 0 else 0
        )
        return {
            "clients": clients,
            "services": services,
            "quotes": quotes,
            "approved_total": approved_total,
            "conversion": conversion,
        }
    finally:
        conn.close()


def main() -> None:
    st.set_page_config(
        page_title="QuoteCraft",
        page_icon="\U0001f4cb",
        layout="wide",
    )

    init_database()

    # Authentication check
    if not require_auth():
        st.stop()

    render_logout_button()
    apply_custom_css()

    st.markdown(
        "<h1 style='text-align:center;'>QuoteCraft</h1>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<p style='text-align:center;color:#555;'>"
        "Sistema de gerenciamento de orçamentos — simples, rápido e funcional."
        "</p>",
        unsafe_allow_html=True,
    )

    st.divider()

    stats = get_stats()

    col1, col2, col3 = st.columns(3)
    col1.metric("Clientes", stats["clients"])
    col2.metric("Serviços Ativos", stats["services"])
    col3.metric("Orçamentos", stats["quotes"])

    col4, col5 = st.columns(2)
    col4.metric("Aprovados (R$)", f"R$ {stats['approved_total']:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
    col5.metric("Taxa de Conversão", f"{stats['conversion']:.1f}%")

    st.divider()

    st.markdown("### Acesso Rápido")
    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("👥  Gerenciar Clientes", use_container_width=True):
            st.switch_page("pages/1_👥_Clientes.py")
    with c2:
        if st.button("🛠️  Gerenciar Serviços", use_container_width=True):
            st.switch_page("pages/2_🛠️_Servicos.py")
    with c3:
        if st.button("📄  Gerenciar Orçamentos", use_container_width=True):
            st.switch_page("pages/3_📄_Orcamentos.py")


if __name__ == "__main__":
    main()
