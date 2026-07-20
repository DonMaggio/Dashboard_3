from datetime import datetime
from pathlib import Path

from jinja2 import Template

TEMPLATE_PATH = Path(__file__).parent / "template-reporte-cliente.html"
OUTPUT_DIR = Path(__file__).parent / "reportes"


def generar_reporte(cliente, resumen, visitas, periodo=None):
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
    path = OUTPUT_DIR / f"reporte_{ficha}_{periodo_str}.html"

    path.write_text(html, encoding="utf-8")
    return path


def generar_reporte_bytes(cliente, resumen, visitas, periodo=None):
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = Template(f.read())

    return template.render(
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
    ).encode("utf-8")
