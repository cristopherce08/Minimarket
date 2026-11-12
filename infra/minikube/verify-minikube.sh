#!/usr/bin/env bash
# ==============================================================================
# MiniMarket Cloud — Verificación del Cluster Minikube y CNI Calico
# ==============================================================================

set -euo pipefail

PROFILE="minimarket"

echo "======================================================================"
echo "  MINIMARKET CLOUD — Verificación de Salud del Cluster"
echo "======================================================================"

echo "1. Estado de Minikube:"
minikube status -p "${PROFILE}"

echo ""
echo "2. Nodos del cluster Kubernetes:"
kubectl get nodes -o wide

echo ""
echo "3. Pods de sistema y CNI Calico en kube-system:"
kubectl get pods -n kube-system -o wide | grep -E "calico|coredns|kube-apiserver"

echo ""
echo "4. Capacidad de recursos del nodo:"
kubectl describe node minimarket | grep -A 8 "Capacity:"

echo ""
echo "5. Verificación de CNI Calico Controller:"
kubectl get pods -n kube-system -l k8s-app=calico-node -o wide
echo "✅ Cluster Minikube verificado satisfactoriamente."
