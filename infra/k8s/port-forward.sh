#!/usr/bin/env bash
# ==============================================================================
# MiniMarket Cloud — Script de Acceso Local al Cluster Kubernetes (Port-Forward)
# Integrante 1: Infraestructura y Redes
# ==============================================================================

set -euo pipefail

echo "======================================================================"
echo "  MINIMARKET CLOUD — Túnel de Acceso Local (Port-Forward K8s)"
echo "======================================================================"
echo "Mapeando puertos hacia los microservicios en Minikube:"
echo "  🌐 Frontend Web:    http://localhost:8085  -> svc/frontend:80 (minimarket-frontend)"
echo "  🛒 Ventas API:      http://localhost:8005  -> svc/ventas-api:8000 (minimarket-backend)"
echo "  📈 Reportes API:    http://localhost:8006  -> svc/reportes-api:8001 (minimarket-backend)"
echo "======================================================================"
echo "Presiona Ctrl + C para detener los túneles."
echo ""

trap 'kill $(jobs -p) 2>/dev/null || true' EXIT

kubectl port-forward -n minimarket-frontend svc/frontend 8085:80 &
kubectl port-forward -n minimarket-backend svc/ventas-api 8005:8000 &
kubectl port-forward -n minimarket-backend svc/reportes-api 8006:8001 &

wait
