# Checklist de Cumplimiento de la Rúbrica de Evaluación (UTP)

Este documento detalla los **cinco criterios de evaluación** oficiales para el proyecto **MiniMarket Cloud**, estableciendo las tecnologías exigidas, los entregables concretos, la estrategia de prueba y las evidencias exactas que se presentarán durante la sustentación académica.

---

## Matriz General de Criterios

| Criterio | Nombre del Dominio | Tecnologías Clave | Estado Actual | Integrante Responsable |
|---|---|---|:---:|---|
| **Criterio 1** | Infraestructura Base y Redes | Ubuntu, Multipass, Cloud-init, Docker Networks, K8s NetworkPolicies | ✅ Completado y Verificado | Integrante 1 |
| **Criterio 2** | Orquestación K8s y Empaquetado | Docker, Minikube, Kubernetes, Helm Charts | ✅ Completado y Verificado | Integrante 1 & 2 |
| **Criterio 3** | Procesamiento y Datos Locales | HTML/JS, Python FastAPI, PostgreSQL 16 (ACID), Alembic, PySpark | ✅ Funcional (Etapa 1) | Integrante 2 & 3 |
| **Criterio 4** | Resiliencia, Caos y Elasticidad | Metrics Server, HPA, Chaos Mesh (inyección de fallas) | ⏳ Pendiente (Etapa posterior) | Integrante 2 & 4 |
| **Criterio 5** | Telemetría y Dimensionamiento Físico | Istio Service Mesh, Prometheus, Grafana, `hey`, Script Bash TCO | ⏳ Pendiente (Etapa posterior) | Integrante 4 |

---

## Desglose Detallado por Criterio y Evidencias para Sustentación

### Criterio 1: Infraestructura Base y Redes

**Objetivo:** Demostrar aprovisionamiento automatizado, segmentación y aislamiento de tráfico a nivel de red.

- [x] **Configuración de VM Ubuntu con Multipass y Cloud-init:**
  - Manifiesto `infra/multipass/cloud-init.yaml` y scripts reproducibles `setup-vm.sh` y `verify-vm.sh`.
  - *Evidencia documentada:* [`docs/infraestructura/guia-multipass-ubuntu.md`](infraestructura/guia-multipass-ubuntu.md).
- [x] **Aislamiento con Docker Networks y Namespaces de Kubernetes:**
  - Namespaces dedicados creados: `minimarket-frontend`, `minimarket-backend`, `minimarket-data`.
  - Red Docker aislada en Docker Compose (`minimarket-net`).
  - *Evidencia documentada:* [`docs/infraestructura/arquitectura-k8s.md`](infraestructura/arquitectura-k8s.md).
- [x] **Políticas de red L3/L4 (Kubernetes NetworkPolicies con Calico):**
  - Regla que prohíbe el acceso directo del Frontend al pod de PostgreSQL (verificado: `Connection timed out`).
  - Regla de entrada autorizada a PostgreSQL solo para el backend (verificado: port 5432 `open`).
  - *Evidencia documentada:* [`docs/infraestructura/guia-redes-networkpolicies.md`](infraestructura/guia-redes-networkpolicies.md).

---

### Criterio 2: Orquestación K8s y Empaquetado

**Objetivo:** Demostrar buenas prácticas de contenerización y automatización del despliegue en Kubernetes.

- [x] **Dockerfiles optimizados (Multi-stage builds):**
  - Dockerfiles para `frontend`, `ventas-api` y `reportes-api` en Python 3.12 y Nginx Alpine.
  - *Evidencia documentada:* Imágenes generadas y cargadas en Minikube (`minikube image load`).
- [x] **Manifiestos y Helm Chart Modular:**
  - Chart `infra/helm/minimarket` validado limpiamente con `helm lint` y renderizado con `helm template`.
  - Despliegue funcional en Minikube (`helm install minimarket infra/helm/minimarket`).
  - Health checks configurados (`livenessProbe` a `/health` y `readinessProbe` a `/ready` operando en 200 OK).
  - Límites y requests de CPU/RAM configurados para soporte de HPA.
  - *Evidencia documentada:* [`docs/infraestructura/guia-helm-despliegue.md`](infraestructura/guia-helm-despliegue.md).

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
