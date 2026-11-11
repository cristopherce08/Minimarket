# Guía de Sustentación Académica — Integrante 2
## MiniMarket Cloud | Aplicación, Concurrencia y HPA

---

## 1. Responsabilidades del Integrante 2 ante el Evaluador

| Área | Entregable Concreto | Rúbrica UTP |
|---|---|:---:|
| **Transacciones ACID y Concurrencia** | `sales_service.py` con `SELECT ... FOR UPDATE` y descuento atómico condicional | Criterio 3 (Procesamiento y Datos) |
| **Control de Sobreventa** | Pruebas de integración concurrentes con 10 y 20 workers compitiendo por stock | Criterio 3 (Procesamiento y Datos) |
| **Empaquetado HPA** | Template Helm `ventas-api-hpa.yaml` (`autoscaling/v2`) y `values.yaml` | Criterio 2 (Orquestación K8s) |
| **Autoescalado Bajo Carga Real** | Demostración en vivo de escalamiento de 2 a 5 pods usando `hey` y Metrics Server | Criterio 4 (Resiliencia y Elasticidad) |
| **Telemetría y Métricas** | Endpoint `/metrics` con `PrometheusMiddleware` y métricas de negocio | Criterio 5 (Telemetría) |

---

## 2. Comandos en Vivo para la Demostración

### Paso 1: Mostrar las Pruebas Automatizadas de Aislamiento, Concurrencia y ACID
```bash
# Levantar PostgreSQL de pruebas aislado en RAM (puerto 5434)
docker compose -f docker-compose.test.yml up -d

# Ejecutar la suite completa de 18 pruebas automatizadas
TEST_DATABASE_URL="postgresql+psycopg://test_user:test_password@localhost:5434/minimarket_test_db" .venv/bin/pytest tests/ -v
```
*Qué explicar:*  
1. Demostrar la protección de datos: la suite rechaza categóricamente cualquier intento de conexión a la base de desarrollo `minimarket_db` mediante aserciones de seguridad en `tests/conftest.py` y `tests/test_database_isolation.py`.
2. Validar que las pruebas unitarias y de integración concurrentes (`test_prevent_overselling_concurrency`, `test_concurrent_multi_product_sales_no_deadlock` y `test_high_concurrency_exact_inventory_accounting`) operan sobre una base efímera en `tmpfs`, garantizando que:
   - El stock nunca cae por debajo de 0.
   - Exactamente la cantidad disponible se vende (HTTP 201) y el excedente se rechaza limpiamente con HTTP 400.
   - Se previenen deadlocks al bloquear filas en orden ascendente por ID.

### Paso 2: Mostrar el Estado del HPA y Metrics Server en Kubernetes
```bash
kubectl top nodes
kubectl top pods -n minimarket-backend
kubectl get hpa -n minimarket-backend
```
*Qué explicar:*  
Metrics Server recolecta métricas reales de CPU/RAM de los pods de `ventas-api`. El HPA está configurado con min=2, max=5 y target=25% de utilización promedio de CPU.

### Paso 3: Disparar la Prueba de Carga con `hey`
```bash
# En una terminal: observar los pods
kubectl get pods -n minimarket-backend -l app=ventas-api -w

# En otra terminal: disparar el script de carga
bash tests/load/generar_carga_hpa.sh http://localhost:8005/api/v1/productos 45s 30
```
*Qué explicar:*  
La carga satura la CPU de los 2 pods iniciales. El HPA detecta el incremento sobre el 25% y escala automáticamente primero a 4 pods y luego al tope de 5 pods. Los nuevos pods alcanzan estado `Ready` y absorben el tráfico balanceado.

### Paso 4: Registrar una Venta Atómica en Vivo
```bash
curl -i -X POST http://localhost:8005/api/v1/ventas \
  -H "Content-Type: application/json" \
  -d '{"items": [{"product_id": 1, "quantity": 1}]}'
```
*Qué explicar:*  
Durante el escalamiento, las ventas continúan operando con total consistencia ACID y sin interrupción de servicio.

### Paso 5: Mostrar la Reducción Ordenada (Scale Down)
```bash
kubectl get hpa -n minimarket-backend
kubectl describe hpa -n minimarket-backend ventas-api-hpa
```
*Qué explicar:*  
Al cesar el tráfico, transcurridos los 60 segundos de la ventana de estabilización (`stabilizationWindowSeconds: 60`), el HPA termina ordenadamente las 3 réplicas adicionales y regresa a las 2 réplicas base para optimizar el consumo de recursos de la nube.
