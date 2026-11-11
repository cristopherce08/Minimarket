# Dockerfile — Spark Job Runner (Entorno local y pruebas)
# MiniMarket Cloud | Integrante 3 — Datos y Procesamiento Distribuido
#
# Imagen multi-etapa basada en Python 3.11 + PySpark 3.5
# Compatible con arquitecturas AMD64 y Apple Silicon ARM64.
# Incluye el driver JDBC de PostgreSQL para conectar Spark con la BD.

FROM python:3.11-slim-bookworm AS base

# Dependencias del sistema operativo (Java es obligatorio para Spark)
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        curl \
        wget \
    && rm -rf /var/lib/apt/lists/* \
    && JAVA_DIR=$(find /usr/lib/jvm -maxdepth 1 -name "java-17-openjdk*" | head -n 1) \
    && ln -s "$JAVA_DIR" /usr/lib/jvm/java-17-openjdk-current

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-current
ENV PATH="$JAVA_HOME/bin:$PATH"

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Descargar driver JDBC de PostgreSQL
RUN mkdir -p /opt/spark/jars && \
    wget -q https://jdbc.postgresql.org/download/postgresql-42.7.3.jar \
         -O /opt/spark/jars/postgresql-42.7.3.jar

# Copiar los jobs
COPY jobs/ ./jobs/

# Variables de entorno por defecto (sin credenciales incrustadas)
ENV SPARK_MASTER="local[*]"
ENV PYTHONUNBUFFERED=1

# El job por defecto a ejecutar
CMD ["python", "jobs/analisis_ventas.py"]
