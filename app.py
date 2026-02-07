"""QuoteCraft - Homepage."""

import streamlit as st

from database.models import init_database, get_connection
from services.auth import require_auth, render_logout_button, hide_admin_pages_css


def apply_custom_css() -> None:
    """Inject custom fonts and styling with mobile responsiveness."""
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

        /* Hero section */
        .hero-section {
            background: linear-gradient(135deg, #2E5266 0%, #4A7C59 100%);
            padding: 2rem;
            border-radius: 16px;
            color: white;
            text-align: center;
            margin-bottom: 1.5rem;
        }
        .hero-section h1 {
            color: white !important;
            margin-bottom: 0.5rem;
        }
        .hero-section p {
            color: rgba(255,255,255,0.9);
            margin: 0;
        }

        /* Metric cards */
        .metric-card {
            background: white;
            padding: 1.25rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.06);
            border: 1px solid #e8e8e8;
        }

        /* Prevent columns from stacking on mobile */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 0.5rem;
        }
        [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
            flex: 1 1 0 !important;
            min-width: 0 !important;
        }

        /* Mobile adjustments */
        @media (max-width: 640px) {
            .stButton > button {
                padding: 0.4rem 0.5rem;
                font-size: 0.85rem;
            }
            [data-testid="stMetricValue"] {
                font-size: 1.1rem !important;
            }
            [data-testid="stMetricLabel"] {
                font-size: 0.75rem !important;
            }
            .hero-section {
                padding: 1.25rem;
                border-radius: 12px;
            }
            .hero-section h1 {
                font-size: 1.5rem !important;
            }
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
    hide_admin_pages_css()
    apply_custom_css()

    # Hero section
    st.markdown("""
        <div class="hero-section">
            <h1>📋 QuoteCraft</h1>
            <p>Sistema de gerenciamento de orçamentos — simples, rápido e funcional.</p>
        </div>
    """, unsafe_allow_html=True)

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
