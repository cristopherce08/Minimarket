"""
generar_ventas_simuladas.py
----------------------------
Script de generación de datos sintéticos de ventas para MiniMarket Cloud.
Propósito (Req. 5): Poblar la base de datos con suficientes ventas históricas
para que el job PySpark tenga datos significativos que procesar.

Genera: ~500 ventas distribuidas en los últimos 30 días, con múltiples items
por venta, usando los productos reales del catálogo de la BD.

Ejecución:
    python generar_ventas_simuladas.py

Variables de entorno requeridas:
    DATABASE_URL  (ej: postgresql://user:pass@localhost:5433/minimarket_db)
"""

import os
import random
import logging
from decimal import Decimal
from datetime import datetime, timezone, timedelta
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("generar_ventas_simuladas")

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("Variable de entorno DATABASE_URL no configurada para generar_ventas_simuladas.")

NUM_VENTAS      = 500   # Total de ventas a generar
MAX_ITEMS_VENTA = 5     # Máximo de productos distintos por venta
DIAS_HISTORICO  = 30    # Rango de días hacia atrás para distribuir las ventas

# ---------------------------------------------------------------------------
# Conexión
# ---------------------------------------------------------------------------
engine  = create_engine(DATABASE_URL, echo=False)
Session = sessionmaker(bind=engine)


def obtener_productos(session) -> list[dict]:
    """Devuelve la lista de productos disponibles (stock > 0)."""
    rows = session.execute(
        text("SELECT id, name, price FROM products WHERE stock > 0 ORDER BY id")
    ).fetchall()
    return [{"id": r[0], "name": r[1], "price": Decimal(str(r[2]))} for r in rows]


def generar_fecha_aleatoria() -> datetime:
    """Genera un datetime aleatorio dentro del rango de DIAS_HISTORICO hacia atrás."""
    dias_atras = random.randint(0, DIAS_HISTORICO)
    hora       = random.randint(7, 21)   # Horario comercial 07:00–21:00
    minuto     = random.randint(0, 59)
    segundo    = random.randint(0, 59)
    base       = datetime.now(timezone.utc) - timedelta(days=dias_atras)
    return base.replace(hour=hora, minute=minuto, second=segundo, microsecond=0)


def insertar_venta(session, productos: list[dict]) -> bool:
    """Inserta una venta con 1–MAX_ITEMS_VENTA productos aleatorios."""
    if not productos:
        return False

    num_items       = random.randint(1, min(MAX_ITEMS_VENTA, len(productos)))
    items_elegidos  = random.sample(productos, num_items)
    fecha_venta     = generar_fecha_aleatoria()

    total_venta = Decimal("0.00")
    items_data  = []

    for prod in items_elegidos:
        cantidad  = random.randint(1, 5)
        subtotal  = prod["price"] * cantidad
        total_venta += subtotal
        items_data.append({
            "product_id": prod["id"],
            "quantity":   cantidad,
            "unit_price": prod["price"],
            "subtotal":   subtotal,
        })

    # Insertar cabecera de venta
    result = session.execute(
        text(
            "INSERT INTO sales (total, created_at) "
            "VALUES (:total, :created_at) RETURNING id"
        ),
        {"total": total_venta, "created_at": fecha_venta},
    )
    sale_id = result.fetchone()[0]

    # Insertar ítems
    for item in items_data:
        session.execute(
            text(
                "INSERT INTO sale_items (sale_id, product_id, quantity, unit_price, subtotal) "
                "VALUES (:sale_id, :product_id, :quantity, :unit_price, :subtotal)"
            ),
            {**item, "sale_id": sale_id},
        )

    return True


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("  MiniMarket Cloud — Generador de Ventas Simuladas")
    logger.info("=" * 60)
    logger.info(f"Destino DB : {DATABASE_URL.split('@')[-1]}")
    logger.info(f"Ventas a generar: {NUM_VENTAS}  |  Rango: {DIAS_HISTORICO} días")

    session = Session()
    try:
        productos = obtener_productos(session)
        if not productos:
            logger.error("No hay productos en la BD. Ejecuta primero la API para que el seed corra.")
            return

        logger.info(f"Productos disponibles en catálogo: {len(productos)}")

        generadas = 0
        for i in range(1, NUM_VENTAS + 1):
            insertar_venta(session, productos)
            generadas += 1
            if i % 50 == 0:
                session.commit()
                logger.info(f"  → {i}/{NUM_VENTAS} ventas insertadas...")

        session.commit()
        logger.info(f"\n✅ Listo. {generadas} ventas simuladas generadas exitosamente.")

        # Verificación rápida
        total_en_bd = session.execute(text("SELECT COUNT(*) FROM sales")).scalar()
        logger.info(f"📊 Total de ventas en la BD ahora: {total_en_bd}")

    except Exception as e:
        session.rollback()
        logger.exception(f"❌ Error al generar ventas: {e}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
