# Prometheus + Grafana

Requisitos: minikube corriendo, kubectl y Helm instalados.

## Instalar

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm install monitoring prometheus-community/kube-prometheus-stack -n monitoring --create-namespace -f observability/prometheus-grafana/values.yaml

## Entrar a Grafana

Contraseña del usuario admin:
kubectl -n monitoring get secrets monitoring-grafana -o jsonpath="{.data.admin-password}" | base64 -d ; echo

Abrir el acceso en http://localhost:3000:
kubectl port-forward -n monitoring svc/monitoring-grafana 3000:80
