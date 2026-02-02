"""QuoteCraft - Homepage."""

import streamlit as st

from database.models import init_database, get_connection


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


def get_stats() -> dict[str, int]:
    """Fetch summary statistics from the database."""
    conn = get_connection()
    try:
        clients = conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
        services = conn.execute(
            "SELECT COUNT(*) FROM services WHERE is_active = 1"
        ).fetchone()[0]
        return {"clients": clients, "services": services, "quotes": 0}
    finally:
        conn.close()


def main() -> None:
    st.set_page_config(
        page_title="QuoteCraft",
        page_icon="\U0001f4cb",
        layout="wide",
    )

    init_database()
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

    st.divider()

    st.markdown("### Acesso Rápido")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("👥  Gerenciar Clientes", use_container_width=True):
            st.switch_page("pages/1_👥_Clientes.py")
    with c2:
        if st.button("🛠️  Gerenciar Serviços", use_container_width=True):
            st.switch_page("pages/2_🛠️_Servicos.py")


if __name__ == "__main__":
    main()
