# Dockerfile — Spark Job Runner
# MiniMarket Cloud | Integrante 3 — Datos y Procesamiento Distribuido
#
# Imagen multi-etapa basada en Python 3.11 + PySpark 3.5
# Incluye el driver JDBC de PostgreSQL para conectar Spark con la BD.

FROM python:3.11-slim-bookworm AS base

# Dependencias del sistema operativo (Java es obligatorio para Spark)
RUN apt-get update && apt-get install -y --no-install-recommends \
        openjdk-17-jre-headless \
        curl \
        wget \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV PATH="$JAVA_HOME/bin:$PATH"

WORKDIR /app

# Instalar dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Descargar driver JDBC de PostgreSQL (requerido por Spark para leer/escribir en PG)
RUN mkdir -p /opt/spark/jars && \
    wget -q https://jdbc.postgresql.org/download/postgresql-42.7.3.jar \
         -O /opt/spark/jars/postgresql-42.7.3.jar

# Copiar los jobs
COPY jobs/ ./jobs/

# Variables de entorno por defecto (sobreescribibles en docker-compose)
ENV DATABASE_URL="postgresql://minimarket_user:minimarket_password@postgres:5432/minimarket_db"
ENV SPARK_MASTER="local[*]"
ENV PYTHONUNBUFFERED=1

# El job por defecto a ejecutar (se puede sobreescribir con CMD en compose)
CMD ["python", "jobs/analisis_ventas.py"]
