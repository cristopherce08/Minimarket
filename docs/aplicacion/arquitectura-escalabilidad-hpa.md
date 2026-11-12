# Arquitectura de la API Escalable y Horizontal Pod Autoscaler (HPA)
## MiniMarket Cloud — Integrante 2 (Aplicación y Escalabilidad)

---

## 1. Visión General del Microservicio `ventas-api`

`ventas-api` es el microservicio transaccional central de MiniMarket Cloud. Implementado con **FastAPI (Python 3.12)** y **SQLAlchemy 2.0 / Psycopg 3**, gestiona el catálogo de productos, el inventario en tiempo real y el procesamiento de ventas atómicas con estricto apego a las propiedades **ACID** sobre **PostgreSQL 16**.

### Características de Diseño Cloud Native

1. **Arquitectura Sin Estado (Stateless):**  
   Los pods no almacenan estado de sesión en memoria local. Cada solicitud HTTP es autocontenida y transacciona directamente con PostgreSQL, permitiendo que el tráfico sea distribuido equitativamente entre cualquier cantidad de réplicas sin afinidad de sesión (*session affinity*).

2. **Control de Concurrencia y Cero Sobreventa:**  
   Para impedir la sobreventa (*overselling*) cuando múltiples réplicas procesan compras simultáneas del mismo producto con stock limitado:
   - **Bloqueo Pesimista por Fila (`SELECT ... FOR UPDATE`):** Se bloquean las filas de los productos solicitados en orden ascendente por `id` (`ORDER BY id ASC`), eliminando el riesgo de interbloqueos (*deadlocks*).
   - **Actualización Condicional Atómica:** `UPDATE products SET stock = stock - qty WHERE id = :id AND stock >= :qty`. Si el stock fue consumido por otra transacción simultánea, `rowcount == 0` y la transacción se aborta con `ROLLBACK` total y código de estado `HTTP 400 Bad Request`.
   - **Captura de Precio Histórico:** Cada ítem vendido almacena el precio unitario exacto al momento de la confirmación (`unit_price`), garantizando trazabilidad contable inmutable.

3. **Pool de Conexiones Calibrado para `max_connections=100`:**  
   Se calibró el pool de SQLAlchemy (`pool_size=5`, `max_overflow=5`, `pool_recycle=1800`, `pool_timeout=30`, `pool_pre_ping=True`) parametrizado vía variables de entorno (`DB_POOL_SIZE`, `DB_MAX_OVERFLOW`).  
   - Con 5 réplicas HPA máximas: `5 pods * (5 pool + 5 overflow) = 50 conexiones máximas`.  
   - Deja 50 conexiones libres en PostgreSQL para `reportes-api` (10), PySpark JDBC (20) y conexiones administrativas/probes Kubelet (20), garantizando que nunca se sature el límite global de 100 conexiones.

4. **Apagado Ordenado (*Graceful Shutdown*):**  
   - En el despliegue de Kubernetes se configuró `terminationGracePeriodSeconds: 30`.
   - En el `lifespan` de FastAPI, al recibir la señal `SIGTERM`, la aplicación detiene la recepción de nuevas solicitudes y ejecuta `engine.dispose()`, permitiendo que las transacciones SQL activas culminen limpiamente antes de cerrar los descriptores de red.

---

## 2. Configuración del Horizontal Pod Autoscaler (HPA)

El autoescalado horizontal se implementa mediante la especificación moderna **`autoscaling/v2`** de Kubernetes, empaquetado y configurable dentro del Helm Chart (`infra/helm/minimarket`).

### Parámetros Operativos

- **Métrica Principal:** Utilización promedio de CPU (`Resource: cpu`, `Target: Utilization`).
- **Umbral de Disparo Configurable:** `25%` (o `50%` según el entorno).
- **Rango de Réplicas:** Mínimo `2` pods, Máximo `5` pods.
- **Políticas de Comportamiento (*Behavior*):**
  - **Escala Ascendente (*Scale Up*):**
    - `stabilizationWindowSeconds: 0`: Reacción inmediata ante picos de demanda.
    - `selectPolicy: Max`: Selecciona el mayor incremento entre duplicar réplicas (+100%) o sumar 2 pods cada 15 segundos.
  - **Escala Descendente (*Scale Down*):**
    - `stabilizationWindowSeconds: 60`: Ventana de estabilización de 60 segundos para evitar fluctuaciones rápidas (*flapping / thrashing*).
    - `selectPolicy: Min`: Reducción conservadora para preservar disponibilidad.

### Coordinación Helm sin Conflictos de Réplicas

Cuando autoscaling está activado (`autoscaling.enabled: true`), el template `ventas-api-deployment.yaml` omite la propiedad `spec.replicas`:

```yaml
spec:
  {{- if not .Values.ventasApi.autoscaling.enabled }}
  replicas: {{ .Values.ventasApi.replicaCount }}
  {{- end }}
```

Esto impide que ejecuciones de `helm upgrade` reescriban y degraden el número de réplicas que el controlador HPA ha escalado en tiempo de ejecución.

---

## 3. Telemetría y Métricas Expuestas

`ventas-api` implementa el middleware `PrometheusMiddleware` que instrumenta automáticamente todas las rutas de negocio y expone el estándar OpenMetrics en `/metrics`:

- `minimarket_requests_total`: Contador etiquetado por `method`, `endpoint` y `status_code`.
- `minimarket_request_duration_seconds`: Histograma de latencias con buckets calibrados para microservicios web (10ms a 5s).
- `minimarket_sales_total`: Contador de ventas completadas exitosamente.
- `minimarket_sales_revenue_soles_total`: Acumulador monetario en Soles (PEN).
- `minimarket_sales_failed_total`: Contador de ventas fallidas etiquetado por causa (`stock_insuficiente`, `carrito_vacio`, `producto_no_encontrado`).

Las etiquetas mantienen una cardinalidad finita y estricta, protegiendo a Prometheus contra el desbordamiento de memoria.
