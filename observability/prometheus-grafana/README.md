# Prometheus y Grafana

El chart usa [`values.yaml`](values.yaml). Aplica el [ServiceMonitor](servicemonitor.yaml) y el [PodMonitor de Istio](../istio/podmonitor-gateway.yaml) después de instalar las CRDs de Prometheus Operator.

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --version 93.11.0 -n monitoring --create-namespace \
  -f observability/prometheus-grafana/values.yaml
kubectl apply -f observability/prometheus-grafana/servicemonitor.yaml \
  -f observability/istio/podmonitor-gateway.yaml
kubectl -n monitoring create configmap minimarket-dashboard \
  --from-file=minimarket.json=observability/prometheus-grafana/dashboards/minimarket.json \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl -n monitoring label configmap minimarket-dashboard grafana_dashboard=1 --overwrite
```

Consulta `/targets` de Prometheus y abre el dashboard **MiniMarket - Observabilidad** en Grafana. Genera tráfico GET hacia ambas APIs y espera dos intervalos de scraping para ver tasas y percentiles. ServiceMonitor conserva el label `endpoint` de la aplicación. Los paneles de ventas e ingresos muestran cero cuando faltan muestras de ventas.

[Resultados del Integrante 4](evidencia-prometheus.md) · [Validación final UTP](../../docs/validacion-final-utp.md)
