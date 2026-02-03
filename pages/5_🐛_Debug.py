"""QuoteCraft - Debug Panel (Admin Only)."""

from __future__ import annotations

import json
from datetime import datetime

import streamlit as st

from database.models import init_database, get_connection
from services.auth import require_auth, render_logout_button
from utils.debug import (
    is_debug_mode,
    get_session_state_summary,
    get_database_stats,
    read_recent_logs,
    clear_logs,
    log_info,
    LOG_FILE,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------

st.set_page_config(page_title="Debug - QuoteCraft", page_icon="🐛", layout="wide")
init_database()

# Authentication check
if not require_auth():
    st.stop()

render_logout_button()

# Check debug mode
if not is_debug_mode():
    st.warning("Modo debug desativado. Ative em secrets.toml: `[app] debug = true`")

st.title("🐛 Painel de Debug")

log_info("Debug panel accessed")

# ---------------------------------------------------------------------------
# Tabs
# ---------------------------------------------------------------------------

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📊 Visao Geral",
    "🗄️ Session State",
    "💾 Banco de Dados",
    "📜 Logs",
    "🔧 Ferramentas"
])

# ---------------------------------------------------------------------------
# Tab 1: Overview
# ---------------------------------------------------------------------------

with tab1:
    st.subheader("Status do Sistema")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Debug Mode", "ON" if is_debug_mode() else "OFF")

    with col2:
        db_stats = get_database_stats()
        total_records = sum(v for v in db_stats.values() if v > 0)
        st.metric("Total de Registros", total_records)

    with col3:
        st.metric("Hora do Servidor", datetime.now().strftime("%H:%M:%S"))

    st.markdown("---")

    st.subheader("Estatisticas do Banco")
    for table, count in db_stats.items():
        st.write(f"- **{table}**: {count} registros")

    st.markdown("---")

    st.subheader("Configuracao")
    try:
        config_info = {
            "app.base_url": st.secrets.get("app", {}).get("base_url", "N/A"),
            "app.debug": st.secrets.get("app", {}).get("debug", False),
            "app.token_expiry_days": st.secrets.get("app", {}).get("token_expiry_days", 30),
            "smtp.server": st.secrets.get("smtp", {}).get("server", "N/A"),
            "smtp.port": st.secrets.get("smtp", {}).get("port", "N/A"),
            "smtp.email": st.secrets.get("smtp", {}).get("email", "N/A")[:20] + "...",
            "auth.username": st.secrets.get("auth", {}).get("username", "N/A"),
        }
        for key, value in config_info.items():
            st.write(f"- **{key}**: `{value}`")
    except Exception as e:
        st.error(f"Erro ao ler configuracao: {e}")

# ---------------------------------------------------------------------------
# Tab 2: Session State
# ---------------------------------------------------------------------------

with tab2:
    st.subheader("Session State Atual")

    if st.button("🔄 Atualizar", key="refresh_session"):
        st.rerun()

    session_summary = get_session_state_summary()

    if not session_summary:
        st.info("Session state vazio.")
    else:
        # Display as expandable JSON
        st.json(session_summary)

        st.markdown("---")

        st.subheader("Detalhes Completos")
        for key, value in st.session_state.items():
            with st.expander(f"`{key}` ({type(value).__name__})"):
                if isinstance(value, (dict, list)):
                    st.json(value)
                else:
                    st.write(value)

    st.markdown("---")

    st.subheader("Limpar Session State")
    st.warning("Isso vai deslogar voce e limpar todos os dados temporarios.")
    if st.button("🗑️ Limpar Tudo", key="clear_session"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.success("Session state limpo!")
        st.rerun()

# ---------------------------------------------------------------------------
# Tab 3: Database
# ---------------------------------------------------------------------------

with tab3:
    st.subheader("Explorador do Banco de Dados")

    table = st.selectbox(
        "Selecione a tabela",
        ["clients", "services", "quotes", "quote_items"]
    )

    limit = st.slider("Limite de registros", 10, 100, 25)

    if st.button("🔍 Consultar", key="query_db"):
        conn = get_connection()
        try:
            query = f"SELECT * FROM {table} ORDER BY id DESC LIMIT {limit}"
            import pandas as pd
            df = pd.read_sql_query(query, conn)
            st.dataframe(df, use_container_width=True)
            st.caption(f"{len(df)} registros exibidos")
        except Exception as e:
            st.error(f"Erro na consulta: {e}")
        finally:
            conn.close()

    st.markdown("---")

    st.subheader("Consulta SQL Personalizada")
    st.warning("Use com cuidado! Apenas consultas SELECT sao permitidas.")

    custom_query = st.text_area(
        "Query SQL",
        value="SELECT * FROM quotes WHERE status = 'draft' LIMIT 10",
        height=100
    )

    if st.button("▶️ Executar", key="run_custom_query"):
        if not custom_query.strip().upper().startswith("SELECT"):
            st.error("Apenas consultas SELECT sao permitidas.")
        else:
            conn = get_connection()
            try:
                import pandas as pd
                df = pd.read_sql_query(custom_query, conn)
                st.dataframe(df, use_container_width=True)
                st.caption(f"{len(df)} registros retornados")
            except Exception as e:
                st.error(f"Erro: {e}")
            finally:
                conn.close()

# ---------------------------------------------------------------------------
# Tab 4: Logs
# ---------------------------------------------------------------------------

with tab4:
    st.subheader("Logs do Sistema")

    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        log_lines = st.slider("Linhas para exibir", 20, 500, 100)

    with col2:
        if st.button("🔄 Atualizar Logs", key="refresh_logs"):
            st.rerun()

    with col3:
        if st.button("🗑️ Limpar Logs", key="clear_logs"):
            if clear_logs():
                st.success("Logs limpos!")
            else:
                st.error("Erro ao limpar logs.")

    st.caption(f"Arquivo: `{LOG_FILE}`")

    logs = read_recent_logs(log_lines)

    # Filter options
    log_filter = st.text_input("Filtrar logs (texto)", key="log_filter")

    if log_filter:
        logs = [line for line in logs if log_filter.lower() in line.lower()]

    # Display logs
    log_text = "".join(logs)
    st.code(log_text, language="log")

# ---------------------------------------------------------------------------
# Tab 5: Tools
# ---------------------------------------------------------------------------

with tab5:
    st.subheader("Ferramentas de Debug")

    # Test Email
    st.markdown("### 📧 Testar Envio de Email")
    test_email = st.text_input("Email de teste", key="test_email")

    if st.button("Enviar Email de Teste", key="send_test_email"):
        if test_email:
            from services.email_service import get_smtp_config, send_quote_email

            config = get_smtp_config()
            st.write("**Configuracao SMTP:**")
            st.json({
                "server": config["server"],
                "port": config["port"],
                "email": config["email"][:20] + "...",
                "password": "***" if config["password"] else "NOT SET"
            })

            # Simple test without full quote data
            st.info("Para teste completo, envie um orcamento real pela pagina de Orcamentos.")
        else:
            st.warning("Informe um email de teste.")

    st.markdown("---")

    # Test Token
    st.markdown("### 🔑 Testar Token")
    test_token = st.text_input("Token para validar", key="test_token")

    if st.button("Validar Token", key="validate_token"):
        if test_token:
            from services.token_service import get_quote_by_token
            quote_id = get_quote_by_token(test_token)
            if quote_id:
                st.success(f"Token valido! Quote ID: {quote_id}")
            else:
                st.error("Token invalido ou expirado.")
        else:
            st.warning("Informe um token.")

    st.markdown("---")

    # Generate Password Hash
    st.markdown("### 🔐 Gerar Hash de Senha")
    new_password = st.text_input("Nova senha", type="password", key="new_password")

    if st.button("Gerar Hash", key="generate_hash"):
        if new_password:
            from services.auth import hash_password
            password_hash = hash_password(new_password)
            st.code(password_hash, language="text")
            st.caption("Copie este hash para secrets.toml em `[auth] password_hash`")
        else:
            st.warning("Informe uma senha.")

    st.markdown("---")

    # Environment Info
    st.markdown("### 🖥️ Informacoes do Ambiente")
    import sys
    import platform

    env_info = {
        "Python Version": sys.version,
        "Platform": platform.platform(),
        "Streamlit Version": st.__version__,
    }

    for key, value in env_info.items():
        st.write(f"- **{key}**: `{value}`")
