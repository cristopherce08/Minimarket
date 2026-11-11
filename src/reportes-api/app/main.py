import logging
import time
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from typing import List
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import text, func, cast, Date, desc
 
from .config import settings
from .database import get_db
from .schemas import (
    VentasHoyResponse,
    ProductoTopItem,
    VentaDiaItem,
    ResumenGeneralResponse,
    SparkResumen,
    SparkResultadosResponse,
    HealthResponse,
    ReadyResponse,
)
from .metrics import PrometheusMiddleware, metrics_endpoint
 
# Importar o mapear modelos para consultas relacionales
from sqlalchemy import Table, MetaData
 
metadata = MetaData()
 
# Logging estructurado
logging.basicConfig(
    level=logging.INFO,
    format='{"time": "%(asctime)s", "level": "%(levelname)s", "service": "reportes-api", "message": "%(message)s"}',
)
logger = logging.getLogger("reportes-api")
 
app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    description="Microservicio de analítica y reportes estadísticos para MiniMarket Cloud.",
)
 
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
 
app.add_middleware(PrometheusMiddleware)
 
 
# -------------------------------------------------------------
# Endpoints de Diagnóstico
# -------------------------------------------------------------
 
@app.get("/health", response_model=HealthResponse, tags=["Diagnóstico"])
def health_check():
    """Liveness probe para Kubernetes."""
    return HealthResponse(
        status="healthy",
        service="reportes-api",
        timestamp=datetime.now(timezone.utc),
    )
 
 
@app.get("/ready", response_model=ReadyResponse, tags=["Diagnóstico"])
def readiness_check(db: Session = Depends(get_db)):
    """Readiness probe: valida conectividad con la base de datos."""
    start = time.time()
    try:
        db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000
        return ReadyResponse(
            status="ready",
            database="connected",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        logger.error(f"Fallo en readiness probe de reportes: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Fallo de conexión a base de datos: {str(e)}",
        )
 
 
@app.get("/metrics", tags=["Diagnóstico"])
def metrics():
    """Exposición de métricas Prometheus para el servicio de reportes."""
    return metrics_endpoint()
 
 
# -------------------------------------------------------------
# Endpoints de Reportes Estadísticos
# -------------------------------------------------------------
 
@app.get("/api/v1/reportes/ventas-hoy", response_model=VentasHoyResponse, tags=["Reportes"])
def get_ventas_hoy(db: Session = Depends(get_db)):
    """
    Retorna el total vendido y número de ventas del día actual.
    (En etapas posteriores, consumirá resúmenes persistidos por Apache Spark).
    """
    today = date.today()
    try:
        # Consulta SQL compatible y rápida
        sql = text("""
            SELECT 
                COUNT(id) AS total_ventas,
                COALESCE(SUM(total), 0) AS total_ingresos
            FROM sales
            WHERE DATE(created_at) = :today
        """)
        row = db.execute(sql, {"today": today}).fetchone()
 
        total_ventas = int(row[0]) if row and row[0] is not None else 0
        total_ingresos = Decimal(str(row[1])) if row and row[1] is not None else Decimal("0.00")
        ticket_promedio = round(total_ingresos / Decimal(total_ventas), 2) if total_ventas > 0 else Decimal("0.00")
 
        return VentasHoyResponse(
            fecha=today,
            total_ventas=total_ventas,
            total_ingresos=total_ingresos,
            ticket_promedio=ticket_promedio,
        )
    except Exception as e:
        logger.error(f"Error al calcular ventas de hoy: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar reporte de ventas de hoy: {str(e)}",
        )
 
 
@app.get("/api/v1/reportes/productos-top", response_model=List[ProductoTopItem], tags=["Reportes"])
def get_productos_top(limite: int = Query(5, ge=1, le=50), db: Session = Depends(get_db)):
    """
    Retorna el ranking de productos más vendidos en volumen y recaudación.
    Diseñado para consumir agregaciones procesadas por Apache Spark en etapas avanzadas.
    """
    try:
        sql = text("""
            SELECT 
                p.id AS product_id,
                p.name AS product_name,
                COALESCE(SUM(si.quantity), 0) AS unidades_vendidas,
                COALESCE(SUM(si.subtotal), 0) AS total_recaudado
            FROM products p
            INNER JOIN sale_items si ON p.id = si.product_id
            GROUP BY p.id, p.name
            ORDER BY unidades_vendidas DESC, total_recaudado DESC
            LIMIT :limite
        """)
        rows = db.execute(sql, {"limite": limite}).fetchall()
 
        ranking = []
        for idx, row in enumerate(rows, start=1):
            ranking.append(
                ProductoTopItem(
                    ranking=idx,
                    product_id=row[0],
                    product_name=row[1],
                    unidades_vendidas=int(row[2]),
                    total_recaudado=Decimal(str(row[3])),
                )
            )
        return ranking
    except Exception as e:
        logger.error(f"Error al calcular productos top: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al generar ranking de productos: {str(e)}",
        )
 
 
@app.get("/api/v1/reportes/ventas-agrupadas-dia", response_model=List[VentaDiaItem], tags=["Reportes"])
def get_ventas_agrupadas_dia(dias: int = Query(7, ge=1, le=90), db: Session = Depends(get_db)):
    """
    Retorna las ventas agrupadas por día para los últimos N días.
    """
    try:
        start_date = date.today() - timedelta(days=dias)
        sql = text("""
            SELECT 
                DATE(created_at) AS fecha_dia,
                COUNT(id) AS numero_ventas,
                COALESCE(SUM(total), 0) AS total_ingresos
            FROM sales
            WHERE DATE(created_at) >= :start_date
            GROUP BY DATE(created_at)
            ORDER BY fecha_dia ASC
        """)
        rows = db.execute(sql, {"start_date": start_date}).fetchall()
 
        return [
            VentaDiaItem(
                fecha=str(row[0]),
                numero_ventas=int(row[1]),
                total_ingresos=Decimal(str(row[2])),
            )
            for row in rows
        ]
    except Exception as e:
        logger.error(f"Error al agrupar ventas por día: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al agrupar ventas diarias: {str(e)}",
        )
 
 
@app.get("/api/v1/reportes/resumen-general", response_model=ResumenGeneralResponse, tags=["Reportes"])
def get_resumen_general(db: Session = Depends(get_db)):
    """Estadísticas acumuladas generales del negocio."""
    try:
        sql_sales = text("SELECT COUNT(id), COALESCE(SUM(total), 0) FROM sales")
        sales_row = db.execute(sql_sales).fetchone()
 
        sql_prods = text("SELECT COUNT(id) FROM products")
        prods_row = db.execute(sql_prods).fetchone()
 
        total_ventas = int(sales_row[0]) if sales_row and sales_row[0] is not None else 0
        ingresos_totales = Decimal(str(sales_row[1])) if sales_row and sales_row[1] is not None else Decimal("0.00")
        total_prods = int(prods_row[0]) if prods_row and prods_row[0] is not None else 0
 
        return ResumenGeneralResponse(
            total_ventas_historicas=total_ventas,
            ingresos_totales_historicos=ingresos_totales,
            total_productos_activos=total_prods,
        )
    except Exception as e:
        logger.error(f"Error en resumen general: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resumen general: {str(e)}",
        )
 
 
@app.get("/api/v1/reportes/spark", response_model=SparkResultadosResponse, tags=["Reportes"])
def get_resultados_spark(
    limite: int = Query(10, ge=1, le=50),
    dias: int = Query(30, ge=1, le=365),
    db: Session = Depends(get_db),
):
    """
    Retorna los resultados del último procesamiento distribuido con Apache Spark
    (ventas por día, productos más vendidos y resumen general), leídos de las
    tablas agg_* donde el job los persiste.
 
    Si el job aún no se ha ejecutado, responde 200 con `disponible: false`.
    """
    try:
        resumen_row = db.execute(
            text(
                "SELECT total_ventas, ingresos_totales, total_productos, procesado_en "
                "FROM agg_resumen_general WHERE id = 1"
            )
        ).fetchone()
 
        if resumen_row is None:
            return SparkResultadosResponse(disponible=False)
 
        top_rows = db.execute(
            text(
                "SELECT ranking, product_id, product_name, unidades_vendidas, total_recaudado "
                "FROM agg_productos_top ORDER BY ranking ASC LIMIT :limite"
            ),
            {"limite": limite},
        ).fetchall()
 
        # Últimos N días con datos, devueltos en orden cronológico
        dias_rows = db.execute(
            text(
                "SELECT fecha, numero_ventas, total_ingresos FROM ("
                "  SELECT fecha, numero_ventas, total_ingresos "
                "  FROM agg_ventas_diarias ORDER BY fecha DESC LIMIT :dias"
                ") ultimos ORDER BY fecha ASC"
            ),
            {"dias": dias},
        ).fetchall()
 
        return SparkResultadosResponse(
            disponible=True,
            procesado_en=resumen_row[3],
            resumen=SparkResumen(
                total_ventas=int(resumen_row[0]),
                ingresos_totales=Decimal(str(resumen_row[1])),
                total_productos=int(resumen_row[2]),
            ),
            productos_top=[
                ProductoTopItem(
                    ranking=int(r[0]),
                    product_id=int(r[1]),
                    product_name=r[2],
                    unidades_vendidas=int(r[3]),
                    total_recaudado=Decimal(str(r[4])),
                )
                for r in top_rows
            ],
            ventas_por_dia=[
                VentaDiaItem(
                    fecha=str(r[0]),
                    numero_ventas=int(r[1]),
                    total_ingresos=Decimal(str(r[2])),
                )
                for r in dias_rows
            ],
        )
    except Exception as e:
        logger.error(f"Error al leer resultados de Spark: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener los resultados de Spark. Verifica que la migración 002 esté aplicada.",
        )
 