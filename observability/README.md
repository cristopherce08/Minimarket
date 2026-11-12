# Observabilidad y resiliencia (Integrante 4)

Istio, Prometheus/Grafana, Chaos Mesh y pruebas de carga del MiniMarket sobre minikube.

## 1. Requisitos
Cluster `minimarket` con Calico (`setup-minikube.sh`), chart del MiniMarket desplegado, `kubectl`, `helm`, `istioctl` 1.32, `hey`.

## 2. Instalación

**Prometheus + Grafana** (`observability/prometheus-grafana/`):

    helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
    helm install monitoring prometheus-community/kube-prometheus-stack \
      -n monitoring --create-namespace \
      -f observability/prometheus-grafana/values.yaml
    kubectl apply -f observability/prometheus-grafana/servicemonitor.yaml
    kubectl create configmap minimarket-dashboard -n monitoring \
      --from-file=minimarket.json=observability/prometheus-grafana/dashboards/minimarket.json
    kubectl label cm minimarket-dashboard -n monitoring grafana_dashboard=1

**Istio** (`observability/istio/`):

    istioctl install --set profile=demo -y
    kubectl label ns minimarket-backend istio-injection=enabled --overwrite
    kubectl rollout restart deploy -n minimarket-backend
    kubectl apply -f observability/istio/gateway.yaml \
      -f observability/istio/virtualservice.yaml \
      -f observability/istio/destinationrule.yaml
    kubectl apply -f observability/istio/podmonitor-gateway.yaml

**Chaos Mesh** (`observability/chaos-mesh/`):

    helm repo add chaos-mesh https://charts.chaos-mesh.org
    helm install chaos-mesh chaos-mesh/chaos-mesh -n chaos-mesh --create-namespace \
      --set chaosDaemon.runtime=containerd \
      --set chaosDaemon.socketPath=/run/containerd/containerd.sock

**Protección de PostgreSQL** (ver hallazgo 1, aplicar una vez):

    kubectl exec -n minimarket-data deploy/postgres -- psql -U minimarket_user \
      -d minimarket_db -c "alter database minimarket_db set idle_in_transaction_session_timeout = '30s';"

## 3. Acceso

    kubectl port-forward -n istio-system svc/istio-ingressgateway 8080:80
    kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80

Grafana en http://localhost:3000, dashboard "MiniMarket". Cada comando va en su propia terminal.

## 4. Pruebas de carga y caos

Carga (5 conexiones, por debajo del pool de BD de 5+5):

    hey -z 120s -c 5 -m POST -T "application/json" \
      -d '{"items":[{"product_id":1,"quantity":1}]}' \
      http://localhost:8080/api/v1/ventas

Experimentos (aplicar con la carga en marcha, luego eliminar):

    kubectl apply -f observability/chaos-mesh/pod-kill-ventas.yaml
    kubectl delete -f observability/chaos-mesh/pod-kill-ventas.yaml
    kubectl apply -f observability/chaos-mesh/network-delay-ventas.yaml
    kubectl delete -f observability/chaos-mesh/network-delay-ventas.yaml

## 5. Resultados (2 réplicas iniciales, HPA hasta 5)

| Escenario | 201 | Errores | Req/s | p95 | p99 |
|---|---|---|---|---|---|
| Base (sin caos) | 3974 | 0 | 66 | 0.13 s | 0.18 s |
| Pod-kill | 6803 | 3 x 504 | 57 | 0.19 s | 0.38 s |
| Retraso de red 100 ms | 3002 | 19 x 503, 8 x 504 | 25 | 1.18 s | 2.55 s |

Pod-kill: Kubernetes repuso el pod y el HPA subió a 5 réplicas; solo fallaron las 3 peticiones en vuelo.

Retraso de red: el 99.1% de las ventas se completó. La ventana del retraso coincidió con el escalado del HPA, así que el resultado es orientativo.

Integridad: en la prueba de red hubo 3010 ventas en BD frente a 3002 respuestas 201; las 8 de diferencia son las 504 (venta registrada, cliente con timeout).


## 6. Hallazgos y recomendaciones para el equipo

1. **Transacciones huérfanas.** Un pod-kill en pleno SELECT FOR UPDATE dejó sesiones idle in transaction que retuvieron el bloqueo de la fila del producto. Las demás ventas esperaron con su conexión tomada, el pool (5+5) se agotó, el readiness (/ready, necesita conexión) falló y el gateway respondió 503 UH. Mitigación: idle_in_transaction_session_timeout en PostgreSQL (ver sección 2); debería ir en el init de la BD o en el chart.
2. **Idempotencia.** Un 504 puede ocultar una venta ya registrada; un reintento duplicaría la venta. Se recomienda una clave de idempotencia en POST /ventas. Por eso el VirtualService solo reintenta en connect-failure y refused-stream.
3. **Readiness comparte el pool de la app.** Con el pool agotado el pod sale del servicio y la congestión se agrava.
4. **Arranque.** La versión anterior de ventas-api no reintentaba la conexión a BD si PostgreSQL aún no estaba listo.
5. **Observabilidad.** La métrica de la app no ve los errores que genera Istio (503 y 504); el dashboard usa istio_requests_total del gateway (PodMonitor).
6. **NetworkPolicies.** Verificar que no bloqueen el scrape de Prometheus desde monitoring antes de aplicarlas.

## 7. Dimensionamiento físico y TCO

    ./infra/tco/dimensionamiento_tco.sh        # interactivo
    ./infra/tco/dimensionamiento_tco.sh -y     # valores por defecto
