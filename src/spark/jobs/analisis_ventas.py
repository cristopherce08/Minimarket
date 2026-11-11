"""
analisis_ventas.py
-------------------
Job PySpark — Procesamiento Distribuido de Ventas (Req. 4, 6, 7, 8)
MiniMarket Cloud | Integrante 3 — Datos y Procesamiento Distribuido

Qué hace este job:
  1. Lee las tablas transaccionales (sales, sale_items, products) desde PostgreSQL.
  2. Calcula con PySpark (múltiples ejecutores):
       a) Ventas agrupadas por día  → spark_ventas_por_dia
       b) Ranking de productos top  → spark_productos_top
       c) Resumen general           → spark_resumen_general
  3. Guarda los resultados de vuelta en PostgreSQL para que la reportes-api los exponga.

Ejecución local (modo standalone):
    python analisis_ventas.py

Ejecución con múltiples workers Spark:
    spark-submit --master spark://spark-master:7077 \\
                 --num-executors 2 \\
                 --executor-cores 1 \\
                 --jars /opt/spark/jars/postgresql-42.7.3.jar \\
                 analisis_ventas.py

Variables de entorno:
    DATABASE_URL   URL de conexión a PostgreSQL
    SPARK_MASTER   URL del master Spark (default: local[*])
"""

import os
import logging
from datetime import datetime, timezone
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, DecimalType, TimestampType

# ---------------------------------------------------------------------------
# Configuración
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("analisis_ventas_spark")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://minimarket_user:minimarket_password@localhost:5433/minimarket_db",
)
SPARK_MASTER = os.getenv("SPARK_MASTER", "local[*]")

# Convertir URL SQLAlchemy → JDBC (Spark usa formato JDBC)
# De: postgresql://user:pass@host:port/db
# A:  jdbc:postgresql://host:port/db
def sqlalchemy_url_a_jdbc(url: str) -> tuple[str, str, str]:
    """Convierte DATABASE_URL al formato JDBC y extrae credenciales."""
    # Remover el prefijo de driver
    clean = url.replace("postgresql+psycopg://", "").replace("postgresql://", "")
    # Separar credenciales de host
    creds, rest = clean.split("@", 1)
    user, password = creds.split(":", 1)
    jdbc_url = f"jdbc:postgresql://{rest}"
    return jdbc_url, user, password


JDBC_URL, DB_USER, DB_PASS = sqlalchemy_url_a_jdbc(DATABASE_URL)
JDBC_DRIVER  = "org.postgresql.Driver"
JDBC_JAR     = "/opt/spark/jars/postgresql-42.7.3.jar"

FECHA_PROCESO = datetime.now(timezone.utc)

# ---------------------------------------------------------------------------
# Inicializar SparkSession
# ---------------------------------------------------------------------------
def crear_spark_session() -> SparkSession:
    logger.info(f"Iniciando SparkSession — master: {SPARK_MASTER}")
    spark = (
        SparkSession.builder
        .appName("MiniMarket-AnalisisVentas")
        .master(SPARK_MASTER)
        .config("spark.jars", JDBC_JAR)
        .config("spark.sql.shuffle.partitions", "4")
        .config("spark.executor.memory", "512m")
        .config("spark.driver.memory", "512m")
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
    logger.info(f"SparkSession activa — versión: {spark.version}")
    return spark


# ---------------------------------------------------------------------------
# Lectura desde PostgreSQL
# ---------------------------------------------------------------------------
def leer_tabla(spark: SparkSession, tabla: str):
    """Lee una tabla PostgreSQL como DataFrame de Spark via JDBC."""
    logger.info(f"Leyendo tabla: {tabla}")
    return (
        spark.read
        .format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", tabla)
        .option("user", DB_USER)
        .option("password", DB_PASS)
        .option("driver", JDBC_DRIVER)
        .option("fetchsize", "1000")
        .load()
    )


# ---------------------------------------------------------------------------
# Escritura hacia PostgreSQL
# ---------------------------------------------------------------------------
def escribir_tabla(df, tabla: str, modo: str = "overwrite"):
    """Escribe un DataFrame de Spark de vuelta a PostgreSQL."""
    logger.info(f"Escribiendo resultados → tabla: {tabla} (modo: {modo})")
    (
        df.write
        .format("jdbc")
        .option("url", JDBC_URL)
        .option("dbtable", tabla)
        .option("user", DB_USER)
        .option("password", DB_PASS)
        .option("driver", JDBC_DRIVER)
        .option("batchsize", "500")
        .mode(modo)
        .save()
    )
    logger.info(f"  ✅ {tabla} guardada. Registros: {df.count()}")


# ---------------------------------------------------------------------------
# Transformaciones PySpark
# ---------------------------------------------------------------------------
def calcular_ventas_por_dia(df_sales):
    """
    Req. 6a: Agrupa ventas por fecha, conta transacciones e ingresos totales.
    Resultado: fecha_dia | numero_ventas | total_ingresos | ticket_promedio
    """
    logger.info("Calculando: ventas agrupadas por día...")
    return (
        df_sales
        .withColumn("fecha_dia", F.to_date(F.col("created_at")))
        .groupBy("fecha_dia")
        .agg(
            F.count("id").alias("numero_ventas"),
            F.round(F.sum("total"), 2).alias("total_ingresos"),
        )
        .withColumn(
            "ticket_promedio",
            F.round(F.col("total_ingresos") / F.col("numero_ventas"), 2),
        )
        .withColumn("fecha_proceso", F.lit(FECHA_PROCESO))
        .orderBy("fecha_dia")
    )


def calcular_productos_top(df_sale_items, df_products):
    """
    Req. 6c: Ranking de productos más vendidos por unidades y recaudación.
    Resultado: ranking | product_id | product_name | unidades_vendidas | total_recaudado
    """
    logger.info("Calculando: ranking de productos más vendidos...")
    df_joined = df_sale_items.join(df_products, df_sale_items.product_id == df_products.id, "inner")

    df_agg = (
        df_joined
        .groupBy(df_products.id.alias("product_id"), df_products.name.alias("product_name"))
        .agg(
            F.sum("quantity").cast("integer").alias("unidades_vendidas"),
            F.round(F.sum("subtotal"), 2).alias("total_recaudado"),
        )
        .orderBy(F.desc("unidades_vendidas"), F.desc("total_recaudado"))
    )

    # Agregar columna de ranking con window function
    from pyspark.sql.window import Window
    window_rank = Window.orderBy(F.desc("unidades_vendidas"), F.desc("total_recaudado"))

    return (
        df_agg
        .withColumn("ranking", F.rank().over(window_rank))
        .withColumn("fecha_proceso", F.lit(FECHA_PROCESO))
        .select("ranking", "product_id", "product_name", "unidades_vendidas", "total_recaudado", "fecha_proceso")
    )


def calcular_resumen_general(df_sales, df_sale_items, df_products):
    """
    Req. 6b: Resumen global del período procesado.
    Resultado: fecha_proceso | total_ventas | ingresos_totales | total_items | producto_mas_vendido
    """
    logger.info("Calculando: resumen general...")

    total_ventas    = df_sales.count()
    ingresos_tot    = df_sales.agg(F.round(F.sum("total"), 2)).collect()[0][0] or 0.0
    total_items     = df_sale_items.agg(F.sum("quantity")).collect()[0][0] or 0

    # Producto más vendido
    df_top = (
        df_sale_items
        .join(df_products, df_sale_items.product_id == df_products.id)
        .groupBy(df_products.name.alias("product_name"))
        .agg(F.sum("quantity").alias("total_vendido"))
        .orderBy(F.desc("total_vendido"))
        .limit(1)
    )
    top_product = df_top.collect()
    producto_mas_vendido = top_product[0]["product_name"] if top_product else "N/A"

    # Crear DataFrame de una sola fila
    from pyspark.sql import Row
    spark = df_sales.sparkSession
    resumen_row = Row(
        fecha_proceso=FECHA_PROCESO,
        total_ventas=int(total_ventas),
        ingresos_totales=float(ingresos_tot),
        total_items_vendidos=int(total_items),
        producto_mas_vendido=producto_mas_vendido,
    )
    return spark.createDataFrame([resumen_row])


# ---------------------------------------------------------------------------
# Pipeline principal
# ---------------------------------------------------------------------------
def main():
    logger.info("=" * 60)
    logger.info("  MiniMarket Cloud — Job PySpark: Análisis de Ventas")
    logger.info("=" * 60)
    logger.info(f"JDBC URL   : {JDBC_URL}")
    logger.info(f"Spark Master: {SPARK_MASTER}")
    logger.info(f"Fecha proc : {FECHA_PROCESO.isoformat()}")

    spark = crear_spark_session()

    try:
        # 1. Leer tablas transaccionales
        df_sales      = leer_tabla(spark, "sales")
        df_sale_items = leer_tabla(spark, "sale_items")
        df_products   = leer_tabla(spark, "products")

        total_ventas = df_sales.count()
        logger.info(f"\n📥 Datos leídos:")
        logger.info(f"   sales      → {total_ventas} registros")
        logger.info(f"   sale_items → {df_sale_items.count()} registros")
        logger.info(f"   products   → {df_products.count()} registros")

        if total_ventas == 0:
            logger.warning("⚠️  No hay ventas en la BD. Ejecuta primero generar_ventas_simuladas.py")
            return

        # 2. Calcular agregaciones con PySpark
        df_por_dia  = calcular_ventas_por_dia(df_sales)
        df_top_prod = calcular_productos_top(df_sale_items, df_products)
        df_resumen  = calcular_resumen_general(df_sales, df_sale_items, df_products)

        # 3. Guardar resultados en PostgreSQL (Req. 7)
        logger.info("\n📤 Guardando resultados en PostgreSQL...")
        escribir_tabla(df_por_dia,  "spark_ventas_por_dia")
        escribir_tabla(df_top_prod, "spark_productos_top")
        escribir_tabla(df_resumen,  "spark_resumen_general")

        # 4. Mostrar resumen en consola
        logger.info("\n" + "=" * 60)
        logger.info("  RESULTADOS DEL PROCESAMIENTO SPARK")
        logger.info("=" * 60)

        logger.info("\n📅 Ventas por día (últimos 5 días):")
        df_por_dia.orderBy(F.desc("fecha_dia")).show(5, truncate=False)

        logger.info("\n🏆 Top 5 productos más vendidos:")
        df_top_prod.show(5, truncate=False)

        logger.info("\n📊 Resumen general:")
        df_resumen.show(truncate=False)

        logger.info("✅ Job completado exitosamente.")

    except Exception as e:
        logger.exception(f"❌ Error en el job Spark: {e}")
        raise
    finally:
        spark.stop()
        logger.info("SparkSession cerrada.")


if __name__ == "__main__":
    main()
