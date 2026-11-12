# Guía de Sustentación para Evaluación (Criterio 3: Datos y Spark)

## 1. Puntos Clave de la Rúbrica Evaluada

- **Persistencia en PostgreSQL**:
  - Almacenamiento en PVC `postgres-pvc` con StorageClass `standard` dinámica en Minikube.
  - Esquema versionado con Alembic (`001_initial_schema` y `002_agregados_spark`).
- **Procesamiento Distribuido con Apache Spark**:
  - Ejecución en Kubernetes con 1 Driver y 2 Ejecutores reales.
  - 8 particiones distribuidas procesando 200,000 ventas simuladas.
  - Registro de evidencias del reparto de filas por pod ejecutor.
- **Seguridad y Aislamiento**:
  - Cero contraseñas hardcodeadas en Dockerfiles, scripts o YAMLs.
  - Uso exclusivo del Secret `backend-db-secret`.
  - Calico NetworkPolicy habilitando únicamente pods con `app: spark-job`.
- **Integración con Reportes y Frontend**:
  - Endpoint `/api/v1/reportes/spark` tolerante a fallos (HTTP 200 con `disponible: false` si las tablas aún no se han procesado).
  - Dashboard de visualización en el frontend.

---

## 2. Secuencia de Comprobación en Vivo frente al Docente

### Paso 1: Demostrar Persistencia de PostgreSQL
```bash
# Verificar StorageClass y PVC en Kubernetes
kubectl get sc
kubectl get pvc -n minimarket-data
kubectl get pv
```

### Paso 2: Demostrar Migraciones Alembic
```bash
# Verificar el historial de versiones de la base de datos
alembic -c src/ventas-api/alembic.ini current
```

### Paso 3: Demostrar el Job Distribuido de Spark
```bash
# 1. Aplicar RBAC y Job
kubectl apply -f src/spark/k8s/spark-rbac.yaml
kubectl apply -f src/spark/k8s/spark-job.yaml

# 2. Mostrar la presencia de 1 Driver y 2 Ejecutores activos
kubectl get pods -n minimarket-backend -l app=spark-job

# 3. Mostrar la evidencia en los logs del reparto por ejecutor
kubectl logs -n minimarket-backend job/ventas-spark | grep -A 10 "Reparto del trabajo por ejecutor:"
```

### Paso 4: Demostrar la API de Reportes y el Frontend
```bash
# Consultar endpoint de analítica
curl -s http://localhost:8001/api/v1/reportes/spark | jq .

# Abrir el frontend en el navegador y verificar la tarjeta:
# "⚡ Análisis Distribuido con Apache Spark"
```
