# Checklist de Cumplimiento de la Rúbrica de Evaluación (UTP)

Este documento detalla los **cinco criterios de evaluación** oficiales para el proyecto **MiniMarket Cloud**, estableciendo las tecnologías exigidas, los entregables concretos, la estrategia de prueba y las evidencias exactas que se presentarán durante la sustentación académica.

---

## Matriz General de Criterios

| Criterio | Nombre del Dominio | Tecnologías Clave | Estado Actual | Integrante Responsable |
|---|---|---|:---:|---|
| **Criterio 1** | Infraestructura Base y Redes | Ubuntu, Multipass, Cloud-init, Docker Networks, K8s NetworkPolicies | ⏳ En preparación (Etapa 0/1) | Integrante 1 |
| **Criterio 2** | Orquestación K8s y Empaquetado | Docker, Minikube, Kubernetes, Helm Charts | ⏳ En preparación (Etapa 0/1) | Integrante 1 & 2 |
| **Criterio 3** | Procesamiento y Datos Locales | HTML/JS, Python FastAPI, PostgreSQL 16 (ACID), Alembic, PySpark | ⏳ En desarrollo (Etapa 1) | Integrante 2 & 3 |
| **Criterio 4** | Resiliencia, Caos y Elasticidad | Metrics Server, HPA, Chaos Mesh (inyección de fallas) | ⏳ Pendiente (Etapa posterior) | Integrante 2 & 4 |
| **Criterio 5** | Telemetría y Dimensionamiento Físico | Istio Service Mesh, Prometheus, Grafana, `hey`, Script Bash TCO | ⏳ Pendiente (Etapa posterior) | Integrante 4 |

---

## Desglose Detallado por Criterio y Evidencias para Sustentación

### Criterio 1: Infraestructura Base y Redes

**Objetivo:** Demostrar aprovisionamiento automatizado, segmentación y aislamiento de tráfico a nivel de red.

- [ ] **Configuración de VM Ubuntu con Multipass y Cloud-init:**
  - Archivo `infra/multipass/cloud-init.yaml` que aprovisiona usuarios, paquetes base y configuración de red.
  - *Evidencia requerida:* Salida de `multipass info` y archivo cloud-init ejecutado correctamente.
- [ ] **Aislamiento con Docker Networks y Namespaces de Kubernetes:**
  - Namespaces dedicados: `minimarket-frontend`, `minimarket-backend`, `minimarket-data`, `observabilidad`.
  - Red Docker aislada en Docker Compose (`minimarket-net`).
  - *Evidencia requerida:* Comando `kubectl get namespaces` / inspección de red Docker.
- [ ] **Políticas de red L3/L4 (Kubernetes NetworkPolicies):**
  - Regla que prohíbe el acceso directo del Frontend al pod de PostgreSQL.
  - Regla de entrada restringida a PostgreSQL solo para el backend y jobs autorizados.
  - *Evidencia requerida:* Prueba interactiva con pod efímero (`curl` o `nc` bloqueado vs. permitido).

---

### Criterio 2: Orquestación K8s y Empaquetado

**Objetivo:** Demostrar buenas prácticas de contenerización y automatización del despliegue en Kubernetes.

- [ ] **Dockerfiles optimizados (Multi-stage builds):**
  - Dockerfile para `frontend` (Nginx Alpine con assets estáticos).
  - Dockerfile para `ventas-api` (Python 3.12 slim, usuario no-root).
  - Dockerfile para `reportes-api` (Python 3.12 slim).
  - *Evidencia requerida:* Inspección de imágenes (`docker images`) mostrando etiquetas y tamaños optimizados.
- [ ] **Manifiestos y Helm Chart Modular:**
  - Chart `infra/helm/minimarket` estructurado con `values.yaml` parametrizado.
  - Plantillas de Deployments, Services, ConfigMaps, Secrets y PVCs.
  - Health checks configurados (`livenessProbe` y `readinessProbe` apuntando a `/health` y `/ready`).
  - *Evidencia requerida:* `helm lint`, despliegue con `helm install` y salida de `kubectl get all`.

---

### Criterio 3: Procesamiento y Datos Locales

**Objetivo:** Demostrar una aplicación funcional completa con persistencia relacional transaccional, control de inventario y procesamiento analítico de datos.

- [ ] **Interfaz Web de Usuario (Frontend SPA):**
  - Catálogo en vivo, formulario de productos, carrito de venta multi-producto y panel de inventario/reportes.
  - *Evidencia requerida:* Navegación y demostración en vivo en navegador web sin datos ficticios en presencia de backend.
- [ ] **Microservicio `ventas-api` con Descuento Atómico y Control de Concurrencia:**
  - Transacciones ACID en PostgreSQL con `SELECT ... FOR UPDATE` (bloqueo de fila).
  - Rechazo estricto y rollback completo si algún ítem carece de stock (HTTP 400).
  - Guardado del precio histórico unitario (`unit_price`) en cada detalle de venta.
  - *Evidencia requerida:* Suite de pruebas pytest ejecutadas y reporte con paso exitoso de compra, descuento de stock y rechazo por stock insuficiente.
- [ ] **Persistencia Relacional y Migraciones con Alembic:**
  - Tablas: `products`, `sales`, `sale_items` con tipos `Numeric(10, 2)` para dinero.
  - Script de seed idempotente con productos típicos de bodega peruana.
  - *Evidencia requerida:* Historial de migraciones Alembic y consulta `SELECT * FROM products;`.
- [ ] **Microservicio `reportes-api` y Procesamiento de Datos:**
  - Endpoints de resumen diario y top productos más vendidos.
  - Preparado para integración desacoplada con Apache Spark en etapas posteriores.
  - *Evidencia requerida:* Salida JSON de reportes basada en consultas reales a PostgreSQL.

---

### Criterio 4: Resiliencia, Caos y Elasticidad

**Objetivo:** Demostrar tolerancia a fallos, auto-recuperación y escalamiento automático ante demanda variable.

- [ ] **Autoescalado Horizontal (HPA):**
  - Métricas recolectadas por Metrics Server en Kubernetes.
  - Configuración HPA para `ventas-api` escalando de 2 a 5 pods según umbral de CPU.
  - *Evidencia requerida:* Salida de `kubectl get hpa -w` bajo carga generada con `hey`.
- [ ] **Ingeniería del Caos (Chaos Mesh):**
  - Manifiestos de experimentos de caos (`PodChaos` / `NetworkChaos`).
  - Demostración de auto-recuperación de pods sin caída del servicio (Zero-Downtime).
  - *Evidencia requerida:* Métricas de resiliencia y logs de Kubernetes durante la inyección del fallo.

---

### Criterio 5: Telemetría y Dimensionamiento Físico

**Objetivo:** Demostrar observabilidad avanzada con service mesh y sustentación de dimensionamiento térmico y económico.

- [ ] **Service Mesh (Istio):**
  - Ingress Gateway y mTLS entre microservicios con proxies Envoy.
  - *Evidencia requerida:* Kiali graph o inspección de certificados mTLS.
- [ ] **Pila de Monitoreo (kube-prometheus-stack + Grafana):**
  - Endpoint `/metrics` instrumentado en microservicios con `prometheus-client`.
  - ServiceMonitors y Tablero interactivo en Grafana.
  - *Evidencia requerida:* Captura de dashboard en Grafana reflejando RPS, latencia y uso de recursos.
- [ ] **Pruebas de Carga con `hey`:**
  - Script automatizado de benchmarking y saturación.
  - *Evidencia requerida:* Reporte generado por `hey` (latencia P50, P95, throughput req/sec).
- [ ] **Script de Dimensionamiento Físico y TCO:**
  - Script interactivo en Bash (`infra/tco/dimensionamiento_tco.sh`) para cálculo de Watts, BTU/hr y TCO a 3 años.
  - *Evidencia requerida:* Ejecución del script en consola con salida de costos y disipación térmica.
