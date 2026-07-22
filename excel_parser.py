from datetime import datetime

import pandas as pd


def _clean_valor(val):
    if pd.isna(val):
        return None
    s = str(val).replace(".", "").replace(",", ".")
    try:
        return f"{float(s):.2f}"
    except ValueError:
        return str(val)


def valor_to_float(valor_str):
    if valor_str is None:
        return None
    try:
        return float(valor_str)
    except (ValueError, TypeError):
        return None


def _map_estado(sheet_name):
    name = sheet_name.replace("Propiedades ", "").replace("Tasaciones ", "Tasación ")
    return name.strip()


def _build_ficha_map(xls):
    estado_map = {}
    extra_map = {}
    for sheet in xls.sheet_names:
        if not (sheet.startswith("Propiedades ") or sheet.startswith("Tasaciones ")):
            continue
        df = pd.read_excel(xls, sheet_name=sheet)
        if "Ficha nro." not in df.columns:
            continue
        estado = _map_estado(sheet)
        for _, row in df.iterrows():
            f = row.get("Ficha nro.")
            if pd.isna(f):
                continue
            f = int(f)
            if f not in estado_map:
                estado_map[f] = estado
            if f not in extra_map:
                extra_map[f] = {
                    "operacion": str(row.get("Operación", "")).strip() if pd.notna(row.get("Operación")) else "",
                    "valor": _clean_valor(row.get("Valor")),
                    "moneda": str(row.get("Moneda", "")).strip() if pd.notna(row.get("Moneda")) else "",
                    "tipo": str(row.get("Tipo", "")).strip() if pd.notna(row.get("Tipo")) else "",
                }
    return estado_map, extra_map


def parse_xintel_excel(archivo, periodo):
    xls = pd.ExcelFile(archivo)

    top = pd.read_excel(xls, sheet_name="Top Propiedades Consultadas")
    top = top.dropna(subset=["Ficha nro."])
    top = top[top["Origen"].str.strip().str.lower() != "historico"]
    top["Ficha nro."] = top["Ficha nro."].astype(int)

    estado_map, extra_map = _build_ficha_map(xls)

    registros = []
    for _, row in top.iterrows():
        ficha = int(row["Ficha nro."])
        extra = extra_map.get(ficha, {})
        estado = estado_map.get(ficha)

        if not estado:
            origen = str(row.get("Origen", "")).strip() if pd.notna(row.get("Origen")) else "Activo"
            estado = origen

        barrio = str(row.get("Barrio", "")).strip() if pd.notna(row.get("Barrio")) else "sin especificar"
        direccion = str(row.get("Dirección", "")).strip() if pd.notna(row.get("Dirección")) else ""

        registros.append({
            "ficha": str(ficha),
            "direccion": direccion,
            "barrio": barrio,
            "localidad": str(row.get("Localidad", "")).strip() if pd.notna(row.get("Localidad")) else "",
            "estado": estado,
            "consultas": int(row.get("Total Consultas", 0)) if pd.notna(row.get("Total Consultas")) else 0,
            "operacion": extra.get("operacion", ""),
            "valor": extra.get("valor"),
            "moneda": extra.get("moneda", ""),
            "tipo": extra.get("tipo", ""),
            "periodo": periodo,
        })

    return registros


def parse_cartera(archivo, periodo):
    xls = pd.ExcelFile(archivo)
    registros = []
    for sheet in xls.sheet_names:
        if not (sheet.startswith("Propiedades ") or sheet.startswith("Tasaciones ")):
            continue
        df = pd.read_excel(xls, sheet_name=sheet)
        if "Ficha nro." not in df.columns:
            continue
        categoria = "Propiedad" if sheet.startswith("Propiedades ") else "Tasacion"
        estado = sheet.replace("Propiedades ", "").replace("Tasaciones ", "Tasación ").strip()
        for _, row in df.iterrows():
            f = row.get("Ficha nro.")
            if pd.isna(f):
                continue
            fecha_raw = row.get("Fecha")
            fecha = None
            if pd.notna(fecha_raw):
                try:
                    fecha = str(pd.Timestamp(fecha_raw).date())
                except Exception:
                    fecha = str(fecha_raw)
            registros.append({
                "ficha": str(int(f)),
                "fecha_alta": fecha,
                "direccion": str(row.get("Dirección", "")).strip() if pd.notna(row.get("Dirección")) else "",
                "barrio": str(row.get("Barrio", "")).strip() if pd.notna(row.get("Barrio")) else "",
                "localidad": str(row.get("Localidad", "")).strip() if pd.notna(row.get("Localidad")) else "",
                "tipo": str(row.get("Tipo", "")).strip() if pd.notna(row.get("Tipo")) else "",
                "operacion": str(row.get("Operación", "")).strip() if pd.notna(row.get("Operación")) else "",
                "valor": _clean_valor(row.get("Valor")),
                "moneda": str(row.get("Moneda", "")).strip() if pd.notna(row.get("Moneda")) else "",
                "estado": estado,
                "categoria": categoria,
                "periodo": periodo,
            })
    return registros


def parse_consultas_diarias(archivo, periodo):
    xls = pd.ExcelFile(archivo)
    registros = []

    sheet_map = {
        "CONSULTAS POR CANAL": "total",
        "CONSULTAS UNICAS POR CANAL": "unica",
        "CONSULTAS POR OPERACION": "operacion",
    }

    for sheet_name, tipo_reg in sheet_map.items():
        try:
            df = pd.read_excel(xls, sheet_name=sheet_name)
        except ValueError:
            continue
        if df.empty:
            continue
        col_key = "Canal" if tipo_reg != "operacion" else "Operación"
        if col_key not in df.columns:
            continue
        for _, row in df.iterrows():
            fecha_raw = row.get("Fecha")
            fecha_hora = None
            if pd.notna(fecha_raw):
                try:
                    fecha_hora = str(pd.Timestamp(fecha_raw))
                except Exception:
                    fecha_hora = str(fecha_raw)
            registros.append({
                "periodo": periodo,
                "fecha_hora": fecha_hora,
                "tipo_registro": tipo_reg,
                "canal": str(row.get("Canal", "")).strip() if tipo_reg != "operacion" and pd.notna(row.get("Canal")) else "",
                "operacion": str(row.get("Operación", "")).strip() if tipo_reg == "operacion" and pd.notna(row.get("Operación")) else "",
                "cliente": str(row.get("Cliente", "")).strip() if pd.notna(row.get("Cliente")) else "",
                "email": str(row.get("E-mail", "")).strip() if pd.notna(row.get("E-mail")) else "",
                "telefono": str(row.get("Teléfono", "")).strip() if pd.notna(row.get("Teléfono")) else "",
            })
    return registros


def parse_complementary(archivo, periodo):
    xls = pd.ExcelFile(archivo)

    canales_t = _count_by_col(xls, "CONSULTAS POR CANAL", "Canal")
    canales_u = _count_by_col(xls, "CONSULTAS UNICAS POR CANAL", "Canal")
    todos_canales = list(set(list(canales_t.keys()) + list(canales_u.keys())))
    canales_data = []
    for c in sorted(todos_canales):
        canales_data.append({"canal": c, "total": canales_t.get(c, 0), "unicas": canales_u.get(c, 0)})

    ops = _count_by_col(xls, "CONSULTAS POR OPERACION", "Operación")
    operaciones_data = [{"operacion": k, "total": v} for k, v in sorted(ops.items(), key=lambda x: -x[1])]

    tareas_data = []
    try:
        tf = pd.read_excel(xls, sheet_name="Informe de tareas")
        if not tf.empty and "Motivo" in tf.columns and "Cantidad" in tf.columns:
            for _, row in tf.iterrows():
                if pd.notna(row.get("Motivo")) and pd.notna(row.get("Cantidad")):
                    tareas_data.append({
                        "motivo": str(row["Motivo"]).strip(),
                        "cantidad": int(row["Cantidad"]),
                    })
    except ValueError:
        pass

    tiempo_data = []
    try:
        tiempo = pd.read_excel(xls, sheet_name="Tiempo Promedio Respuesta")
        tiempo = tiempo.dropna(subset=["Operador"])
        for _, row in tiempo.iterrows():
            tiempo_data.append({
                "operador": str(row.get("Operador", "")).strip(),
                "tiempo_promedio": float(row.get("Tiempo Promedio Respuesta (horas)", 0) or 0),
                "tareas_respondidas": int(row.get("Total Tareas Respondidas", 0) or 0),
            })
    except ValueError:
        pass

    return {
        "canales": canales_data,
        "operaciones": operaciones_data,
        "tareas": tareas_data,
        "tiempo_respuesta": tiempo_data,
    }


def _count_by_col(xls, sheet, col):
    try:
        df = pd.read_excel(xls, sheet_name=sheet)
    except ValueError:
        return {}
    if df.empty or col not in df.columns:
        return {}
    return df[col].value_counts().to_dict()

