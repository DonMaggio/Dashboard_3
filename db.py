import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data.db"


def _conn():
    return sqlite3.connect(str(DB_PATH))


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with _conn() as c:
        c.execute("""
            CREATE TABLE IF NOT EXISTS clientes (
                ficha TEXT NOT NULL,
                periodo TEXT NOT NULL,
                direccion TEXT,
                barrio TEXT,
                localidad TEXT,
                estado TEXT,
                consultas INTEGER DEFAULT 0,
                operacion TEXT,
                valor TEXT,
                moneda TEXT,
                tipo TEXT DEFAULT '',
                PRIMARY KEY (ficha, periodo)
            )
        """)
        try:
            c.execute("ALTER TABLE clientes ADD COLUMN tipo TEXT DEFAULT ''")
        except sqlite3.OperationalError:
            pass
        c.execute("""
            CREATE TABLE IF NOT EXISTS resumen_mercado (
                periodo TEXT PRIMARY KEY,
                oferta_demanda TEXT,
                costo_construccion TEXT,
                contexto_general TEXT,
                updated_at TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS complementaria (
                periodo TEXT NOT NULL,
                tipo TEXT NOT NULL,
                clave TEXT NOT NULL,
                valor REAL DEFAULT 0,
                extra TEXT DEFAULT ''
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS visitas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ficha TEXT NOT NULL,
                periodo TEXT NOT NULL,
                fecha TEXT,
                nombre TEXT,
                comentario TEXT
            )
        """)
        c.execute("""
            CREATE TABLE IF NOT EXISTS historial (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ficha TEXT NOT NULL,
                direccion TEXT,
                periodo TEXT NOT NULL,
                generado_en TEXT,
                pdf_path TEXT
            )
        """)


def upsert_clientes(registros):
    with _conn() as c:
        for r in registros:
            c.execute("""
                INSERT OR REPLACE INTO clientes (ficha, periodo, direccion, barrio, localidad, estado, consultas, operacion, valor, moneda, tipo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                str(r["ficha"]), r["periodo"], r.get("direccion"),
                r.get("barrio"), r.get("localidad"), r.get("estado"),
                int(r.get("consultas", 0)), r.get("operacion"),
                r.get("valor"), r.get("moneda"), r.get("tipo", "")
            ))


def get_periodos_disponibles():
    with _conn() as c:
        rows = c.execute("SELECT DISTINCT periodo FROM clientes ORDER BY periodo DESC").fetchall()
    return [r[0] for r in rows]


def get_clientes(periodo):
    with _conn() as c:
        rows = c.execute(
            "SELECT ficha, direccion, barrio, localidad, estado, consultas, operacion, valor, moneda, tipo FROM clientes WHERE periodo = ? ORDER BY ficha",
            (periodo,)
        ).fetchall()
    return [
        {"ficha": r[0], "direccion": r[1], "barrio": r[2], "localidad": r[3],
         "estado": r[4], "consultas": r[5], "operacion": r[6], "valor": r[7], "moneda": r[8], "tipo": r[9] or ""}
        for r in rows
    ]


def get_resumen_mercado(periodo):
    with _conn() as c:
        row = c.execute("SELECT oferta_demanda, costo_construccion, contexto_general FROM resumen_mercado WHERE periodo = ?", (periodo,)).fetchone()
    if row:
        return {"oferta_demanda": row[0], "costo_construccion": row[1], "contexto_general": row[2]}
    return {}


def save_resumen_mercado(periodo, oferta_demanda, costo_construccion, contexto_general, updated_at):
    with _conn() as c:
        c.execute("""
            INSERT OR REPLACE INTO resumen_mercado (periodo, oferta_demanda, costo_construccion, contexto_general, updated_at)
            VALUES (?, ?, ?, ?, ?)
        """, (periodo, oferta_demanda, costo_construccion, contexto_general, updated_at))


def get_visitas(ficha, periodo):
    with _conn() as c:
        rows = c.execute(
            "SELECT fecha, nombre, comentario FROM visitas WHERE ficha = ? AND periodo = ? ORDER BY fecha",
            (ficha, periodo)
        ).fetchall()
    return [{"fecha": r[0], "nombre": r[1], "comentario": r[2]} for r in rows]


def replace_visitas(ficha, periodo, visitas):
    with _conn() as c:
        c.execute("DELETE FROM visitas WHERE ficha = ? AND periodo = ?", (ficha, periodo))
        for v in visitas:
            c.execute(
                "INSERT INTO visitas (ficha, periodo, fecha, nombre, comentario) VALUES (?, ?, ?, ?, ?)",
                (ficha, periodo, v.get("fecha"), v.get("nombre"), v.get("comentario"))
            )


def save_complementaria(periodo, data):
    with _conn() as c:
        c.execute("DELETE FROM complementaria WHERE periodo = ?", (periodo,))
        for canal in data.get("canales", []):
            clave = canal.get("canal", "")
            c.execute(
                "INSERT INTO complementaria (periodo, tipo, clave, valor, extra) VALUES (?, 'canal', ?, ?, ?)",
                (periodo, clave, float(canal.get("total", 0)),
                 str(int(canal.get("unicas", 0))))
            )
        for op in data.get("operaciones", []):
            clave = op.get("operacion", "")
            c.execute(
                "INSERT INTO complementaria (periodo, tipo, clave, valor) VALUES (?, 'operacion', ?, ?)",
                (periodo, clave, float(op.get("total", 0)))
            )
        for t in data.get("tareas", []):
            clave = t.get("motivo", "")
            c.execute(
                "INSERT INTO complementaria (periodo, tipo, clave, valor) VALUES (?, 'tarea', ?, ?)",
                (periodo, clave, float(t.get("cantidad", 0)))
            )
        for tr in data.get("tiempo_respuesta", []):
            c.execute(
                "INSERT INTO complementaria (periodo, tipo, clave, valor, extra) VALUES (?, 'tiempo', ?, ?, ?)",
                (periodo, tr["operador"], float(tr["tiempo_promedio"]),
                 str(int(tr["tareas_respondidas"])))
            )


def get_complementaria(periodo, tipo):
    with _conn() as c:
        rows = c.execute(
            "SELECT clave, valor, extra FROM complementaria WHERE periodo = ? AND tipo = ? ORDER BY valor DESC",
            (periodo, tipo)
        ).fetchall()
    return rows


def get_canales(periodo):
    rows = get_complementaria(periodo, "canal")
    return [{"canal": r[0], "total": int(r[1]), "unicas": int(r[2])} for r in rows]


def get_operaciones(periodo):
    rows = get_complementaria(periodo, "operacion")
    return [{"operacion": r[0], "total": int(r[1])} for r in rows]


def get_tareas(periodo):
    rows = get_complementaria(periodo, "tarea")
    return [{"motivo": r[0], "cantidad": int(r[1])} for r in rows]


def get_tiempo_respuesta(periodo):
    rows = get_complementaria(periodo, "tiempo")
    return [{"operador": r[0], "tiempo_promedio": float(r[1]), "tareas_respondidas": int(r[2])} for r in rows]


def save_reporte(ficha, direccion, periodo, generado_en, pdf_path):
    with _conn() as c:
        c.execute(
            "INSERT INTO historial (ficha, direccion, periodo, generado_en, pdf_path) VALUES (?, ?, ?, ?, ?)",
            (ficha, direccion, periodo, generado_en, pdf_path)
        )


def get_historial():
    with _conn() as c:
        rows = c.execute(
            "SELECT id, ficha, direccion, periodo, generado_en, pdf_path FROM historial ORDER BY generado_en DESC"
        ).fetchall()
    return [
        {"id": r[0], "ficha": r[1], "direccion": r[2], "periodo": r[3],
         "generado_en": r[4], "pdf_path": r[5]}
        for r in rows
    ]
