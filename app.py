from datetime import date, datetime
from pathlib import Path

import pandas as pd
import streamlit as st

import db
from excel_parser import parse_xintel_excel, parse_complementary
from pdf_generator import generar_reporte

st.set_page_config(page_title="Panel Inmobiliario", page_icon=":material/analytics:", layout="wide")
db.init_db()

PRIMARY = "#2C2E7B"
ACCENT = "#EF8A23"

st.markdown(f"""
<style>
    :root {{
        --primary: {PRIMARY};
        --accent: {ACCENT};
    }}
    .stApp {{ background-color: #F7F8FA; }}
    h1, h2, h3 {{ color: var(--primary); }}
    .stButton>button[kind="primary"] {{ background-color: var(--accent); border-color: var(--accent); }}
    div[data-testid="stSidebar"] > div:first-child {{ background-color: #FFFFFF; }}

    @media (prefers-color-scheme: dark) {{
        .stApp {{ background-color: #0E1117 !important; }}
        h1, h2, h3 {{ color: #A0A5D0 !important; }}
        div[data-testid="stSidebar"] > div:first-child {{ background-color: #151820 !important; }}
        section[data-testid="stSidebar"] * {{ color: #E0E2E8 !important; }}
        p, .stMarkdown, .stCaption, .st-bw, .st-c0, .st-dl {{ color: #D0D3DD !important; }}
        div[data-testid="stMetric"] > div, div[data-testid="stMetric"] label {{ color: #E0E2E8 !important; }}
        div[data-testid="stMetric"] {{ background-color: #1A1D24; border: 1px solid #2C2F3A; border-radius: 8px; padding: 8px 12px; }}
        div.st-bb, div[data-testid="stDataFrame"], div[data-testid="stExpander"],
        div[class*="stAlert"], div[data-testid="stVerticalBlockBorder"] > div {{
            background-color: #1A1D24 !important; border-color: #2C2F3A !important;
        }}
        .st-bb {{ border-color: #2C2F3A !important; }}
        .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div,
        div[data-testid="stMultiSelect"] > div {{
            background-color: #22262F !important; color: #E0E2E8 !important; border-color: #3A3E4A !important;
        }}
        div[role="radiogroup"] label {{ color: #E0E2E8 !important; }}
        button[kind="secondary"] {{ background-color: #22262F !important; color: #D0D3DD !important; border-color: #3A3E4A !important; }}
        div.stAlert p {{ color: #D0D3DD !important; }}
    }}
</style>
""", unsafe_allow_html=True)


def periodo_actual() -> str:
    hoy = date.today()
    return f"{hoy.year}-{hoy.month:02d}"


if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:
    st.logo("Logo-5IA.png")
    col1, col2, col3 = st.columns([1.5, 2, 1.5])
    with col2:
        st.title("Panel Inmobiliario")
        st.image("Logo-5IA.png", width=200)
        user = st.text_input("Usuario", placeholder="consultora", label_visibility="collapsed")
        password = st.text_input("Contraseña", type="password", placeholder="consultora", label_visibility="collapsed")
        if st.button("Ingresar", type="primary", use_container_width=True):
            if user == "consultora" and password == "consultora":
                st.session_state.logged_in = True
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos")
    st.stop()

st.logo("Logo-5IA.png")

with st.sidebar:
    with st.container():
        c1, c2 = st.columns([3, 1])
        with c1:
            st.caption("Reportes mensuales por cliente")
        with c2:
            if st.button(":material/logout:", help="Cerrar sesión", key="logout_btn"):
                st.session_state.logged_in = False
                st.rerun()
    seccion = st.radio(
        "Navegación",
        [":material/explore: Explorar y filtrar", ":material/upload: Cargar Excel Xintel",
         ":material/trending_up: Resumen de mercado", ":material/description: Generar reporte",
         ":material/history: Historial"],
        label_visibility="collapsed",
    )

# ---------------------------------------------------------------------------
# 1) EXPLORAR Y FILTRAR
# ---------------------------------------------------------------------------
if seccion == ":material/explore: Explorar y filtrar":
    st.title("Explorar y filtrar propiedades")

    periodos = db.get_periodos_disponibles()
    if not periodos:
        st.info("Todavía no cargaste ningún Excel de Xintel.", icon=":material/info:")
    else:
        col1, col2 = st.columns([1, 3])
        with col1:
            periodo_sel = st.selectbox("Período", periodos, index=0)

        clientes = db.get_clientes(periodo_sel)
        df = pd.DataFrame(clientes)

        with st.container(border=True):
            st.markdown("**Filtros**")
            c1, c2, c3, c4, c5 = st.columns(5)
            with c1:
                barrios = sorted([b for b in df["barrio"].dropna().unique() if b]) if not df.empty else []
                f_barrio = st.multiselect("Barrio", barrios, label_visibility="collapsed", placeholder="Barrio")
            with c2:
                localidades = sorted([l for l in df["localidad"].dropna().unique() if l]) if not df.empty else []
                f_localidad = st.multiselect("Localidad", localidades, label_visibility="collapsed", placeholder="Localidad")
            with c3:
                estados = sorted([e for e in df["estado"].dropna().unique() if e]) if not df.empty else []
                f_estado = st.multiselect("Estado", estados, label_visibility="collapsed", placeholder="Estado")
            with c4:
                tipos = sorted([t for t in df["tipo"].dropna().unique() if t]) if not df.empty else []
                f_tipo = st.multiselect("Tipo", tipos, label_visibility="collapsed", placeholder="Tipo")
            with c5:
                min_c, max_c = (int(df["consultas"].min()), int(df["consultas"].max())) if not df.empty else (0, 0)
                f_consultas = st.slider("Consultas mínimas", min_c, max(max_c, min_c), min_c, label_visibility="collapsed")
            texto = st.text_input("Buscar por ficha o dirección", label_visibility="collapsed", placeholder="Buscar por ficha o dirección")

        if not df.empty:
            filtrado = df.copy()
            if f_barrio:
                filtrado = filtrado[filtrado["barrio"].isin(f_barrio)]
            if f_localidad:
                filtrado = filtrado[filtrado["localidad"].isin(f_localidad)]
            if f_estado:
                filtrado = filtrado[filtrado["estado"].isin(f_estado)]
            if f_tipo:
                filtrado = filtrado[filtrado["tipo"].isin(f_tipo)]
            filtrado = filtrado[filtrado["consultas"] >= f_consultas]
            if texto:
                t = texto.lower()
                filtrado = filtrado[
                    filtrado["ficha"].str.lower().str.contains(t)
                    | filtrado["direccion"].str.lower().str.contains(t, na=False)
                ]

            with st.container(horizontal=True):
                st.metric("Fichas (filtro actual)", len(filtrado))
                st.metric("Consultas totales", int(filtrado["consultas"].sum()))
                st.metric("Vendidas", int((filtrado["estado"].str.upper() == "VENDIDAS").sum()))
                st.metric("Activas", int((filtrado["estado"].str.upper() == "ACTIVO").sum()))

            with st.container(border=True):
                st.dataframe(
                    filtrado[["ficha", "direccion", "barrio", "localidad", "tipo", "estado", "consultas", "operacion", "valor", "moneda"]],
                    hide_index=True,
                )

            st.subheader("Consultas por barrio")
            if not filtrado.empty:
                por_barrio = filtrado.groupby("barrio")["consultas"].sum().sort_values(ascending=False).head(15)
                st.bar_chart(por_barrio)

            st.divider()
            st.header("Analytics del período", text_alignment="center")

            canales = db.get_canales(periodo_sel)
            operaciones = db.get_operaciones(periodo_sel)
            tareas = db.get_tareas(periodo_sel)
            tiempo = db.get_tiempo_respuesta(periodo_sel)

            c_col1, c_col2 = st.columns(2)
            with c_col1:
                with st.container(border=True):
                    st.subheader("Consultas por canal")
                    if canales and filtrado is not None:
                        df_canales = pd.DataFrame(canales)
                        filtro_canal = st.multiselect(
                            "Filtrar canales", df_canales["canal"].tolist(),
                            default=df_canales["canal"].tolist(),
                            label_visibility="collapsed", placeholder="Canales",
                            key="filtro_canal"
                        )
                        df_canal_filt = df_canales[df_canales["canal"].isin(filtro_canal)]
                        if not df_canal_filt.empty:
                            st.bar_chart(df_canal_filt.set_index("canal")["total"])
                            with st.expander("Ver detalle"):
                                st.dataframe(df_canal_filt, hide_index=True)
                    else:
                        st.caption("Sin datos de canales.")

            with c_col2:
                with st.container(border=True):
                    st.subheader("Consultas por operación")
                    if operaciones:
                        df_ops = pd.DataFrame(operaciones)
                        st.bar_chart(df_ops.set_index("operacion")["total"])
                        with st.expander("Ver detalle"):
                            st.dataframe(df_ops, hide_index=True)
                    else:
                        st.caption("Sin datos de operaciones.")

            t_col1, t_col2 = st.columns(2)
            with t_col1:
                with st.container(border=True):
                    st.subheader("Tiempo promedio de respuesta")
                    if tiempo:
                        df_tiempo = pd.DataFrame(tiempo)
                        df_tiempo = df_tiempo[df_tiempo["operador"] != "PROMEDIO GENERAL"]
                        if not df_tiempo.empty:
                            st.bar_chart(df_tiempo.set_index("operador")["tiempo_promedio"])
                        prom = next((t for t in tiempo if t["operador"] == "PROMEDIO GENERAL"), None)
                        if prom:
                            st.metric("Promedio general", f'{prom["tiempo_promedio"]:.0f} h',
                                      help=f'{int(prom["tareas_respondidas"])} tareas respondidas')
                        with st.expander("Ver detalle"):
                            st.dataframe(pd.DataFrame(tiempo), hide_index=True)
                    else:
                        st.caption("Sin datos de tiempo de respuesta.")

            with t_col2:
                with st.container(border=True):
                    st.subheader("Tareas del período")
                    if tareas:
                        df_tareas = pd.DataFrame(tareas)
                        st.bar_chart(df_tareas.set_index("motivo")["cantidad"])
                        with st.expander("Ver detalle"):
                            st.dataframe(df_tareas, hide_index=True)
                    else:
                        st.caption("Sin datos de tareas.")
        else:
            st.warning("No hay datos para ese período.")

# ---------------------------------------------------------------------------
# 2) CARGAR EXCEL XINTEL
# ---------------------------------------------------------------------------
elif seccion == ":material/upload: Cargar Excel Xintel":
    st.title("Cargar Excel mensual de Xintel")
    st.caption("Subí el archivo .xlsx exportado desde Xintel para extraer las fichas y sus métricas.")

    with st.container(border=True):
        periodo = st.text_input("Período (YYYY-MM)", value=periodo_actual())
        archivo = st.file_uploader("Archivo .xlsx", type=["xlsx"], label_visibility="collapsed")

        if archivo and st.button("Procesar archivo", type="primary"):
            with st.spinner("Procesando..."):
                try:
                    registros = parse_xintel_excel(archivo, periodo)
                    db.upsert_clientes(registros)
                    comp = parse_complementary(archivo, periodo)
                    db.save_complementaria(periodo, comp)
                    st.success(f"Archivo procesado — {len(registros)} fichas detectadas para el período {periodo}.", icon=":material/check_circle:")
                    st.dataframe(pd.DataFrame(registros).head(20), hide_index=True)
                except Exception as e:
                    st.error(f"No se pudo procesar el archivo: {e}", icon=":material/error:")

# ---------------------------------------------------------------------------
# 3) RESUMEN DE MERCADO
# ---------------------------------------------------------------------------
elif seccion == ":material/trending_up: Resumen de mercado":
    st.title("Resumen de mercado del mes")
    st.caption("Este contexto se aplica a todos los reportes que generes en el período.")

    with st.container(border=True):
        periodo = st.text_input("Período (YYYY-MM)", value=periodo_actual(), key="periodo_mercado")
        existente = db.get_resumen_mercado(periodo) or {}

        oferta_demanda = st.text_area("Oferta y demanda de lotes", value=existente.get("oferta_demanda", ""), height=120)
        costo_construccion = st.text_area("Costo de construcción", value=existente.get("costo_construccion", ""), height=120)
        contexto_general = st.text_area("Contexto general / noticias del mercado", value=existente.get("contexto_general", ""), height=180)

        if st.button("Guardar resumen de mercado", type="primary"):
            db.save_resumen_mercado(periodo, oferta_demanda, costo_construccion, contexto_general, datetime.now().isoformat())
            st.success("Resumen guardado.", icon=":material/check_circle:")

# ---------------------------------------------------------------------------
# 4) GENERAR REPORTE
# ---------------------------------------------------------------------------
elif seccion == ":material/description: Generar reporte":
    st.title("Generar reporte por cliente")

    periodos = db.get_periodos_disponibles()
    if not periodos:
        st.info("Primero cargá un Excel de Xintel.", icon=":material/info:")
    else:
        periodo = st.selectbox("Período", periodos, key="periodo_reporte")
        clientes = db.get_clientes(periodo)
        opciones = {f"{c['ficha']} — {c['direccion']} ({c['barrio']})": c["ficha"] for c in clientes}
        elegido = st.selectbox("Cliente / ficha", list(opciones.keys()) if opciones else [], label_visibility="collapsed", placeholder="Seleccionar propiedad")

        if elegido:
            ficha = opciones[elegido]
            cliente = next(c for c in clientes if c["ficha"] == ficha)

            with st.container(border=True):
                st.markdown("**Métricas automáticas**")
                with st.container(horizontal=True):
                    st.metric("Consultas virtuales", cliente["consultas"])
                    st.metric("Estado", cliente["estado"])
                    st.metric("Operación", cliente.get("operacion") or "—")

            with st.container(border=True):
                st.markdown("**Visitas presenciales**")
                visitas_actuales = db.get_visitas(ficha, periodo)
                df_visitas = pd.DataFrame(visitas_actuales) if visitas_actuales else pd.DataFrame(columns=["fecha", "nombre", "comentario"])
                df_editado = st.data_editor(
                    df_visitas, num_rows="dynamic",
                    column_config={"fecha": st.column_config.TextColumn("Fecha (YYYY-MM-DD)")},
                )

                if st.button("Guardar visitas"):
                    visitas_dict = df_editado.dropna(subset=["fecha"]).to_dict("records")
                    db.replace_visitas(ficha, periodo, visitas_dict)
                    st.success("Visitas guardadas.", icon=":material/check_circle:")

            if st.button("Generar reporte", type="primary", icon=":material/description:"):
                with st.spinner("Generando reporte..."):
                    resumen = db.get_resumen_mercado(periodo)
                    visitas_guardadas = db.get_visitas(ficha, periodo)
                    ruta = generar_reporte(cliente, resumen, visitas_guardadas, periodo=periodo)
                    db.save_reporte(ficha, cliente["direccion"], periodo, datetime.now().isoformat(), str(ruta))
                    st.success("Reporte generado.", icon=":material/check_circle:")
                    with open(ruta, "rb") as f:
                        st.download_button("Descargar PDF", f, file_name=ruta.name, mime="application/pdf")

# ---------------------------------------------------------------------------
# 5) HISTORIAL
# ---------------------------------------------------------------------------
elif seccion == ":material/history: Historial":
    st.title("Historial de reportes generados")
    historial = db.get_historial()
    if not historial:
        st.info("Todavía no se generó ningún reporte.", icon=":material/info:")
    else:
        for r in historial:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([1, 3, 1, 1])
                c1.write(r["ficha"])
                c2.write(r["direccion"])
                c3.write(r["periodo"])
                pdf_path = Path(r["pdf_path"])
                if pdf_path.exists():
                    with open(pdf_path, "rb") as f:
                        c4.download_button("Descargar", f, file_name=pdf_path.name, key=f"dl_{r['id']}")
                else:
                    c4.caption("Archivo no disponible")
