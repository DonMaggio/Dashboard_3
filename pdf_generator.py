import io
import math
import os
import re
import tempfile
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

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


def _letter_spacing(text):
    return " ".join(text)


def _multi_cell_height(pdf, text, w, lh):
    if not text:
        return lh
    lines = text.replace("\r", "").split("\n")
    total = 0
    for line in lines:
        total += max(1, math.ceil(pdf.get_string_width(line) / max(w, 1)))
    return max(total, 1) * lh


OUTPUT_DIR = Path(__file__).parent / "reportes"
LOGO_PATH = Path(__file__).parent / "Logo-5IA-blanco.png"

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
C_MARKET_BORDER = (243, 223, 196)


class ReportePDF(FPDF):
    def header(self):
        pass

    def footer(self):
        pass

    def _section_title(self, title):
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*C_PRIMARY)
        self.cell(0, 8, _letter_spacing(title.upper()), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*C_BORDER)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(5)


def _draw_header(pdf, periodo):
    pdf.set_fill_color(*C_PRIMARY)
    pdf.rect(0, 0, 210, 35, "F")

    if LOGO_PATH.exists():
        pdf.image(str(LOGO_PATH), x=14, y=4, h=12)

    pdf.set_y(6)
    pdf.set_font("Helvetica", "B", 20)
    pdf.set_text_color(*C_WHITE)
    pdf.cell(0, 9, _s("Reporte Mensual de Propiedad"), align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(*C_ACCENT)
    pdf.cell(0, 6, _s(f"PERIODO {periodo}"), align="R", new_x="LMARGIN", new_y="NEXT")


def _draw_property_bar(pdf, cliente):
    y_bar = pdf.get_y()
    pdf.set_fill_color(*C_LIGHT_BG)
    pdf.rect(0, y_bar, 210, 24, "F")

    cols = [
        ("Direccion", cliente.get("direccion", "")),
        ("Barrio / Localidad", f'{cliente.get("barrio", "")}, {cliente.get("localidad", "")}'),
        ("Ficha", f'#{cliente.get("ficha", "")}'),
        ("Estado", cliente.get("estado", "")),
    ]

    usable = pdf.w - pdf.l_margin - pdf.r_margin
    w_col = usable / len(cols) - 3
    x_start = pdf.l_margin + 3

    for i, (label, valor) in enumerate(cols):
        x = x_start + i * (w_col + 3)
        pdf.set_xy(x, y_bar + 4)
        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(w_col, 4, _s(label.upper()))

        pdf.set_xy(x, y_bar + 10)
        pdf.set_font("Helvetica", "B", 12)
        if i == 3:
            sv = _s(valor)
            ancho = pdf.get_string_width(sv) + 10
            cx = x + (w_col - ancho) / 2
            pdf.set_fill_color(*C_ACCENT)
            pdf.set_text_color(*C_WHITE)
            pdf.cell(ancho, 8, sv, fill=True, align="C")
            pdf.set_text_color(*C_DARK)
        else:
            pdf.set_text_color(*C_PRIMARY)
            pdf.cell(w_col, 8, _s(valor))

    pdf.set_y(y_bar + 24)
    pdf.set_draw_color(*C_ACCENT)
    pdf.set_line_width(1)
    pdf.line(0, pdf.get_y(), 210, pdf.get_y())
    pdf.ln(2)


def _draw_kpi_row(pdf, consultas, visitas_count, estado):
    y0 = pdf.get_y()
    card_w = 58
    card_h = 25
    gap = 4

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

        pdf.set_xy(x + 6, y0 + 4)
        pdf.set_font("Helvetica", "B", 22)
        pdf.set_text_color(*C_PRIMARY)
        pdf.cell(card_w - 12, 11, _s(numero))

        pdf.set_xy(x + 6, y0 + 17)
        pdf.set_font("Helvetica", "", 7.5)
        pdf.set_text_color(*C_MUTED)
        pdf.cell(card_w - 12, 6, _s(label.upper()))

    pdf.set_y(y0 + card_h + 5)


def _draw_visitas_table(pdf, visitas):
    col_w = [28, 48, 106]
    headers = ["Fecha", "Interesado", "Comentario"]

    pdf.set_fill_color(*C_PRIMARY)
    pdf.set_text_color(*C_WHITE)
    pdf.set_font("Helvetica", "B", 9)
    x0 = pdf.l_margin
    for i, h in enumerate(headers):
        pdf.set_xy(x0 + sum(col_w[:i]), pdf.get_y())
        pdf.cell(col_w[i], 10, _s(h), fill=True, align="L")
    pdf.ln(10)

    pdf.set_text_color(*C_DARK)
    if not visitas:
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(*C_GRAY)
        pdf.set_xy(x0, pdf.get_y())
        pdf.cell(sum(col_w), 12, _s("No se registraron visitas presenciales en este periodo."), align="C")
        pdf.ln(12)
        pdf.set_text_color(*C_DARK)
    else:
        for idx, v in enumerate(visitas):
            if idx % 2 == 0:
                pdf.set_fill_color(250, 250, 252)
            else:
                pdf.set_fill_color(*C_WHITE)
            pdf.set_font("Helvetica", "", 9)
            for i, key in enumerate(["fecha", "nombre", "comentario"]):
                pdf.set_xy(x0 + sum(col_w[:i]), pdf.get_y())
                pdf.cell(col_w[i], 9, _s(str(v.get(key, ""))), fill=True, align="L")
            pdf.ln(9)
    pdf.ln(3)


def _draw_mercado(pdf, resumen):
    col_w = 89
    gap = 4
    y0 = pdf.get_y()

    pdf.set_font("Helvetica", "", 9)
    text_h = []
    for _, texto in [
        ("Oferta y demanda de lotes", (resumen or {}).get("oferta_demanda", "")),
        ("Costo de construccion", (resumen or {}).get("costo_construccion", "")),
    ]:
        text_h.append(_multi_cell_height(pdf, _s(texto or "Sin datos."), col_w - 10, 4.5))
    card_h = min(max(40, 12 + max(text_h) + 6), pdf.h - y0 - 50)

    for i, (titulo, texto) in enumerate([
        ("Oferta y demanda de lotes", (resumen or {}).get("oferta_demanda", "")),
        ("Costo de construccion", (resumen or {}).get("costo_construccion", "")),
    ]):
        x = pdf.l_margin + i * (col_w + gap)
        pdf.set_fill_color(*C_MARKET_BG)
        pdf.set_draw_color(*C_MARKET_BORDER)
        pdf.rect(x, y0, col_w, card_h, "DF")

        pdf.set_xy(x + 5, y0 + 4)
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(*C_ACCENT)
        pdf.cell(col_w - 10, 5, _s(titulo.upper()))

        pdf.set_xy(x + 5, y0 + 12)
        pdf.set_font("Helvetica", "", 9)
        pdf.set_text_color(58, 61, 80)
        pdf.multi_cell(col_w - 10, 4.5, _s(texto or "Sin datos."))

    pdf.set_y(y0 + card_h + 5)

    ctx = _s((resumen or {}).get("contexto_general", "") or "Sin datos.")
    y_ctx = pdf.get_y()
    if y_ctx > pdf.h - 55:
        pdf.add_page()
        y_ctx = pdf.get_y()
    pdf.set_font("Helvetica", "", 9)
    text_h = _multi_cell_height(pdf, ctx, 172, 4.5)
    max_h = pdf.h - y_ctx - 28
    h_ctx = min(12 + text_h + 8, max_h)
    pdf.set_fill_color(*C_LIGHT_BG)
    pdf.rect(pdf.l_margin, y_ctx, 182, h_ctx, "F")
    pdf.set_font("Helvetica", "B", 9)
    pdf.set_text_color(*C_PRIMARY)
    pdf.set_xy(pdf.l_margin + 5, y_ctx + 4)
    pdf.cell(170, 5, _s("CONTEXTO GENERAL DEL MERCADO"))
    pdf.set_xy(pdf.l_margin + 5, y_ctx + 12)
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(58, 61, 80)
    pdf.multi_cell(172, 4.5, ctx)
    if pdf.get_y() < y_ctx + h_ctx + 4:
        pdf.set_y(y_ctx + h_ctx + 4)


def _draw_footer(pdf):
    y = pdf.h - 22
    pdf.set_draw_color(*C_BORDER)
    pdf.set_line_width(0.4)
    pdf.line(pdf.l_margin, y, pdf.w - pdf.r_margin, y)
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*C_GRAY)
    pdf.text(pdf.l_margin, y + 5, f'Generado el {datetime.now().strftime("%d/%m/%Y %H:%M")}')
    pdf.set_font("Helvetica", "B", 8)
    pdf.set_text_color(*C_PRIMARY)
    pdf.text(pdf.w - pdf.r_margin - pdf.get_string_width(_s("5IA · Reportes Inteligentes")), y + 5, _s("5IA · Reportes Inteligentes"))
    pdf.set_y(y + 6)


def _make_chart_image(chart_type, data, **kwargs):
    fig, ax = plt.subplots(figsize=(3.2, 1.6), dpi=130)
    fig.patch.set_facecolor("#F4F5FA")
    ax.set_facecolor("#F4F5FA")

    if chart_type == "bar":
        labels = list(data.keys())
        values = list(data.values())
        colors = ["#2C2E7B"] * len(labels)
        if kwargs.get("highlight"):
            colors[-1] = "#EF8A23"
        bars = ax.barh(labels, values, color=colors, height=0.6, edgecolor="white", linewidth=0.5)
        for b, v in zip(bars, values):
            ax.text(v + max(values) * 0.01, b.get_y() + b.get_height() / 2,
                    f"{v:.0f}", va="center", fontsize=6, color="#2C2E7B", fontweight="bold")
        ax.set_xlim(0, max(values) * 1.25)
        ax.xaxis.set_visible(False)
        ax.yaxis.set_ticks([])
        for i, label in enumerate(labels):
            ax.text(-max(values) * 0.02, i, label, ha="right", va="center", fontsize=5.5, color="#5B5F76")

    elif chart_type == "comparison":
        labels = list(data.keys())
        values = list(data.values())
        colors = [kwargs.get("color_self", "#EF8A23") if i == 0 else "#2C2E7B" for i in range(len(labels))]
        bars = ax.bar(labels, values, color=colors, width=0.5, edgecolor="white", linewidth=0.5)
        for b, v in zip(bars, values):
            ax.text(b.get_x() + b.get_width() / 2, b.get_height() + max(values) * 0.02,
                    f"{v:.1f}" if v != int(v) else f"{v:.0f}", ha="center", va="bottom",
                    fontsize=7, color="#2C2E7B", fontweight="bold")
        ax.set_ylim(0, max(values) * 1.3)
        ax.yaxis.set_visible(False)
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, fontsize=6.5, color="#5B5F76")
        for spine in ax.spines.values():
            spine.set_visible(False)
        ax.tick_params(axis="x", length=0)

    elif chart_type == "pie":
        wedges, texts, autotexts = ax.pie(
            list(data.values()), labels=list(data.keys()), autopct="%1.0f%%",
            startangle=90, colors=["#2C2E7B", "#EF8A23", "#5B5F76", "#9A9DB0", "#C4C6D4"],
            textprops={"fontsize": 5.5, "color": "#1E2233"},
            pctdistance=0.75,
        )
        for t in autotexts:
            t.set_fontsize(5.5)
            t.set_color("#FFFFFF")
            t.set_fontweight("bold")

    for spine in ax.spines.values():
        spine.set_visible(False)
    plt.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.05)

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=130, bbox_inches="tight", pad_inches=0.1,
                facecolor=fig.get_facecolor(), edgecolor="none")
    plt.close(fig)
    buf.seek(0)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
    tmp.write(buf.read())
    tmp.close()
    return tmp.name


def _draw_comparativa(pdf, cliente, barrio_data):
    pdf._section_title("Analisis comparativo")
    consultas_prop = cliente.get("consultas", 0)
    consultas_prom = barrio_data.get("consultas_promedio", 0)
    valor_str = cliente.get("valor")
    import excel_parser as _ep
    valor_prop = _ep.valor_to_float(valor_str) if valor_str else None
    valor_prom = barrio_data.get("valor_promedio")

    texto = f"Esta propiedad recibio {consultas_prop} consultas. "
    if consultas_prom > 0:
        diff = consultas_prop - consultas_prom
        signo = "+" if diff >= 0 else ""
        texto += f"El promedio en {_s(cliente.get('barrio', 'el barrio'))} es de {consultas_prom:.0f} ({signo}{diff:.0f} vs el promedio). "
    else:
        texto += "No hay datos comparativos del barrio. "

    if valor_prop and valor_prom:
        diff_v = valor_prop - valor_prom
        signo_v = "+" if diff_v >= 0 else ""
        texto += f"Valor: U$D {valor_prop:,.0f} (promedio del barrio: U$D {valor_prom:,.0f}, {signo_v}U$D {abs(diff_v):,.0f})."

    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(58, 61, 80)
    pdf.multi_cell(182, 4.5, _s(texto))
    pdf.ln(3)

    if consultas_prom > 0:
        chart_path = _make_chart_image("comparison", {
            "Esta propiedad": consultas_prop,
            f"Prom. {_s(cliente.get('barrio', 'barrio'))}": consultas_prom,
        })
        if chart_path:
            pdf.image(chart_path, x=pdf.l_margin + 30, w=120)
            pdf.ln(2)
            os.unlink(chart_path)


def _draw_canales_chart(pdf, canales):
    if not canales:
        return
    pdf._section_title("Canales principales")
    top = sorted(canales, key=lambda c: c["total"], reverse=True)[:5]
    data = {_s(c["canal"][:18]): c["total"] for c in top}
    chart_path = _make_chart_image("bar", data, highlight=False)
    pdf.image(chart_path, x=pdf.l_margin + 30, w=120)
    pdf.ln(2)
    os.unlink(chart_path)

    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(*C_MUTED)
    total = sum(c["total"] for c in canales)
    for c in top[:3]:
        pct = c["total"] / total * 100 if total > 0 else 0
        pdf.cell(0, 4, _s(f"  {c['canal'][:22]}: {c['total']} ({pct:.0f}%)"))
        pdf.ln(4)


def generar_reporte(cliente, resumen, visitas, periodo=None, canales=None, barrio_data=None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    pdf = ReportePDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=28)
    pdf.add_page()
    pdf.set_margins(14, 10, 14)

    periodo_str = periodo or ""
    _draw_header(pdf, periodo_str)
    pdf.ln(4)
    _draw_property_bar(pdf, cliente)

    pdf.ln(6)
    pdf._section_title("Resumen de actividad del mes")
    _draw_kpi_row(pdf, cliente.get("consultas", 0), len(visitas), cliente.get("estado", ""))

    pdf._section_title("Detalle de visitas presenciales")
    _draw_visitas_table(pdf, visitas)

    if barrio_data:
        _draw_comparativa(pdf, cliente, barrio_data)

    if canales:
        _draw_canales_chart(pdf, canales)

    pdf._section_title(f"Contexto de mercado - {periodo_str}")
    _draw_mercado(pdf, resumen)

    _draw_footer(pdf)

    ficha = cliente.get("ficha", "unknown")
    p_str = periodo_str or "unknown"
    path = OUTPUT_DIR / f"reporte_{ficha}_{p_str}.pdf"
    pdf.output(str(path))
    return path
