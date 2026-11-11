from datetime import date, datetime
 
import pytest
from sqlalchemy import text
 
TABLAS = ["agg_ventas_diarias", "agg_productos_top", "agg_resumen_general"]
 
# Esquema equivalente a la migracion Alembic 002 (CREATE TABLE IF NOT EXISTS:
# si la migracion ya se aplico en la base de pruebas, no se modifica).
DDL = [
    """CREATE TABLE IF NOT EXISTS agg_ventas_diarias (
        fecha DATE PRIMARY KEY,
        numero_ventas BIGINT NOT NULL,
        total_ingresos NUMERIC(16, 2) NOT NULL,
        procesado_en TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS agg_productos_top (
        ranking INTEGER PRIMARY KEY,
        product_id INTEGER NOT NULL,
        product_name VARCHAR(150) NOT NULL,
        unidades_vendidas BIGINT NOT NULL,
        total_recaudado NUMERIC(16, 2) NOT NULL,
        procesado_en TIMESTAMP
    )""",
    """CREATE TABLE IF NOT EXISTS agg_resumen_general (
        id SMALLINT PRIMARY KEY,
        total_ventas BIGINT NOT NULL,
        ingresos_totales NUMERIC(16, 2) NOT NULL,
        total_productos INTEGER NOT NULL,
        procesado_en TIMESTAMP
    )""",
]
 
PROCESADO = datetime(2026, 11, 11, 4, 0, 59)
 
 
def _limpiar(db):
    for tabla in TABLAS:
        db.execute(text(f"DELETE FROM {tabla}"))
    db.commit()
 
 
@pytest.fixture
def agg_tables(db):
    for ddl in DDL:
        db.execute(text(ddl))
    db.commit()
    _limpiar(db)
    yield db
    _limpiar(db)
 
 
def _cargar_resultados(db):
    db.execute(
        text(
            "INSERT INTO agg_resumen_general "
            "(id, total_ventas, ingresos_totales, total_productos, procesado_en) "
            "VALUES (1, 200000, 2649828.80, 12, :ts)"
        ),
        {"ts": PROCESADO},
    )
    productos = [
        (1, 5, "Coca Cola 500ml", 50641, 177243.50),
        (2, 2, "Azucar Rubia 1kg", 50436, 191656.80),
        (3, 7, "Galletas Margarita 4pk", 50392, 110862.40),
    ]
    for ranking, pid, nombre, unidades, recaudado in productos:
        db.execute(
            text(
                "INSERT INTO agg_productos_top "
                "(ranking, product_id, product_name, unidades_vendidas, total_recaudado, procesado_en) "
                "VALUES (:r, :p, :n, :u, :t, :ts)"
            ),
            {"r": ranking, "p": pid, "n": nombre, "u": unidades, "t": recaudado, "ts": PROCESADO},
        )
    dias = [
        (date(2026, 11, 6), 6711, 88641.40),
        (date(2026, 11, 7), 6615, 86881.60),
        (date(2026, 11, 8), 6670, 87417.30),
        (date(2026, 11, 9), 6759, 89912.60),
        (date(2026, 11, 10), 6514, 86241.50),
    ]
    for fecha, ventas, ingresos in dias:
        db.execute(
            text(
                "INSERT INTO agg_ventas_diarias "
                "(fecha, numero_ventas, total_ingresos, procesado_en) "
                "VALUES (:f, :v, :i, :ts)"
            ),
            {"f": fecha, "v": ventas, "i": ingresos, "ts": PROCESADO},
        )
    db.commit()
 
 
def test_spark_sin_resultados(agg_tables, reportes_client):
    """Si el job de Spark aun no corrio, la API responde 200 con disponible=false."""
    res = reportes_client.get("/api/v1/reportes/spark")
    assert res.status_code == 200
    data = res.json()
    assert data["disponible"] is False
    assert data["resumen"] is None
    assert data["productos_top"] == []
    assert data["ventas_por_dia"] == []
 
 
def test_spark_con_resultados(agg_tables, reportes_client):
    """Devuelve resumen, ranking y ventas por dia persistidos por Spark."""
    _cargar_resultados(agg_tables)
 
    res = reportes_client.get("/api/v1/reportes/spark")
    assert res.status_code == 200
    data = res.json()
 
    assert data["disponible"] is True
    assert data["procesado_en"].startswith("2026-11-11T04:00:59")
    assert data["resumen"]["total_ventas"] == 200000
    assert float(data["resumen"]["ingresos_totales"]) == 2649828.80
    assert data["resumen"]["total_productos"] == 12
 
    top = data["productos_top"]
    assert [t["ranking"] for t in top] == [1, 2, 3]
    assert top[0]["product_name"] == "Coca Cola 500ml"
    assert top[0]["unidades_vendidas"] == 50641
    assert float(top[0]["total_recaudado"]) == 177243.50
 
    dias = data["ventas_por_dia"]
    assert [d["fecha"] for d in dias] == [
        "2026-11-06", "2026-11-07", "2026-11-08", "2026-11-09", "2026-11-10",
    ]
    assert dias[-1]["numero_ventas"] == 6514
    assert float(dias[-1]["total_ingresos"]) == 86241.50
 
 
def test_spark_parametros_limite_y_dias(agg_tables, reportes_client):
    """`limite` recorta el ranking y `dias` devuelve los ultimos N dias en orden cronologico."""
    _cargar_resultados(agg_tables)
 
    data = reportes_client.get("/api/v1/reportes/spark?limite=2&dias=2").json()
    assert [t["ranking"] for t in data["productos_top"]] == [1, 2]
    assert [d["fecha"] for d in data["ventas_por_dia"]] == ["2026-11-09", "2026-11-10"]
 
 
@pytest.mark.parametrize("query", ["limite=0", "limite=51", "dias=0", "dias=366"])
def test_spark_parametros_invalidos(agg_tables, reportes_client, query):
    res = reportes_client.get(f"/api/v1/reportes/spark?{query}")
    assert res.status_code == 422
 
 
def test_reportes_en_vivo_siguen_funcionando(agg_tables, reportes_client):
    """El nuevo endpoint no altera los reportes existentes calculados en vivo."""
    res = reportes_client.get("/api/v1/reportes/resumen-general")
    assert res.status_code == 200
    assert res.json()["total_ventas_historicas"] == 0
 