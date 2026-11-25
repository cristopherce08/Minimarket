# Evidencia de Prometheus y del dashboard

Este documento responde a la corrección del revisor sobre Prometheus: mostrar los targets, las consultas PromQL y que el dashboard tiene datos. Los datos se tomaron el 2026-11-24 con el clúster `minimarket`, usando solo operaciones de lectura. Para que los paneles de tasa tuvieran datos se enviaron 288 peticiones `GET` (mitad `/api/v1/productos`, mitad `/api/v1/reportes/ventas-hoy`) durante unos 40 segundos por el gateway.

## 1. Targets

Prometheus lee métricas de "targets" (los servicios que expone). Se consultó su estado con la API de Prometheus:

```bash
kubectl get --raw "/api/v1/namespaces/monitoring/services/monitoring-kube-prometheus-prometheus:9090/proxy/api/v1/targets?state=active"
```

Resultado: **19 targets, 16 en `UP`**.

| Target | Estado | Cantidad |
|---|---|---|
| `ventas-api` | UP | 2 (una por réplica) |
| `reportes-api` | UP | 1 |
| `monitoring/istio-ingressgateway` | UP | 1 |
| `kube-state-metrics`, `node-exporter`, `kubelet`, `apiserver`, `coredns`, `kube-proxy` | UP | 8 |
| `monitoring-grafana`, operador y Prometheus | UP | 4 |
| `kube-controller-manager`, `kube-etcd`, `kube-scheduler` | **DOWN** | 3 |

**Sobre los 3 targets en `DOWN`:** son componentes internos de Kubernetes. En minikube solo escuchan en local (`127.0.0.1`), así que Prometheus no puede conectarse (`connection refused` en `192.168.49.2`, puertos 10257, 2381 y 10259). No afectan a la aplicación. Se pueden desactivar en los valores de `kube-prometheus-stack` si se quiere una lista de targets sin `DOWN`.

## 2. Consultas PromQL

Son las mismas que usan los paneles del dashboard "MiniMarket - Observabilidad". Valores medidos durante la prueba:

| Qué mide | Consulta PromQL | Resultado |
|---|---|---|
| Estado de las APIs | `up{namespace="minimarket-backend"}` | 1 en las 3 instancias |
| Tráfico por endpoint (req/s) | `sum(rate(minimarket_requests_total[1m])) by (exported_endpoint)` | `/api/v1/productos`: 2.51 |
| Respuestas del gateway por código (req/s) | `sum(rate(istio_requests_total{source_workload="istio-ingressgateway"}[1m])) by (response_code)` | código 200: 4.62 |
| Latencia p95 de `ventas-api` | `histogram_quantile(0.95, sum(rate(minimarket_request_duration_seconds_bucket[1m])) by (le, service))` | 0.0426 s (≈ 43 ms) |
| CPU por namespace (núcleos) | `sum(rate(container_cpu_usage_seconds_total{namespace=~'minimarket-.*',container!=''}[2m])) by (namespace)` | backend 0.0446, data 0.0233, frontend 0.0002 |
| RAM por namespace | `sum(container_memory_working_set_bytes{namespace=~'minimarket-.*',container!=''}) by (namespace)` | backend ≈ 317 MiB, data ≈ 39 MiB, frontend ≈ 5 MiB |
| Réplicas de `ventas-api` | `kube_deployment_status_replicas{namespace="minimarket-backend",deployment="ventas-api"}` | 2 |
| Errores 5xx del gateway (última hora) | `sum(increase(istio_requests_total{source_workload="istio-ingressgateway",response_code=~"5.."}[1h])) or vector(0)` | 0 |

Las 288 peticiones salieron todas con código 200 en el gateway. El resultado de 0 errores 5xx corresponde solo a la última hora de esta prueba: los errores 503/504 de las pruebas de caos están documentados aparte, en `observability/README.md`.

## 3. Dashboard

El dashboard "MiniMarket - Observabilidad" (`dashboards/minimarket.json`) tiene 10 paneles: CPU y RAM por namespace, tráfico por endpoint, errores 5xx del gateway, latencia p95, ventas completadas, ingresos acumulados, peticiones fallidas, réplicas del HPA y respuestas del gateway por código. Los paneles de tasa respondieron con datos durante la prueba, como se ve en la tabla anterior.

Capturas de pantalla (pendientes de tomar en el navegador, con Grafana en `http://localhost:3000`):

- [ ] Lista de targets en Prometheus (`http://localhost:9090/targets`)
- [ ] Dashboard completo con datos
- [ ] Panel de latencia p95 y de respuestas por código

## 4. Limitaciones

- **El dashboard no muestra el tráfico de `reportes-api`.** Esta API expone otros nombres de métrica (`minimarket_reportes_requests_total` y `minimarket_reportes_request_duration_seconds`), y los paneles de "Tráfico por endpoint" y "Latencia p95" solo consultan las de `ventas-api`. Por eso, de las 288 peticiones, solo aparecen las de productos en esos paneles. Se puede corregir agregando las consultas de reportes a esos paneles.
- **Los paneles "Ventas completadas" e "Ingresos acumulados"** dependen de ventas reales (código 201 y la métrica de ingresos). Como esta prueba fue solo de lectura, no suman datos nuevos.
- Los valores de CPU y RAM son de un momento puntual, con poca carga.

## 5. Cómo repetirlo

```bash
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
# abrir http://localhost:9090/targets y probar las consultas en http://localhost:9090/graph
```
