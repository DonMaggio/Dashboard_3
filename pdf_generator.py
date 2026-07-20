from datetime import datetime
from pathlib import Path

from jinja2 import Template
from xhtml2pdf import pisa

TEMPLATE_PATH = Path(__file__).parent / "template-reporte-cliente.html"
OUTPUT_DIR = Path(__file__).parent / "reportes"


def generar_pdf_cliente(cliente, resumen, visitas, periodo=None):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = Template(f.read())

    html = template.render(
        periodo=periodo or "",
        direccion=cliente.get("direccion", ""),
        barrio=cliente.get("barrio", ""),
        localidad=cliente.get("localidad", ""),
        ficha=cliente.get("ficha", ""),
        estado=cliente.get("estado", ""),
        consultas_virtuales=cliente.get("consultas", 0),
        cantidad_visitas_presenciales=len(visitas),
        visitas_presenciales=visitas,
        oferta_demanda=(resumen or {}).get("oferta_demanda", ""),
        costo_construccion=(resumen or {}).get("costo_construccion", ""),
        contexto_general=(resumen or {}).get("contexto_general", ""),
        fecha_generacion=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )

    ficha = cliente.get("ficha", "unknown")
    periodo_str = periodo or "unknown"
    pdf_path = OUTPUT_DIR / f"reporte_{ficha}_{periodo_str}.pdf"

    with open(pdf_path, "wb") as f:
        result = pisa.CreatePDF(html, dest=f)

    if result.err:
        raise RuntimeError(f"Error generando PDF: {result.err}")

    return pdf_path


def generar_pdf_bytes(cliente, resumen, visitas, periodo=None):
    """Genera PDF y devuelve los bytes (para almacenar en DB o descargar)."""
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = Template(f.read())

    html = template.render(
        periodo=periodo or "",
        direccion=cliente.get("direccion", ""),
        barrio=cliente.get("barrio", ""),
        localidad=cliente.get("localidad", ""),
        ficha=cliente.get("ficha", ""),
        estado=cliente.get("estado", ""),
        consultas_virtuales=cliente.get("consultas", 0),
        cantidad_visitas_presenciales=len(visitas),
        visitas_presenciales=visitas,
        oferta_demanda=(resumen or {}).get("oferta_demanda", ""),
        costo_construccion=(resumen or {}).get("costo_construccion", ""),
        contexto_general=(resumen or {}).get("contexto_general", ""),
        fecha_generacion=datetime.now().strftime("%d/%m/%Y %H:%M"),
    )

    pdf_data = pisa.CreatePDF(html)
    if pdf_data.err:
        raise RuntimeError(f"Error generando PDF: {pdf_data.err}")
    return pdf_data.dest.getvalue()
