# Checklist de Cumplimiento de la Rúbrica de Evaluación (UTP)

Este documento detalla los **cinco criterios de evaluación** para el proyecto **MiniMarket Cloud**, estableciendo las tecnologías exigidas, los entregables concretos, la estrategia de prueba y las evidencias exactas que se presentarán durante la sustentación académica.

---

## Matriz General de Criterios

| Criterio | Nombre del Dominio | Tecnologías Clave | Estado Actual | Integrante Responsable |
|---|---|---|:---:|---|
| **Criterio 1** | Infraestructura Base, Virtualización y Redes | Ubuntu, Multipass, Cloud-init, Docker Networks, K8s NetworkPolicies | ⏳ En preparación (Etapa 0) | Integrante 1 |
| **Criterio 2** | Contenedores, Orquestación y Empaquetado | Docker, Minikube, Kubernetes, Helm Charts | ⏳ En preparación (Etapa 0) | Integrante 1 & 2 |
| **Criterio 3** | Desarrollo de Microservicios y Persistencia | HTML/JS, Python FastAPI, PostgreSQL (Transacciones ACID) | ⏳ En preparación (Etapa 0) | Integrante 2 & 3 |
| **Criterio 4** | Procesamiento Distribuido de Grandes Volúmenes | Apache Spark, PySpark, Spark DataFrames, JDBC | ⏳ En preparación (Etapa 0) | Integrante 3 |
| **Criterio 5** | Observabilidad, Resiliencia, Pruebas de Carga y TCO | Istio, Chaos Mesh, HPA, Prometheus, Grafana, `hey`, Script Bash | ⏳ En preparación (Etapa 0) | Integrante 4 |

---

## Desglose Detallado por Criterio y Evidencias para Sustentación

### Criterio 1: Infraestructura Base, Virtualización y Redes

**Objetivo:** Demostrar aprovisionamiento automatizado, segmentación y aislamiento de tráfico a nivel de red.

- [ ] **Configuración de VM Ubuntu con Multipass y Cloud-init:**
  - Archivo `infra/multipass/cloud-init.yaml` que aprovisiona usuarios, paquetes base y configuración de red.
  - *Evidencia:* Salida de `multipass info` y archivo cloud-init ejecutado correctamente.
- [ ] **Aislamiento con Docker Networks y Namespaces de Kubernetes:**
  - Namespaces dedicados: `minimarket-frontend`, `minimarket-backend`, `minimarket-data`, `observabilidad`.
  - *Evidencia:* Comando `kubectl get namespaces`.
- [ ] **Políticas de red L3/L4 (Kubernetes NetworkPolicies):**
  - Regla que prohíbe el acceso directo del Frontend al pod de PostgreSQL.
  - Regla de entrada restringida a PostgreSQL solo para el selector `app: ventas-api` y `app: spark-job`.
  - *Evidencia:* Prueba interactiva con un pod efímero de prueba (`curl` o `nc`):
    - Conexión rechazada/timeout desde pod de frontend a postgres:5432.
    - Conexión exitosa desde pod de ventas-api a postgres:5432.

---

### Criterio 2: Contenedores, Orquestación y Empaquetado Helm

**Objetivo:** Demostrar buenas prácticas de contenerización y automatización del despliegue en Kubernetes.

- [ ] **Dockerfiles optimizados (Multi-stage builds):**
  - Dockerfile para `frontend` (Nginx Alpine con assets estáticos).
  - Dockerfile para `ventas-api` (Python slim con dependencias aisladas y usuario no-root).
  - Dockerfile para `reportes-api` / Spark (imagen ligera con entorno PySpark).
  - *Evidencia:* Inspección de imágenes (`docker images`) mostrando tamaños reducidos.
- [ ] **Manifiestos y Helm Chart Modular:**
  - Chart `infra/helm/minimarket` estructurado con `values.yaml` personalizable por entorno.
  - Plantillas de Deployments, Services, ConfigMaps, Secrets y PVCs.
  - Health checks configurados (`livenessProbe` y `readinessProbe`).
  - *Evidencia:*
    - Ejecución limpia de `helm lint infra/helm/minimarket`.
    - Despliegue con un solo comando: `helm install minimarket infra/helm/minimarket`.
    - Salida de `kubectl get all -n minimarket-backend`.

---

### Criterio 3: Lógica de Negocio y Persistencia Transaccional

**Objetivo:** Demostrar una aplicación funcional completa con manejo de concurrencia y consistencia en base de datos.

- [ ] **Interfaz Web de Usuario (Frontend SPA):**
  - Visualización del catálogo de productos con precio y stock actualizado.
  - Carrito de ventas interactivo permitiendo seleccionar varios productos y cantidades.
  - Panel visual de reportes ejecutados.
  - *Evidencia:* Captura y demostración en vivo desde el navegador web.
- [ ] **Microservicio `ventas-api` y Descuento de Stock:**
  - Endpoint `POST /api/v1/ventas` con transacción ACID (`SELECT ... FOR UPDATE` o bloqueo a nivel de fila).
  - Validación de existencia previa y control estricto de no permitir ventas con stock insuficiente (HTTP 400 con mensaje descriptivo).
  - Descuento atómico del stock y confirmación de la venta.
  - *Evidencia:*
    1. Venta exitosa descontando stock de 2 productos distintos.
    2. Intento de compra con cantidad mayor al stock disponible -> comprobación de rechazo y rollback (stock intacto).
- [ ] **Persistencia en PostgreSQL:**
  - Esquema normalizado (`productos`, `ventas`, `detalle_ventas`) con claves foráneas.
  - Almacenamiento en volumen persistente de Kubernetes (PV/PVC).
  - *Evidencia:* Consulta `SELECT * FROM productos;` y `SELECT * FROM detalle_ventas;` desde `psql`.

---

### Criterio 4: Procesamiento Distribuido de Grandes Volúmenes (Apache Spark)

**Objetivo:** Implementar computación distribuida para analítica desacoplada de la base transaccional.

- [ ] **Jobs PySpark para Agregaciones Analíticas:**
  - Script `src/spark/jobs/reporte_diario.py`: Cálculo de ingresos brutos por fecha, volumen de transacciones y ticket promedio.
  - Script `src/spark/jobs/productos_top.py`: Ranking de productos con mayor rotación e ingresos generados.
  - Lectura de datos vía JDBC conectada a PostgreSQL mediante Spark DataFrames.
- [ ] **Integración en `reportes-api`:**
  - Endpoint `GET /api/v1/reportes/ventas-diarias` y `GET /api/v1/reportes/productos-top` que sirven la información procesada por Spark.
  - *Evidencia:*
    - Logs de ejecución de PySpark mostrando la inicialización del `SparkSession`, creación de etapas (stages), tareas (tasks) y salida del DataFrame.
    - Respuesta JSON del endpoint de reportes consumida en vivo por el frontend.

---

### Criterio 5: Observabilidad, Resiliencia, Pruebas de Carga y TCO

**Objetivo:** Demostrar confiabilidad de nivel empresarial, tolerancia a fallos, telemetría y viabilidad económica.

- [ ] **Service Mesh (Istio):**
  - Malla de servicios activa inyectando sidecars Envoy en los microservicios.
  - Tráfico gestionado mediante `Istio Gateway` y `VirtualService`.
  - *Evidencia:* Gráfico de topología en Kiali o visualización de mTLS activo entre pods.
- [ ] **Autoescalado Horizontal (HPA) y Pruebas de Carga con `hey`:**
  - HPA configurado para `ventas-api` con umbral de CPU al 60%.
  - Inyección de carga continua: `hey -n 15000 -c 60 http://<ip-cluster>/api/v1/productos`.
  - *Evidencia:* Registro en tiempo real de `kubectl get hpa -w` evidenciando el escalado de 2 réplicas iniciales a 4 o 5 réplicas bajo carga, y posterior desescalado.
- [ ] **Ingeniería del Caos (Chaos Mesh):**
  - Manifiesto de experimento de caos (`PodChaos` o `NetworkChaos`).
  - Inyección de fallo (eliminación abrupta de pods o latencia) mientras se ejecuta la prueba con `hey`.
  - *Evidencia:* Gráficos en Grafana mostrando cómo el servicio absorbe el fallo y se auto-recupera sin interrupción prolongada del servicio (zero-downtime).
- [ ] **Pila de Monitoreo (kube-prometheus-stack + Grafana):**
  - Métricas de latencia HTTP y tasa de peticiones scrapeadas desde `/metrics` de FastAPI.
  - Dashboard interactivo en Grafana importado y funcional.
  - *Evidencia:* Visualización del dashboard de Grafana durante la prueba de carga y el experimento de caos.
- [ ] **Script de Dimensionamiento Físico y TCO:**
  - Script ejecutable en Bash: `infra/tco/dimensionamiento_tco.sh`.
  - Parámetros de entrada interactivos: cantidad de transacciones por segundo, servidores físicos equivalentes, costo de kWh, PUE de datacenter.
  - *Evidencia:* Ejecución en consola del script mostrando el reporte detallado con cálculo de Potencia en Watts, Disipación Térmica en BTU/hr, y comparativa TCO a 3 años (On-Premise vs. Cloud).
