from datetime import date, datetime
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import db
import excel_parser
from excel_parser import parse_xintel_excel, parse_complementary, parse_cartera, parse_consultas_diarias
from pdf_generator import generar_reporte

st.set_page_config(page_title="Panel Inmobiliario", page_icon=":material/analytics:", layout="wide")
db.init_db()

PRIMARY = "#2C2E7B"
ACCENT = "#EF8A23"

_is_dark = False
try:
    _theme = st.context.theme
    _is_dark = _theme and _theme.type == "dark"
except Exception:
    pass

_dark_css = """
    .stApp > header { background-color: """ + PRIMARY + """ !important; }
    .stApp { background-color: #0E1117 !important; }
    h1, h2, h3 { color: #B0B5E0 !important; }
    p, .stMarkdown, .stCaption, .st-bw, .st-c0, .st-dl { color: #D0D3DD !important; }
    .stButton>button[kind="primary"] { background-color: """ + ACCENT + """ !important; border-color: """ + ACCENT + """ !important; color: #FFFFFF !important; }
    div[data-testid="stSidebar"] > div:first-child { background-color: #151820 !important; }
    section[data-testid="stSidebar"] * { color: #E0E2E8 !important; }
    div[data-testid="stMetric"] > div { color: #E0E2E8 !important; }
    div[data-testid="stMetric"] label { color: #9BA0B0 !important; }
    div[data-testid="stMetric"] { background-color: #1A1D24 !important; border: 1px solid #2C2F3A !important; border-radius: 8px; padding: 8px 12px; }
    div.st-bb, div[data-testid="stDataFrame"], div[data-testid="stExpander"],
    div[class*="stAlert"], div[data-testid="stVerticalBlockBorder"] > div {
        background-color: #1A1D24 !important; border-color: #2C2F3A !important;
    }
    .st-bb { border-color: #2C2F3A !important; }
    .stTextInput input, .stTextArea textarea, div[data-baseweb="select"] > div,
    div[data-testid="stMultiSelect"] > div {
        background-color: #22262F !important; color: #E0E2E8 !important; border-color: #3A3E4A !important;
    }
    div[role="radiogroup"] label { color: #E0E2E8 !important; }
    button[kind="secondary"] { background-color: #22262F !important; color: #D0D3DD !important; border-color: #3A3E4A !important; }
    div.stAlert p { color: #D0D3DD !important; }
    .st-cx { background-color: #1A1D24 !important; }
    .st-bq { color: #D0D3DD !important; }
    div[data-testid="stHeader"] { background-color: #0E1117 !important; }
"""

st.markdown(f"""
<style>
    .stApp > header {{ background-color: {PRIMARY}; }}
    .stApp {{ background-color: #F7F8FA; }}
    h1, h2, h3 {{ color: {PRIMARY}; }}
    .stButton>button[kind="primary"] {{ background-color: {ACCENT}; border-color: {ACCENT}; }}
    div[data-testid="stSidebar"] > div:first-child {{ background-color: #FFFFFF; }}
    {_dark_css if _is_dark else ""}
</style>
""", unsafe_allow_html=True)


def _pie_chart(series, names_label):
    return px.pie(
        values=series.values,
        names=series.index,
        title=None,
        hole=0.4,
    ).update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True)


def _bar_chart(series, x_label, y_label):
    return px.bar(
        x=series.index,
        y=series.values,
        labels={"x": x_label, "y": y_label},
    ).update_layout(margin=dict(t=0, b=0, l=0, r=0), xaxis_tickangle=-45)


def _stacked_bar(df, x_label, y_label):
    fig = go.Figure()
    for col in df.columns:
        fig.add_trace(go.Bar(name=col, x=df.index, y=df[col]))
    fig.update_layout(
        barmode="stack",
        margin=dict(t=0, b=0, l=0, r=0),
        xaxis_tickangle=-45,
        xaxis_title=x_label,
        yaxis_title=y_label,
    )
    return fig


def _scatter_chart(df, x_col, y_col, color_col, x_label, y_label):
    return px.scatter(
        df, x=x_col, y=y_col, color=color_col,
        labels={x_col: x_label, y_col: y_label},
        hover_data=["ficha", "barrio", "direccion"],
    ).update_layout(margin=dict(t=0, b=0, l=0, r=0))


def _dual_axis_chart(df, bar_col, line_col):
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df.index, y=df[bar_col],
        name=bar_col, yaxis="y", marker_color="#2C2E7B"
    ))
    fig.add_trace(go.Scatter(
        x=df.index, y=df[line_col],
        name=line_col, yaxis="y2", mode="lines+markers",
        marker_color="#EF8A23", line=dict(color="#EF8A23")
    ))
    fig.update_layout(
        yaxis=dict(title=bar_col, side="left"),
        yaxis2=dict(title=line_col, overlaying="y", side="right"),
        margin=dict(t=0, b=0, l=0, r=0),
        xaxis_tickangle=-45,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


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
        user = st.text_input("Usuario", placeholder="Usuario", label_visibility="collapsed")
        password = st.text_input("Contraseña", type="password", placeholder="Contraseña", label_visibility="collapsed")
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
        [":material/explore: Explorar y filtrar", ":material/analytics: Analítica avanzada",
         ":material/upload: Cargar Excel Xintel",
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
# 2) ANALÍTICA AVANZADA
# ---------------------------------------------------------------------------
elif seccion == ":material/analytics: Analítica avanzada":
    st.title("Analítica avanzada")
    periodos = db.get_periodos_disponibles()
    if not periodos:
        st.info("Primero cargá un Excel de Xintel.", icon=":material/info:")
    else:
        periodo = st.selectbox("Período", periodos, key="periodo_avanzada")
        tab_cartera, tab_tendencias, tab_canales, tab_correlaciones, tab_conversion = st.tabs(
            ["Cartera", "Tendencias", "Canales", "Correlaciones", "Conversión"]
        )

        # ── TAB 1: CARTERA ──────────────────────────────────────────────
        with tab_cartera:
            cartera = db.get_cartera(periodo)
            if not cartera:
                st.info("No hay datos de cartera para este período.")
            else:
                df_c = pd.DataFrame(cartera)
                df_c["valor_num"] = df_c["valor"].apply(excel_parser.valor_to_float)

                col1, col2 = st.columns(2)
                with col1:
                    with st.container(border=True):
                        st.subheader("Distribución por tipo")
                        tipo_counts = df_c[df_c["categoria"] == "Propiedad"]["tipo"].value_counts()
                        if not tipo_counts.empty:
                            st.plotly_chart(
                                _pie_chart(tipo_counts, "Tipo"),
                                use_container_width=True, key="pie_tipo"
                            )
                        else:
                            st.caption("Sin datos de tipo.")

                with col2:
                    with st.container(border=True):
                        st.subheader("Valor promedio por tipo (U$D)")
                        ven = df_c[(df_c["operacion"] == "Venta") & (df_c["moneda"] == "U$D") & (df_c["valor_num"].notna())]
                        if not ven.empty:
                            avg_val = ven.groupby("tipo")["valor_num"].mean().sort_values(ascending=False)
                            st.plotly_chart(
                                _bar_chart(avg_val, "Tipo", "Valor promedio U$D"),
                                use_container_width=True, key="bar_valor_tipo"
                            )
                        else:
                            st.caption("Sin datos de valor.")

                with st.container(border=True):
                    st.subheader("Operación por barrio")
                    op_barrio = df_c[df_c["categoria"] == "Propiedad"].groupby(["barrio", "operacion"]).size().unstack(fill_value=0)
                    if not op_barrio.empty:
                        op_barrio = op_barrio.sort_values(op_barrio.columns[0], ascending=False).head(10)
                        st.plotly_chart(
                            _stacked_bar(op_barrio, "Barrio", "Cantidad"),
                            use_container_width=True, key="stack_op_barrio"
                        )
                    else:
                        st.caption("Sin datos.")

                with st.container(border=True):
                    st.subheader("Valor promedio por barrio (U$D, Venta)")
                    ven_barrio = ven.groupby("barrio")["valor_num"].mean().sort_values(ascending=False).head(10)
                    if not ven_barrio.empty:
                        st.plotly_chart(
                            _bar_chart(ven_barrio, "Barrio", "Valor promedio U$D"),
                            use_container_width=True, key="bar_valor_barrio"
                        )
                    else:
                        st.caption("Sin datos.")

                with st.expander("Ver tabla resumen"):
                    resumen = df_c[df_c["categoria"] == "Propiedad"].groupby(["tipo", "barrio"]).agg(
                        cantidad=("ficha", "count"),
                        valor_promedio=("valor_num", "mean"),
                        valor_min=("valor_num", "min"),
                        valor_max=("valor_num", "max"),
                    ).reset_index()
                    resumen["valor_promedio"] = resumen["valor_promedio"].round(2)
                    st.dataframe(resumen, hide_index=True)

        # ── TAB 2: TENDENCIAS ───────────────────────────────────────────
        with tab_tendencias:
            col1, col2 = st.columns(2)
            with col1:
                with st.container(border=True):
                    st.subheader("Consultas por día")
                    cd = db.get_consultas_diarias(periodo, "total")
                    if cd:
                        df_cd = pd.DataFrame(cd)
                        df_cd["fecha"] = pd.to_datetime(df_cd["fecha_hora"], errors="coerce").dt.date
                        diario = df_cd.groupby("fecha").size()
                        if not diario.empty:
                            st.line_chart(diario)
                        else:
                            st.caption("Sin datos.")
                    else:
                        st.caption("Sin datos de consultas diarias.")

            with col2:
                with st.container(border=True):
                    st.subheader("Consultas únicas por día")
                    cu = db.get_consultas_diarias(periodo, "unica")
                    if cu:
                        df_cu = pd.DataFrame(cu)
                        df_cu["fecha"] = pd.to_datetime(df_cu["fecha_hora"], errors="coerce").dt.date
                        diario_u = df_cu.groupby("fecha").size()
                        if not diario_u.empty:
                            st.line_chart(diario_u)
                        else:
                            st.caption("Sin datos.")
                    else:
                        st.caption("Sin datos.")

            with st.container(border=True):
                st.subheader("Propiedades nuevas y vendidas por día")
                if cartera:
                    df_cartera = pd.DataFrame(cartera)
                    nuevas = df_cartera[(df_cartera["estado"] == "NUEVAS") & (df_cartera["fecha_alta"].notna())].copy()
                    vendidas = df_cartera[(df_cartera["estado"] == "VENDIDAS") & (df_cartera["fecha_alta"].notna())].copy()
                    if not nuevas.empty or not vendidas.empty:
                        series = {}
                        if not nuevas.empty:
                            nuevas["fecha"] = pd.to_datetime(nuevas["fecha_alta"], errors="coerce").dt.date
                            series["Nuevas"] = nuevas.groupby("fecha").size()
                        if not vendidas.empty:
                            vendidas["fecha"] = pd.to_datetime(vendidas["fecha_alta"], errors="coerce").dt.date
                            series["Vendidas"] = vendidas.groupby("fecha").size()
                        df_ts = pd.DataFrame(series).fillna(0)
                        if not df_ts.empty:
                            st.line_chart(df_ts)
                        else:
                            st.caption("Sin datos de fechas.")
                    else:
                        st.caption("Sin datos.")
                else:
                    st.caption("Sin datos de cartera.")

        # ── TAB 3: CANALES ──────────────────────────────────────────────
        with tab_canales:
            canales = db.get_canales(periodo)
            if not canales:
                st.info("Sin datos de canales.")
            else:
                df_can = pd.DataFrame(canales)
                df_can["tasa_unicidad"] = (df_can["unicas"] / df_can["total"] * 100).round(1)
                total_cons = df_can["total"].sum()
                df_can["participacion"] = (df_can["total"] / total_cons * 100).round(1)

                with st.container(border=True):
                    st.subheader("Rendimiento por canal")
                    st.dataframe(
                        df_can[["canal", "total", "unicas", "tasa_unicidad", "participacion"]],
                        column_config={
                            "canal": "Canal",
                            "total": "Totales",
                            "unicas": "Únicas",
                            "tasa_unicidad": st.column_config.NumberColumn("Tasa unicidad %", format="%.1f%%"),
                            "participacion": st.column_config.NumberColumn("Participación %", format="%.1f%%"),
                        },
                        hide_index=True,
                    )

                col1, col2 = st.columns(2)
                with col1:
                    with st.container(border=True):
                        st.subheader("Totales por canal")
                        orden = df_can.sort_values("total", ascending=True)
                        st.plotly_chart(
                            _bar_chart(orden.set_index("canal")["total"], "Canal", "Total"),
                            use_container_width=True, key="canal_total"
                        )
                with col2:
                    with st.container(border=True):
                        st.subheader("Participación por canal")
                        st.plotly_chart(
                            _pie_chart(df_can.set_index("canal")["total"], "Canal"),
                            use_container_width=True, key="canal_pie"
                        )

                if len(periodos) > 1:
                    with st.expander("Comparar con otro período"):
                        p2 = st.selectbox("Período a comparar", [p for p in periodos if p != periodo], key="p2_canales")
                        canales2 = db.get_canales(p2)
                        if canales2:
                            df_c2 = pd.DataFrame(canales2)
                            comp = df_can[["canal", "total"]].merge(df_c2[["canal", "total"]], on="canal", how="outer", suffixes=(f"_{periodo}", f"_{p2}")).fillna(0)
                            comp["diff"] = comp[f"total_{periodo}"] - comp[f"total_{p2}"]
                            st.dataframe(comp, hide_index=True)

        # ── TAB 4: CORRELACIONES ────────────────────────────────────────
        with tab_correlaciones:
            clientes = db.get_clientes(periodo)
            if not clientes:
                st.info("Sin datos de clientes.")
            else:
                df_cli = pd.DataFrame(clientes)
                df_cli["valor_num"] = df_cli["valor"].apply(excel_parser.valor_to_float)

                df_venta = df_cli[(df_cli["operacion"] == "Venta") & (df_cli["moneda"] == "U$D") & (df_cli["valor_num"].notna())]
                df_alq = df_cli[(df_cli["operacion"] == "Alquiler") & (df_cli["moneda"] == "U$D") & (df_cli["valor_num"].notna())]

                col1, col2 = st.columns(2)
                with col1:
                    with st.container(border=True):
                        st.subheader("Consultas vs Precio — Venta")
                        if not df_venta.empty:
                            fig = _scatter_chart(df_venta, "valor_num", "consultas", "tipo", "Valor U$D", "Consultas")
                            st.plotly_chart(fig, use_container_width=True, key="scatter_venta")
                        else:
                            st.caption("Sin datos de venta.")
                with col2:
                    with st.container(border=True):
                        st.subheader("Consultas vs Precio — Alquiler")
                        if not df_alq.empty:
                            fig = _scatter_chart(df_alq, "valor_num", "consultas", "tipo", "Valor U$D", "Consultas")
                            st.plotly_chart(fig, use_container_width=True, key="scatter_alq")
                        else:
                            st.caption("Sin datos de alquiler.")

                with st.container(border=True):
                    st.subheader("Promedio de consultas por tipo")
                    prom_tipo = df_cli.groupby("tipo")["consultas"].mean().sort_values(ascending=False)
                    if not prom_tipo.empty:
                        st.plotly_chart(
                            _bar_chart(prom_tipo, "Tipo", "Consultas promedio"),
                            use_container_width=True, key="bar_cons_tipo"
                        )
                    else:
                        st.caption("Sin datos.")

                with st.container(border=True):
                    st.subheader("Consultas totales y valor promedio por barrio")
                    agrupado = df_cli[df_cli["valor_num"].notna()].groupby("barrio").agg(
                        consultas_totales=("consultas", "sum"),
                        valor_promedio=("valor_num", "mean"),
                    ).sort_values("consultas_totales", ascending=False).head(10)
                    if not agrupado.empty:
                        fig = _dual_axis_chart(agrupado, "Consultas totales", "Valor promedio U$D")
                        st.plotly_chart(fig, use_container_width=True, key="dual_barrio")
                    else:
                        st.caption("Sin datos.")

        # ── TAB 5: CONVERSIÓN ──────────────────────────────────────────
        with tab_conversion:
            clientes = db.get_clientes(periodo)
            if not clientes:
                st.info("Sin datos de clientes para conversión.")
            else:
                total_consultas = sum(c["consultas"] for c in clientes)
                visitas_count = len(db.get_visitas("", periodo)) if periodo else 0
                total_visitas = 0
                for c in clientes:
                    total_visitas += len(db.get_visitas(c["ficha"], periodo))

                cartera_data = db.get_cartera(periodo)
                df_cartera = pd.DataFrame(cartera_data) if cartera_data else pd.DataFrame()
                total_vendidas = len(df_cartera[df_cartera["estado"] == "VENDIDAS"]) if not df_cartera.empty else 0
                total_alquiladas = len(df_cartera[df_cartera["estado"] == "ALQUILADAS"]) if not df_cartera.empty else 0

                t_cons_visita = (total_visitas / total_consultas * 100) if total_consultas > 0 else 0
                t_visita_op = ((total_vendidas + total_alquiladas) / total_visitas * 100) if total_visitas > 0 else 0
                t_cons_op = ((total_vendidas + total_alquiladas) / total_consultas * 100) if total_consultas > 0 else 0

                with st.container(border=True):
                    st.subheader("Funil de conversión del período")
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("Consultas", f"{total_consultas:,}")
                    c2.metric("Visitas", f"{total_visitas:,}")
                    c3.metric("Vendidas", total_vendidas)
                    c4.metric("Alquiladas", total_alquiladas)

                    st.markdown("**Progreso del funil**")
                    st.progress(min(total_consultas / max(total_consultas, 1), 1.0), text=f"Consultas: {total_consultas:,}")
                    st.progress(min(total_visitas / max(total_consultas, 1), 1.0), text=f"Visitas: {total_visitas:,}")
                    st.progress(min((total_vendidas + total_alquiladas) / max(total_consultas, 1), 1.0), text=f"Operaciones cerradas: {total_vendidas + total_alquiladas}")

                with st.container(border=True):
                    st.subheader("Tasas de conversión")
                    cc1, cc2, cc3 = st.columns(3)
                    cc1.metric("Consulta → Visita", f"{t_cons_visita:.1f}%")
                    cc2.metric("Visita → Operación", f"{t_visita_op:.1f}%")
                    cc3.metric("Consulta → Operación", f"{t_cons_op:.1f}%")

                with st.container(border=True):
                    st.subheader("Conversión por barrio (top 10)")
                    if not df_cartera.empty:
                        prop_por_barrio = df_cartera[df_cartera["categoria"] == "Propiedad"]
                        if not prop_por_barrio.empty:
                            barrio_conv = prop_por_barrio.groupby("barrio").agg(
                                total=("ficha", "count"),
                                vendidas=("estado", lambda x: (x == "VENDIDAS").sum()),
                                alquiladas=("estado", lambda x: (x == "ALQUILADAS").sum()),
                            ).reset_index()
                            barrio_conv["cerradas"] = barrio_conv["vendidas"] + barrio_conv["alquiladas"]
                            barrio_conv["tasa_cierre"] = (barrio_conv["cerradas"] / barrio_conv["total"] * 100).round(1)
                            barrio_conv = barrio_conv.sort_values("total", ascending=False).head(10)
                            st.dataframe(
                                barrio_conv[["barrio", "total", "vendidas", "alquiladas", "cerradas", "tasa_cierre"]],
                                column_config={
                                    "barrio": "Barrio",
                                    "total": "Total propiedades",
                                    "vendidas": "Vendidas",
                                    "alquiladas": "Alquiladas",
                                    "cerradas": "Cerradas",
                                    "tasa_cierre": st.column_config.NumberColumn("Tasa de cierre %", format="%.1f%%"),
                                },
                                hide_index=True,
                            )


# ---------------------------------------------------------------------------
# 3) CARGAR EXCEL XINTEL
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
                    cartera = parse_cartera(archivo, periodo)
                    db.insert_cartera(cartera)
                    consultas = parse_consultas_diarias(archivo, periodo)
                    db.insert_consultas_diarias(consultas)
                    st.success(f"Archivo procesado — {len(registros)} fichas, {len(cartera)} propiedades en cartera, {len(consultas)} consultas diarias para {periodo}.", icon=":material/check_circle:")
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
                    canales = db.get_canales(periodo)
                    todos = db.get_clientes(periodo)
                    clientes_localidad = [c for c in todos if c.get("localidad") == cliente.get("localidad")]
                    clientes_tipo_op = [c for c in todos if c.get("tipo") == cliente.get("tipo") and c.get("operacion") == cliente.get("operacion")]
                    datos_comp = {}
                    if clientes_localidad:
                        datos_comp["consultas_prom_localidad"] = sum(c["consultas"] for c in clientes_localidad) / len(clientes_localidad)
                    if clientes_tipo_op:
                        vals = []
                        for c in clientes_tipo_op:
                            v = excel_parser.valor_to_float(c.get("valor"))
                            if v is not None and c.get("moneda") == "U$D":
                                vals.append(v)
                        datos_comp["valor_promedio_tipo_op"] = sum(vals) / len(vals) if vals else 0
                    datos_comp["localidad"] = cliente.get("localidad", "")
                    datos_comp["tipo"] = cliente.get("tipo", "")
                    datos_comp["operacion"] = cliente.get("operacion", "")
                    ruta = generar_reporte(cliente, resumen, visitas_guardadas, periodo=periodo, canales=canales, datos_comp=datos_comp)
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
