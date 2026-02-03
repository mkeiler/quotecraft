"""PDF generation for QuoteCraft quotes using ReportLab."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from utils.helpers import format_currency, format_date

NAVY = colors.HexColor("#2E5266")
ACCENT = colors.HexColor("#73A580")
LIGHT_BG = colors.HexColor("#F0F4F7")

PDFS_DIR = Path(__file__).parent.parent / "pdfs"


class QuotePDFGenerator:
    """Generate a PDF document for a quote.

    *quote_data* must contain keys: quote, client, items, totals
    (as returned by ``get_quote_details``).
    """

    def __init__(self, quote_data: dict[str, Any]) -> None:
        self.data = quote_data
        self.styles = getSampleStyleSheet()
        self._register_styles()

    # ------------------------------------------------------------------
    # Custom paragraph styles
    # ------------------------------------------------------------------

    def _register_styles(self) -> None:
        self.styles.add(ParagraphStyle(
            "DocTitle",
            parent=self.styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            textColor=colors.white,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            "QuoteNumber",
            parent=self.styles["Normal"],
            fontName="Helvetica",
            fontSize=11,
            textColor=colors.white,
            alignment=TA_CENTER,
        ))
        self.styles.add(ParagraphStyle(
            "SectionTitle",
            parent=self.styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            textColor=NAVY,
            spaceAfter=6,
        ))
        self.styles.add(ParagraphStyle(
            "RightAligned",
            parent=self.styles["Normal"],
            alignment=TA_RIGHT,
        ))
        self.styles.add(ParagraphStyle(
            "SmallGray",
            parent=self.styles["Normal"],
            fontSize=8,
            textColor=colors.gray,
            alignment=TA_CENTER,
        ))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, output_path: str | Path | None = None) -> Path:
        """Build the PDF and return the file path."""
        PDFS_DIR.mkdir(exist_ok=True)

        if output_path is None:
            filename = f"{self.data['quote']['quote_number']}.pdf"
            output_path = PDFS_DIR / filename

        output_path = Path(output_path)
        doc = SimpleDocTemplate(
            str(output_path),
            pagesize=A4,
            leftMargin=2 * cm,
            rightMargin=2 * cm,
            topMargin=2 * cm,
            bottomMargin=2 * cm,
        )

        elements: list = []
        elements += self._build_header()
        elements.append(Spacer(1, 0.6 * cm))
        elements += self._build_client_section()
        elements.append(Spacer(1, 0.4 * cm))
        elements += self._build_items_table()
        elements.append(Spacer(1, 0.4 * cm))
        elements += self._build_totals()
        elements += self._build_notes()
        elements.append(Spacer(1, 1 * cm))
        elements += self._build_footer()

        doc.build(elements)
        return output_path

    # ------------------------------------------------------------------
    # Section builders
    # ------------------------------------------------------------------

    def _build_header(self) -> list:
        q = self.data["quote"]
        header_data = [[
            Paragraph("ORÇAMENTO", self.styles["DocTitle"]),
        ], [
            Paragraph(q["quote_number"], self.styles["QuoteNumber"]),
        ], [
            Paragraph(
                f"Emissão: {format_date(q['issue_date'])}    |    "
                f"Validade: {format_date(q['valid_until'])}",
                self.styles["QuoteNumber"],
            ),
        ]]
        t = Table(header_data, colWidths=[17 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), NAVY),
            ("TOPPADDING", (0, 0), (0, 0), 14),
            ("BOTTOMPADDING", (0, -1), (0, -1), 14),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        return [t]

    def _build_client_section(self) -> list:
        c = self.data["client"]
        elements = [Paragraph("CLIENTE", self.styles["SectionTitle"])]
        lines = [f"<b>{c['name']}</b>"]
        if c.get("company"):
            lines.append(c["company"])
        lines.append(c["email"])
        if c.get("phone"):
            lines.append(c["phone"])
        if c.get("address"):
            lines.append(c["address"])
        elements.append(Paragraph("<br/>".join(lines), self.styles["Normal"]))
        return elements

    def _build_items_table(self) -> list:
        elements = [Paragraph("SERVIÇOS", self.styles["SectionTitle"])]
        header = ["Serviço", "Descrição", "Qtd", "Preço Unit.", "Total"]
        rows = [header]
        for item in self.data["items"]:
            desc = (item.get("service_description") or "—")[:80]
            line_total = item["quantity"] * item["unit_price"]
            rows.append([
                item["service_name"],
                desc,
                str(item["quantity"]),
                format_currency(item["unit_price"]),
                format_currency(line_total),
            ])

        col_widths = [4.5 * cm, 5 * cm, 1.5 * cm, 3 * cm, 3 * cm]
        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), NAVY),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 10),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 8),
            ("TOPPADDING", (0, 0), (-1, 0), 8),
            # Body rows
            ("FONTSIZE", (0, 1), (-1, -1), 9),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            # Alternating row background
            *[
                ("BACKGROUND", (0, i), (-1, i), LIGHT_BG)
                for i in range(2, len(rows), 2)
            ],
            # Alignment
            ("ALIGN", (2, 0), (2, -1), "CENTER"),
            ("ALIGN", (3, 0), (4, -1), "RIGHT"),
            # Grid
            ("LINEBELOW", (0, 0), (-1, 0), 1, NAVY),
            ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey),
        ]))
        elements.append(t)
        return elements

    def _build_totals(self) -> list:
        totals = self.data["totals"]
        rows = [
            ["Subtotal:", format_currency(totals["subtotal"])],
        ]
        if totals["discount"] > 0:
            q = self.data["quote"]
            if q["discount_type"] == "percentage":
                label = f"Desconto ({q['discount_value']:.0f}%):"
            else:
                label = "Desconto:"
            rows.append([label, f"- {format_currency(totals['discount'])}"])
        rows.append(["TOTAL:", format_currency(totals["total"])])

        t = Table(rows, colWidths=[13 * cm, 4 * cm])
        style_cmds = [
            ("ALIGN", (0, 0), (0, -1), "RIGHT"),
            ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            # Total row bold & larger
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("FONTSIZE", (0, -1), (-1, -1), 13),
            ("TEXTCOLOR", (0, -1), (-1, -1), NAVY),
            ("LINEABOVE", (0, -1), (-1, -1), 1, NAVY),
        ]
        t.setStyle(TableStyle(style_cmds))
        return [t]

    def _build_notes(self) -> list:
        notes = self.data["quote"].get("notes")
        if not notes:
            return []
        return [
            Spacer(1, 0.4 * cm),
            Paragraph("OBSERVAÇÕES", self.styles["SectionTitle"]),
            Paragraph(notes, self.styles["Normal"]),
        ]

    def _build_footer(self) -> list:
        q = self.data["quote"]
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        return [
            Paragraph(
                f"Orçamento válido até {format_date(q['valid_until'])}",
                self.styles["SmallGray"],
            ),
            Paragraph(f"Gerado em {now}", self.styles["SmallGray"]),
        ]
