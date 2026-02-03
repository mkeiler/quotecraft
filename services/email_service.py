"""Email service for sending quotes via Gmail SMTP."""

from __future__ import annotations

import os
import smtplib
import ssl
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Any, Optional

import streamlit as st

from utils.debug import log_debug, log_info, log_error, log_exception
from utils.helpers import format_currency, format_date


def get_smtp_config() -> dict[str, Any]:
    """Retrieve SMTP configuration from secrets or environment."""
    try:
        config = {
            "server": st.secrets["smtp"]["server"],
            "port": int(st.secrets["smtp"]["port"]),
            "email": st.secrets["smtp"]["email"],
            "password": st.secrets["smtp"]["app_password"],
        }
        log_debug("SMTP config loaded from secrets", server=config["server"], port=config["port"])
        return config
    except (KeyError, FileNotFoundError):
        log_debug("SMTP config not found in secrets, using environment")
        return {
            "server": os.getenv("SMTP_SERVER", "smtp.gmail.com"),
            "port": int(os.getenv("SMTP_PORT", "587")),
            "email": os.getenv("SMTP_EMAIL", ""),
            "password": os.getenv("SMTP_APP_PASSWORD", ""),
        }


def get_base_url() -> str:
    """Get the application base URL for generating links."""
    try:
        return st.secrets["app"]["base_url"]
    except (KeyError, FileNotFoundError):
        return os.getenv("APP_BASE_URL", "http://localhost:8501")


def build_quote_email_html(
    quote_data: dict[str, Any],
    view_link: str,
) -> str:
    """Build professional HTML email template for quote."""
    quote = quote_data["quote"]
    client = quote_data["client"]
    totals = quote_data["totals"]
    items = quote_data["items"]

    # Build items table rows
    items_html = ""
    for item in items:
        line_total = item["quantity"] * item["unit_price"]
        items_html += f"""
        <tr>
            <td style="padding: 8px; border-bottom: 1px solid #eee;">{item['service_name']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: center;">{item['quantity']}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{format_currency(item['unit_price'])}</td>
            <td style="padding: 8px; border-bottom: 1px solid #eee; text-align: right;">{format_currency(line_total)}</td>
        </tr>
        """

    discount_row = ""
    if totals["discount"] > 0:
        discount_row = f"""
        <tr>
            <td colspan="3" style="padding: 8px; text-align: right;"><strong>Desconto:</strong></td>
            <td style="padding: 8px; text-align: right; color: #73A580;">- {format_currency(totals['discount'])}</td>
        </tr>
        """

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #2E5266; color: white; padding: 20px; text-align: center; border-radius: 8px 8px 0 0; }}
            .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; }}
            .footer {{ background-color: #2E5266; color: white; padding: 15px; text-align: center; border-radius: 0 0 8px 8px; font-size: 12px; }}
            .btn {{ display: inline-block; background-color: #73A580; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; }}
            .btn:hover {{ background-color: #5E8A6A; }}
            table {{ width: 100%; border-collapse: collapse; margin: 15px 0; }}
            th {{ background-color: #2E5266; color: white; padding: 10px; text-align: left; }}
            .total-row {{ font-size: 18px; font-weight: bold; color: #2E5266; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="color: white; margin: 0;">Orcamento</h1>
                <p style="margin: 5px 0 0 0; color: white;">{quote['quote_number']}</p>
            </div>
            <div class="content">
                <p>Prezado(a) <strong>{client['name']}</strong>,</p>
                <p>Segue o orcamento solicitado:</p>

                <table>
                    <tr>
                        <td><strong>Numero:</strong></td>
                        <td>{quote['quote_number']}</td>
                    </tr>
                    <tr>
                        <td><strong>Data de Emissao:</strong></td>
                        <td>{format_date(quote['issue_date'])}</td>
                    </tr>
                    <tr>
                        <td><strong>Valido ate:</strong></td>
                        <td>{format_date(quote['valid_until'])}</td>
                    </tr>
                </table>

                <h3 style="color: #2E5266;">Itens do Orcamento</h3>
                <table>
                    <thead>
                        <tr>
                            <th>Servico</th>
                            <th style="text-align: center;">Qtd</th>
                            <th style="text-align: right;">Preco Unit.</th>
                            <th style="text-align: right;">Total</th>
                        </tr>
                    </thead>
                    <tbody>
                        {items_html}
                    </tbody>
                    <tfoot>
                        <tr>
                            <td colspan="3" style="padding: 8px; text-align: right;"><strong>Subtotal:</strong></td>
                            <td style="padding: 8px; text-align: right;">{format_currency(totals['subtotal'])}</td>
                        </tr>
                        {discount_row}
                        <tr class="total-row">
                            <td colspan="3" style="padding: 12px 8px; text-align: right; border-top: 2px solid #2E5266;"><strong>TOTAL:</strong></td>
                            <td style="padding: 12px 8px; text-align: right; border-top: 2px solid #2E5266;"><strong>{format_currency(totals['total'])}</strong></td>
                        </tr>
                    </tfoot>
                </table>

                <div style="text-align: center; margin: 25px 0;">
                    <a href="{view_link}" class="btn">Ver Orcamento Completo</a>
                </div>

                <p style="font-size: 12px; color: #666;">
                    Este orcamento e valido ate {format_date(quote['valid_until'])}.
                    Clique no botao acima para visualizar os detalhes completos.
                </p>
            </div>
            <div class="footer">
                <p style="color: white; margin: 0;">QuoteCraft - Sistema de Orcamentos</p>
            </div>
        </div>
    </body>
    </html>
    """
    return html


def send_quote_email(
    to_email: str,
    quote_data: dict[str, Any],
    view_token: str,
    attach_pdf: bool = False,
    pdf_path: Optional[Path] = None,
) -> tuple[bool, str]:
    """Send quote email to client.

    Returns (success: bool, message: str).
    """
    config = get_smtp_config()

    if not config["email"] or not config["password"]:
        return False, "Configuracao SMTP nao encontrada. Verifique secrets.toml."

    base_url = get_base_url()
    view_link = f"{base_url}/Visualizar_Orcamento?token={view_token}"

    # Create message
    msg = MIMEMultipart("mixed")
    msg["Subject"] = f"Orcamento {quote_data['quote']['quote_number']}"
    msg["From"] = config["email"]
    msg["To"] = to_email

    # HTML content
    html_content = build_quote_email_html(quote_data, view_link)
    html_part = MIMEText(html_content, "html", "utf-8")
    msg.attach(html_part)

    # Attach PDF if requested
    if attach_pdf and pdf_path and pdf_path.exists():
        with open(pdf_path, "rb") as f:
            pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
            pdf_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=pdf_path.name,
            )
            msg.attach(pdf_attachment)

    try:
        log_info("Sending quote email", to=to_email, quote=quote_data["quote"]["quote_number"])
        context = ssl.create_default_context()
        with smtplib.SMTP(config["server"], config["port"]) as server:
            if config["port"] == 1025:
                server.login(config["email"], config["password"])
                server.sendmail(config["email"], to_email, msg.as_string())
            else:
                server.starttls(context=context)
                server.login(config["email"], config["password"])
                server.sendmail(config["email"], to_email, msg.as_string())
        log_info("Email sent successfully", to=to_email)
        return True, "Email enviado com sucesso!"
    except smtplib.SMTPAuthenticationError:
        log_error("SMTP authentication failed", server=config["server"])
        return False, "Erro de autenticacao SMTP. Verifique email e senha do aplicativo."
    except smtplib.SMTPException as e:
        log_error("SMTP error", error=str(e))
        return False, f"Erro ao enviar email: {str(e)}"
    except Exception as e:
        log_exception("Unexpected error sending email")
        return False, f"Erro inesperado: {str(e)}"
