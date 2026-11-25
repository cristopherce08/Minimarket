# Validación integrada de MiniMarket Cloud

Ejecución del 25 de noviembre de 2026 en Minikube `minimarket`, Kubernetes **1.37.0**, containerd, Calico y nodo Linux ARM64. El chart se instaló en `minimarket-backend-utp`, `minimarket-data-utp` y `minimarket-frontend-utp`. El laboratorio de caos usó `minimarket-pruebas`, con su propio servidor PostgreSQL 16. La base original se consultó en modo de solo lectura.

## Evidencia para la rúbrica

| Criterio | Implementación | Evidencia ejecutada y resultado | Limitación | Estado |
|---|---|---|---|---|
| 1. Infraestructura Base y Redes | [Multipass y Cloud-init](infraestructura/guia-multipass-ubuntu.md), [namespaces](../infra/k8s/namespaces/namespaces.yaml) y [NetworkPolicies](infraestructura/guia-redes-networkpolicies.md). | Se preservó la evidencia anterior de Ubuntu 24.04 ARM64 y `cloud-init done`. En el laboratorio Calico permitió frontend → APIs, API → PostgreSQL y DNS. Denegó frontend → PostgreSQL, pod sin rol → API/DB y PostgreSQL de control desde la API de pruebas. Sondas Ready y Alembic alcanzaron la base autorizada. | Multipass se conservó en su estado previo, apagado. Se reutilizó la evidencia de aprovisionamiento ya certificada. | Aprobado |
| 2. Orquestación K8s y Empaquetado | [Helm](../infra/helm/minimarket/), [manifiestos](../infra/k8s/) y límites CPU/RAM definidos por workload. | `helm lint`, `helm template`, validación de servidor y `helm install` exitosos en el laboratorio. Frontend, ventas, reportes y PostgreSQL Ready. BuildKit validó cinco Dockerfiles y se reconstruyeron las imágenes de frontend y ventas con etiquetas del laboratorio. | Nodo único y backend local de PVC. | Aprobado |
| 3. Procesamiento y Datos Locales | [Alembic y modelos](datos/guia-migraciones-alembic.md), [Spark](../src/spark/k8s/) y [suite PostgreSQL](../tests/). | 44/44 pytest. Alembic `001 → 002 → 003` en una base vacía y adopción del esquema previo en una copia aislada. Spark produjo 2.000 ventas simuladas con dos ejecutores y el endpoint analítico devolvió 200. El PVC conservó datos y agregados tras reemplazar el pod PostgreSQL del laboratorio. | Spark se probó con 2.000 filas para acotar recursos. La base original está en un esquema sin `alembic_version` y requiere el procedimiento de adopción antes de un futuro despliegue. | Aprobado |
| 4. Resiliencia, Caos y Elasticidad | [Istio](../observability/istio/), [HPA](../infra/helm/minimarket/templates/ventas-api-hpa.yaml) y [Chaos Mesh](../observability/chaos-mesh/). | Istio 1.32.0 entregó ambas APIs. Envoy observó `mutual_tls` en destino con política `PERMISSIVE`. Chaos Mesh 2.8.8 inyectó los cuatro experimentos en pods de pruebas. Recuperación tras pod-kill y escalado 2 → 4 → 5 → 2 al elevar de forma controlada la CPU de los pods de pruebas. | Durante `pod-failure` hubo respuestas 503. La primera prueba intensiva de lectura coincidió con presión de memoria. Para recuperar Minikube se elevó temporalmente el límite del contenedor de 6 a 7 GiB, sin cambios de hardware. | Aprobado |
| 5. Telemetría y Dimensionamiento Físico | [Monitores y dashboard](../observability/prometheus-grafana/) y [TCO](../infra/tco/dimensionamiento_tco.sh). | Stack 93.11.0, Grafana 13.3.2 y Prometheus operativos. Se verificaron ServiceMonitor y PodMonitor, las consultas PromQL de los diez paneles y los cálculos del script TCO. | Las tasas y latencias dependen del tráfico dentro de la ventana PromQL. Los valores de energía y costos son supuestos de dimensionamiento. | Aprobado |

La calificación definitiva corresponde al docente.

## Aplicación, datos y herramientas

| Comprobación | Resultado |
|---|---|
| Pytest en PostgreSQL 16 aislado | 44 aprobadas, 0 fallos, 1 aviso de deprecación de Starlette TestClient/httpx. Desglose por archivo: aislamiento 9, salud/métricas 2, productos 4, reportes 1, Spark API 9, ventas 10 y credenciales Spark 9. El baseline previo, 41/41, también se ejecutó. |
| Ventas y contratos | Se ejercitaron descuentos ACID, sobreventa, rollback y concurrencia. Los tres casos nuevos cubren repetición tras pérdida de respuesta, carrera con la misma clave, conflicto 409 y reutilización de una clave revertida. El frontend entregó HTML y rutas API mediante Nginx. |
| Alembic y protección | Kubernetes completó `001_initial_schema`, `002_agregados_spark` y `003_sale_requests`. El validador abortó al recibir `minimarket_db`. Se ensayó `stamp 001_initial_schema` y `upgrade head` en una copia del esquema sin historial, preservando producto, venta, detalle y stock de la fixture. |
| Spark | Spark 3.5.3 sobre ARM64. Ejecutores con 750 y 1.250 filas. Se persistieron tres tablas agregadas. `GET /api/v1/reportes/spark` devolvió `disponible=true`, 2.000 ventas, 30 días, 10 productos en el top e ingresos simulados de S/ 26.016,40. |
| Persistencia | En el PostgreSQL del chart, el mismo PV retuvo 12 productos, 2 ventas de seed, 4 detalles y 2.000 ventas analíticas antes y después de reemplazar el pod. |
| RBAC | El ServiceAccount de Spark pudo crear y limpiar pods de su namespace. Se denegó acceso directo a Secrets, borrado de PVC y creación de pods en el namespace original. Al desactivar la propiedad y reutilización de PVC de los ejecutores, Spark no requirió esos permisos. |
| Formatos y API Server | YAML analizado, scripts comprobados con `bash -n`, JavaScript con `node --check` y JSON de Grafana con `jq`. Dry-run de servidor para Kubernetes, Istio `v1`, monitores `v1` y Chaos `v1alpha1` con CRDs establecidas. |

## Istio y telemetría

- El servicio del gateway fue `ClusterIP` con port-forward local. `utp.minimarket.local` entregó ventas y reportes del chart aislado. `pruebas.minimarket.local` entregó únicamente la API de pruebas. Hosts no declarados devolvieron 404.
- Las APIs tuvieron 2/2 contenedores Ready y los proxies se conectaron a `istiod`. Los proxies receptores de ventas y reportes registraron `connection_security_policy="mutual_tls"` desde el gateway. El frontend y Prometheus accedieron a las APIs en `PERMISSIVE`.
- El cluster de Envoy mostró los parámetros de DestinationRule: 100 conexiones, 50 peticiones pendientes, umbral de tres 5xx, intervalo de 10 s y expulsión base de 30 s. Las rutas Envoy de ventas, en ambos hosts, no incluyeron política de reintentos. Reportes conservó tres reintentos restringidos a fallos de conexión o streams rechazados.
- El ServiceMonitor seleccionó `ventas-api`, `reportes-api` y `ventas-api-pruebas`. El PodMonitor recogió métricas del gateway en 15090. Se deshabilitaron los targets incompatibles de etcd, scheduler y controller-manager. Los 21 targets estuvieron UP con cinco réplicas de prueba y los 18 targets quedaron UP en régimen estable con dos réplicas de prueba.
- Grafana cargó el dashboard `minimarket-obs` con su datasource Prometheus. Las 13 consultas de sus diez paneles rindieron series finitas con tráfico de lectura. Los paneles consultan tráfico y p95 de ambas APIs, 5xx del gateway, CPU/RAM, ventas, ingresos y réplicas actuales/deseadas del HPA.

## Carga, fallos y consistencia

Se verificaron el Secret sin mostrar su contenido, el nombre y destino PostgreSQL, los EndpointSlices, los hosts y selectores antes de escribir. Cada escenario combinó 90 lecturas `hey` y 16 intentos de venta con claves distintas. Para las lecturas se usaron tres clientes con un máximo de 5 solicitudes/s por cliente. Con 90 muestras, el p99 por rango más próximo es la lectura más lenta.

| Escenario | GET req/s | GET p50 / p95 / p99 | GET 2xx / 4xx / 5xx | POST 2xx / 4xx / 5xx |
|---|---:|---|---:|---:|
| Base | 14,97 | 6,3 / 14,1 / 23,8 ms | 90 / 0 / 0 | 16 / 0 / 0 |
| Pod-kill | 14,98 | 5,9 / 12,2 / 23,2 ms | 90 / 0 / 0 | 16 / 0 / 0 |
| Pod-failure | 14,97 | 7,4 / 16,8 / 34,2 ms | 78 / 0 / 12 | 14 / 0 / 2 |
| Retraso 100 ms ± 20 ms | 6,47 | 418,5 / 597,7 / 1.433,7 ms | 90 / 0 / 0 | 16 / 0 / 0 |
| Pérdida 10 % | 14,98 | 6,5 / 211,7 / 218,2 ms | 90 / 0 / 0 | 16 / 0 / 0 |

- Chaos Mesh confirmó `AllInjected` y la lista de pods afectados para los cuatro escenarios. El reemplazo quedó Ready aproximadamente 8 s después de iniciar pod-kill. En `pod-failure` hubo 14 respuestas 503 en total. Los recursos de experimento se retiraron individualmente.
- El laboratorio pasó de 0 productos, 0 ventas y 0 detalles a 1 producto, 78 ventas y 78 detalles. El stock de esa fixture bajó de 200 a 122. Las 78 claves confirmadas corresponden exactamente a las 78 respuestas 201. En esta muestra ocurrieron cero 504 y cero timeouts POST. La evidencia histórica registró ocho 504 con venta confirmada. Una respuesta perdida se puede recuperar con la misma clave y el mismo cuerpo.
- HPA observó 2 réplicas en el ensayo moderado. Una prueba intensiva previa tuvo 3.760 lecturas 200 y 238 timeouts de cliente durante la presión de memoria del nodo. En un ensayo posterior se elevó la CPU de los pods de pruebas y se observaron los eventos de escalado 2 → 4 → 5 → 2 con objetivo de 25 %. Este ensayo comprueba el controlador y su máximo configurado.
- La base original tuvo **12 productos, 5 ventas, 7 detalles y 327 unidades de stock** antes y después de las pruebas. Ningún POST de la intervención se dirigió a esa base.

## Dimensionamiento y TCO

Se comparó `dimensionamiento_tco.sh -y` con el cálculo manual. Los números describen un datacenter hipotético y sus costos en soles.

| Magnitud | Cálculo | Resultado |
|---|---|---:|
| Servidores | 3 × 350 W | 1.050 W |
| Switches | 2 × 120 W | 240 W |
| Potencia IT | 1.050 + 240 | 1.290 W |
| Potencia total | 1.290 × 1,5 PUE | 1.935 W |
| Carga térmica IT | 1.290 × 3,412 | 4.401,48 BTU/h |
| Refrigeración IT | 4.401,48 ÷ 12.000 | 0,37 TR |
| UPS | 1,290 kW ÷ 0,90 × 1,25 | 1,79 kVA |
| Energía anual | 1,935 kW × 8.760 h | 16.950,60 kWh |
| CAPEX | 45.000 + 6.000 + 8.000 + 12.000 + 5.000 | S/ 76.000,00 |
| Energía en tres años | 16.950,60 × 0,70 × 3 | S/ 35.596,26 |
| Mantenimiento en tres años | 76.000 × 10 % × 3 | S/ 22.800,00 |
| TCO on-premise | CAPEX + energía + mantenimiento | S/ 134.396,26 |
| TCO nube | 2.500 × 36 meses | S/ 90.000,00 |

La diferencia modelada es de **S/ 44.396,26** a favor de la nube bajo estos supuestos. La carga térmica se calculó para los equipos IT. El PUE se usó para estimar la potencia total y el consumo eléctrico.

## Trazabilidad de la integración

La rama de integración partió de `e06842c`, respaldada localmente en `backup/minimarket-pre-release-e06842c`. Se incorporaron por fast-forward los 14 commits de Observabilidad hasta `baad4f2`. El repositorio original partió de `7d4acba` en `main`. El historial de cada integrante permaneció en la rama de integración.

| Cambio | Archivos |
|---|---|
| Políticas canónicas y retiro de duplicados | `infra/k8s/network-policies/01-allow-postgres-from-backend.yaml`, `02-allow-backend-traffic.yaml`, `03-allow-frontend-traffic.yaml` y `pruebas/aislamiento.yaml`. Se retiraron los dos YAML operativos de `observability/network-policies/`. |
| Malla y hosts | `observability/istio/gateway.yaml`, `virtualservice.yaml` y `peerauthentication.yaml`. Se verificaron además `destinationrule.yaml` y `podmonitor-gateway.yaml`. |
| Laboratorio y caos | `observability/pruebas/namespace.yaml`, `postgres-pruebas.yaml`, `alembic-job-pruebas.yaml`, `ventas-api-pruebas.yaml` y los cuatro experimentos de `observability/chaos-mesh/`. |
| Monitoreo | `observability/prometheus-grafana/values.yaml`, `servicemonitor.yaml` y `dashboards/minimarket.json`. |
| Idempotencia y arranque | `src/ventas-api/app/{config,main,models,sales_service}.py`, `requirements.txt`, `alembic/versions/003_sale_requests.py`, `src/frontend/js/app.js`, `tests/conftest.py` y `tests/test_sales.py`. |
| Jobs e infraestructura de Kubernetes | `infra/helm/minimarket/templates/alembic-job.yaml`, `ventas-api-deployment.yaml` y `src/spark/k8s/spark-job.yaml`. |
| Operación y evaluación | Contratos, guía Alembic, guía de políticas, matriz UTP y README de observabilidad y monitoreo. La evidencia previa de Istio y Prometheus quedó identificada como histórica. |
