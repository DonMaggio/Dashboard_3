import re
from datetime import datetime
from pathlib import Path

from fpdf import FPDF


def _s(text):
    if text is None:
        return ""
    if isinstance(text, str):
        text = text.replace("\u2014", "-").replace("\u2013", "-")
        text = text.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u00f1", "n").replace("\u00d1", "N")
        return re.sub(r"[^\x00-\xFF]", "", text)
    return str(text)

OUTPUT_DIR = Path(__file__).parent / "reportes"
LOGO_PATH = Path(__file__).parent / "Logo-5IA.png"

C_PRIMARY = (44, 46, 123)
C_ACCENT = (239, 138, 35)
C_BG = (247, 248, 250)
C_WHITE = (255, 255, 255)
C_DARK = (30, 34, 51)
C_MUTED = (90, 95, 118)
C_LIGHT_BG = (244, 245, 250)
C_BORDER = (232, 233, 242)
C_GRAY = (154, 157, 176)
C_MARKET_BG = (255, 249, 242)


class ReportePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        pass

    def _section_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*C_PRIMARY)
        self.cell(0, 8, title.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.4)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)


def _draw_header(pdf, periodo):
    pdf.set_fill_color(*C_PRIMARY)
    pdf.rect(0, 0, 210, 38, "F")

    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=12, y=6, h=26)

    pdf.set_y(8)
    pdf.set_font("Helvetica", "B", 18)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(0, 9, _s("Reporte Mensual de Propiedad"), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(*C_ACCENT)
    pdf.cell(0, 6, _s(f"Periodo {periodo}"), align="R", new_x="LMARGIN", new_y="NEXT")


def _draw_property_bar(pdf, cliente):
    pdf.set_fill_color(*C_LIGHT_BG)
    pdf.rect(pdf.l_margin, pdf.get_y(), 190, 20, "F")

    y_start = pdf.get_y() + 2
    cols = [
        ("Dirección", cliente.get("direccion", "")),
        ("Barrio / Localidad", f'{cliente.get("barrio", "")}, {cliente.get("localidad", "")}'),
        ("Ficha", f'#{cliente.get("ficha", "")}'),
        ("Estado", cliente.get("estado", "")),
    ]

    w_col = 190 / len(cols) - 2
    x_start = pdf.l_margin + 2

    for i, (label, valor) in enumerate(cols):
        x = x_start + i * (w_col + 2)
        pdf.set_xy(x, y_start)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(w_col, 4, _s(label.upper()))

        pdf.set_xy(x, y_start + 5)
        pdf.set_font("Helvetica", "B", 10)
        if i == 3:
            sv = _s(valor)
            ancho_estado = pdf.get_string_width(sv) + 8
            pdf.set_fill_color(*C_ACCENT)
            pdf.set_text_color(*C_WHITE)
            pdf.cell(ancho_estado, 7, sv, fill=True, align="C")
            pdf.set_text_color(*C_DARK)
        else:
            pdf.set_text_color(*C_PRIMARY)
            pdf.cell(w_col, 7, _s(valor))

    pdf.set_y(y_start + 14)
    pdf.set_draw_color(*C_ACCENT)
    pdf.set_line_width(0.8)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(2)


def _draw_kpi_row(pdf, consultas, visitas_count, estado):
    y0 = pdf.get_y()
    card_w = 58
    card_h = 28
    gap = 8

    for i, (numero, label) in enumerate([
        (str(consultas), "Consultas virtuales"),
        (str(visitas_count), "Visitas presenciales"),
        (_s(estado), "Estado de la propiedad"),
    ]):
        x = pdf.l_margin + i * (card_w + gap)
        pdf.set_fill_color(*C_LIGHT_BG)
        pdf.rect(x, y0, card_w, card_h, "F")
        pdf.set_draw_color(*C_ACCENT)
        pdf.set_line_width(1.2)
        pdf.line(x, y0, x, y0 + card_h)

        pdf.set_xy(x + 5, y0 + 4)
        pdf.set_font("Helvetica", "B", 20)
        pdf.set_text_color(*C_PRIMARY)
        pdf.cell(card_w - 10, 10, _s(numero))

        pdf.set_xy(x + 5, y0 + 16)
        pdf.set_font("Helvetica", "", 7)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(card_w - 10, 8, _s(label.upper()))

    pdf.set_y(y0 + card_h + 6)


def _draw_visitas_table(pdf, visitas):
    col_w = [30, 50, 100]
    headers = ["Fecha", "Interesado", "Comentario"]

    pdf.set_fill_color(*C_PRIMARY)
    pdf.set_text_color(*C_WHITE)
    pdf.set_font("Helvetica", "B", 8)
    x0 = pdf.l_margin
    for i, h in enumerate(headers):
        pdf.set_xy(x0 + sum(col_w[:i]), pdf.get_y())
        pdf.cell(col_w[i], 8, _s(h), fill=True, align="C")
    pdf.ln(8)

    pdf.set_text_color(*C_DARK)
    if not visitas:
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*C_GRAY)
        pdf.cell(sum(col_w), 10, _s("No se registraron visitas presenciales en este periodo."), align="C")
        pdf.ln(10)
        pdf.set_text_color(*C_DARK)
    else:
        for idx, v in enumerate(visitas):
            if idx % 2 == 0:
                pdf.set_fill_color(250, 250, 252)
            else:
                pdf.set_fill_color(*C_WHITE)
            pdf.set_font("Helvetica", "", 8)
            for i, key in enumerate(["fecha", "nombre", "comentario"]):
                pdf.set_xy(x0 + sum(col_w[:i]), pdf.get_y())
                pdf.cell(col_w[i], 7, _s(str(v.get(key, ""))), fill=True, align="C" if i < 2 else "L")
            pdf.ln(7)


def _draw_mercado(pdf, resumen):
    col_w = 91
    gap = 8
    y0 = pdf.get_y()

    for i, (titulo, texto) in enumerate([
        ("Oferta y demanda de lotes", (resumen or {}).get("oferta_demanda", "")),
        ("Costo de construccion", (resumen or {}).get("costo_construccion", "")),
    ]):
        x = pdf.l_margin + i * (col_w + gap)
        pdf.set_fill_color(*C_MARKET_BG)
        pdf.set_draw_color(243, 223, 196)
        pdf.rect(x, y0, col_w, 45, "DF")

        pdf.set_xy(x + 4, y0 + 3)
        pdf.set_font("Helvetica", "B", 8)
        pdf.set_text_color(*C_ACCENT)
        pdf.cell(col_w - 8, 5, _s(titulo.upper()))

        pdf.set_xy(x + 4, y0 + 10)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(58, 61, 80)
        pdf.multi_cell(col_w - 8, 4, _s(texto or "Sin datos."))

    pdf.set_y(y0 + 45 + 4)

    ctx = (resumen or {}).get("contexto_general", "")
    pdf.set_fill_color(*C_LIGHT_BG)
    pdf.rect(pdf.l_margin, pdf.get_y(), 190, max(20, len(ctx) // 3 + 10), "F")
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*C_PRIMARY)
    pdf.set_xy(pdf.l_margin + 4, pdf.get_y() + 3)
    pdf.cell(180, 5, "CONTEXTO GENERAL DEL MERCADO")
    pdf.set_xy(pdf.l_margin + 4, pdf.get_y() + 10)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(58, 61, 80)
    pdf.multi_cell(182, 4, _s(ctx or "Sin datos."))
    pdf.ln(4)


def _draw_footer(pdf):
    pdf.set_y(-20)
    pdf.set_draw_color(*C_BORDER)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, pdf.get_y(), pdf.w - pdf.r_margin, pdf.get_y())
    pdf.ln(3)
    pdf.set_font("Helvetica", "", 7)
    pdf.set_text_color(*C_GRAY)
    pdf.cell(95, 4, f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}', align="L")
    pdf.set_font("Helvetica", "B", 7)
    pdf.set_text_color(*C_PRIMARY)
    pdf.cell(95, 4, "5IA \u00b7 Reportes Inteligentes", align="R")


def generar_reporte(cliente, resumen, visitas, periodo=None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf = ReportePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=25)
    pdf.add_page()
    pdf.set_margins(10, 10, 10)

    periodo_str = periodo or ""
    _draw_header(pdf, periodo_str)
    pdf.ln(4)
    _draw_property_bar(pdf, cliente)

    pdf.ln(6)
    pdf._section_title("Resumen de actividad del mes")
    _draw_kpi_row(pdf, cliente.get("consultas", 0), len(visitas), cliente.get("estado", ""))

    pdf._section_title("Detalle de visitas presenciales")
    _draw_visitas_table(pdf, visitas)

    pdf._section_title(f"Contexto de mercado - {periodo_str}")
    _draw_mercado(pdf, resumen)

    _draw_footer(pdf)

    ficha = cliente.get("ficha", "unknown")
    p_str = periodo_str or "unknown"
    path = OUTPUT_DIR / f"reporte_{ficha}_{p_str}.pdf"
    pdf.output(str(path))
    return path
