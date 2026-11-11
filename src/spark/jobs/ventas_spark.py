"""
MiniMarket Cloud - Job PySpark: procesamiento distribuido de ventas simuladas.
 
Flujo:
  1. Lee el catalogo real (tabla products) desde PostgreSQL por JDBC.
  2. Genera NUM_VENTAS ventas simuladas de forma distribuida (spark.range).
  3. Calcula ventas por dia, ingresos totales y productos mas vendidos.
  4. Guarda los resultados en PostgreSQL (tablas agg_*).
 
Variables de entorno:
  JDBC_URL, DB_USER, DB_PASSWORD   (obligatorias)
  NUM_VENTAS (200000), NUM_PARTICIONES (8), DIAS (30), TOP_N (10), SEED (42)
  ESPERA_FINAL (90): segundos que se mantienen vivos los ejecutores al terminar,
                     para poder capturar evidencia (kubectl get pods / Spark UI).
"""
import os
import time
from collections import Counter
 
from pyspark import StorageLevel
from pyspark.sql import SparkSession, Window
from pyspark.sql import functions as F
from pyspark.sql.types import DecimalType, IntegerType, LongType
 
NUM_VENTAS = int(os.getenv("NUM_VENTAS", "200000"))
NUM_PARTICIONES = int(os.getenv("NUM_PARTICIONES", "8"))
DIAS = int(os.getenv("DIAS", "30"))
TOP_N = int(os.getenv("TOP_N", "10"))
SEED = int(os.getenv("SEED", "42"))
ESPERA_FINAL = int(os.getenv("ESPERA_FINAL", "90"))
 
MONEDA = DecimalType(16, 2)
 
 
def generar_ventas(spark, catalogo, num_ventas, num_particiones, dias, seed):
    """Genera ventas simuladas de forma distribuida.
 
    catalogo: DataFrame con columnas id, name, price.
    Cada fila es una venta de un producto del catalogo, con cantidad 1-5 y una
    fecha aleatoria dentro de los ultimos `dias` dias (fecha de Lima).
    """
    productos = catalogo.select(
        F.col("id").alias("product_id"),
        F.col("name").alias("product_name"),
        F.col("price").alias("unit_price"),
    )
    productos = productos.withColumn(
        "idx", F.row_number().over(Window.orderBy("product_id")) - 1
    )
    n_productos = productos.count()
    if n_productos == 0:
        raise ValueError("El catalogo de productos esta vacio. Ejecuta primero el seed.")
 
    base = (
        spark.range(num_ventas, numPartitions=num_particiones)
        .withColumnRenamed("id", "sale_id")
        .withColumn("idx", F.floor(F.rand(seed) * n_productos).cast("long"))
        .withColumn("quantity", (F.floor(F.rand(seed + 1) * 5) + 1).cast("int"))
        .withColumn("dia_offset", F.floor(F.rand(seed + 2) * dias).cast("int"))
    )
 
    hoy_lima = F.to_date(F.from_utc_timestamp(F.current_timestamp(), "America/Lima"))
    return (
        base.join(F.broadcast(productos), "idx")
        .withColumn("fecha", F.date_sub(hoy_lima, F.col("dia_offset")))
        .withColumn("subtotal", (F.col("unit_price") * F.col("quantity")).cast(MONEDA))
        .select(
            "sale_id", "fecha", "product_id", "product_name",
            "quantity", "unit_price", "subtotal",
        )
    )
 
 
def calcular_agregados(ventas, top_n):
    """Devuelve (ventas_por_dia, productos_top, resumen_general)."""
    ventas_por_dia = (
        ventas.groupBy("fecha")
        .agg(
            F.count("sale_id").cast(LongType()).alias("numero_ventas"),
            F.sum("subtotal").cast(MONEDA).alias("total_ingresos"),
        )
        .orderBy("fecha")
    )
 
    por_producto = ventas.groupBy("product_id", "product_name").agg(
        F.sum("quantity").cast(LongType()).alias("unidades_vendidas"),
        F.sum("subtotal").cast(MONEDA).alias("total_recaudado"),
    )
    orden = Window.orderBy(F.col("unidades_vendidas").desc(), F.col("product_id"))
    productos_top = (
        por_producto.withColumn("ranking", F.row_number().over(orden).cast(IntegerType()))
        .filter(F.col("ranking") <= top_n)
        .select("ranking", "product_id", "product_name", "unidades_vendidas", "total_recaudado")
    )
 
    resumen = ventas.agg(
        F.count("sale_id").cast(LongType()).alias("total_ventas"),
        F.sum("subtotal").cast(MONEDA).alias("ingresos_totales"),
        F.countDistinct("product_id").cast(IntegerType()).alias("total_productos"),
    ).select(
        F.lit(1).alias("id"), "total_ventas", "ingresos_totales", "total_productos"
    )
    return ventas_por_dia, productos_top, resumen
 
 
def filas_por_ejecutor(ventas):
    """Evidencia de distribucion: cuantas filas proceso cada ejecutor (pod)."""
 
    def contar_filas_por_host(filas):
        import socket
 
        yield (socket.gethostname(), sum(1 for _ in filas))
 
    conteo = Counter()
    for host, n in ventas.rdd.mapPartitions(contar_filas_por_host).collect():
        conteo[host] += n
    return conteo
 
 
def _opciones_jdbc(url, usuario, clave):
    return {
        "url": url,
        "user": usuario,
        "password": clave,
        "driver": "org.postgresql.Driver",
    }
 
 
def guardar(df, tabla, opciones):
    (
        df.write.format("jdbc")
        .options(**opciones)
        .option("dbtable", tabla)
        .option("truncate", "true")  # conserva el esquema creado por Alembic
        .mode("overwrite")
        .save()
    )
 
 
def main():
    url = os.environ["JDBC_URL"]
    opciones = _opciones_jdbc(url, os.environ["DB_USER"], os.environ["DB_PASSWORD"])
 
    spark = (
        SparkSession.builder.appName("minimarket-ventas-spark")
        .config("spark.sql.shuffle.partitions", str(NUM_PARTICIONES))
        .getOrCreate()
    )
    spark.sparkContext.setLogLevel("WARN")
 
    print("=" * 70, flush=True)
    print("MINIMARKET CLOUD - Procesamiento distribuido con Apache Spark", flush=True)
    print(f"Spark {spark.version} | ventas simuladas: {NUM_VENTAS} | "
          f"particiones: {NUM_PARTICIONES} | dias: {DIAS}", flush=True)
    print("=" * 70, flush=True)
 
    catalogo = (
        spark.read.format("jdbc").options(**opciones).option("dbtable", "products").load()
        .select("id", "name", "price")
    )
 
    ventas = generar_ventas(spark, catalogo, NUM_VENTAS, NUM_PARTICIONES, DIAS, SEED)
    ventas = ventas.persist(StorageLevel.MEMORY_AND_DISK)
 
    reparto = filas_por_ejecutor(ventas)
    print("\nReparto del trabajo por ejecutor:", flush=True)
    for host, n in sorted(reparto.items()):
        print(f"  - {host}: {n} filas", flush=True)
    print(f"Ejecutores distintos que procesaron datos: {len(reparto)}", flush=True)
 
    ventas_por_dia, productos_top, resumen = calcular_agregados(ventas, TOP_N)
 
    print("\nVentas por dia (ultimos 5 dias):", flush=True)
    ventas_por_dia.orderBy(F.col("fecha").desc()).show(5, truncate=False)
    print("Productos mas vendidos:", flush=True)
    productos_top.show(TOP_N, truncate=False)
    print("Resumen general:", flush=True)
    resumen.show(truncate=False)
 
    guardar(ventas_por_dia, "agg_ventas_diarias", opciones)
    guardar(productos_top, "agg_productos_top", opciones)
    guardar(resumen, "agg_resumen_general", opciones)
    print("Resultados guardados en PostgreSQL: agg_ventas_diarias, "
          "agg_productos_top, agg_resumen_general", flush=True)
 
    if ESPERA_FINAL > 0:
        print(f"Manteniendo ejecutores {ESPERA_FINAL}s para capturar evidencia...", flush=True)
        time.sleep(ESPERA_FINAL)
 
    ventas.unpersist()
    spark.stop()
 
 
if __name__ == "__main__":
    main()
 