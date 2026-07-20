import tempfile
from datetime import datetime
from pathlib import Path

from jinja2 import Template

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

    tmp_html = tempfile.NamedTemporaryFile(suffix=".html", delete=False, mode="w", encoding="utf-8")
    tmp_html.write(html)
    tmp_html.close()

    ficha = cliente.get("ficha", "unknown")
    periodo_str = periodo or "unknown"
    pdf_path = OUTPUT_DIR / f"reporte_{ficha}_{periodo_str}.pdf"

    _html_to_pdf(tmp_html.name, str(pdf_path))

    Path(tmp_html.name).unlink(missing_ok=True)

    return pdf_path


def _html_to_pdf(html_path, pdf_path):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"file://{html_path}", wait_until="networkidle")
        page.pdf(path=pdf_path, format="A4", print_background=True)
        browser.close()
