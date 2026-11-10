#!/usr/bin/env bash
# ==============================================================================
# MiniMarket Cloud — Script de Arranque Reproducible de Minikube
# Integrante 1: Infraestructura y Redes
# Criterio 2: Orquestación K8s y Empaquetado
# ==============================================================================

set -euo pipefail

PROFILE="minimarket"
DRIVER="docker"
CPUS="4"
MEMORY="6144" # 6 GB
CNI="calico"

echo "======================================================================"
echo "  MINIMARKET CLOUD — Inicialización de Cluster Minikube"
echo "======================================================================"
echo "Perfil:    ${PROFILE}"
echo "Driver:    ${DRIVER}"
echo "CPUs:      ${CPUS}"
echo "Memoria:   ${MEMORY} MB"
echo "CNI:       ${CNI} (Compatible con NetworkPolicies)"
echo "======================================================================"

# Verificar si Minikube ya está corriendo
if minikube status -p "${PROFILE}" 2>/dev/null | grep -q "Running"; then
    echo "✅ El cluster '${PROFILE}' ya se encuentra activo."
    minikube status -p "${PROFILE}"
    exit 0
fi

echo "🚀 Iniciando Minikube..."
minikube start \
    -p "${PROFILE}" \
    --driver="${DRIVER}" \
    --cpus="${CPUS}" \
    --memory="${MEMORY}" \
    --cni="${CNI}"

echo ""
echo "📦 Cargando imágenes locales en el cluster Minikube..."
for img in minimarket-frontend:latest minimarket-ventas-api:latest minimarket-reportes-api:latest postgres:16-alpine; do
    if docker image inspect "${img}" >/dev/null 2>&1; then
        echo "   Cargando imagen: ${img}..."
        minikube -p "${PROFILE}" image load "${img}"
    fi
done

echo ""
echo "✅ Minikube configurado y listo:"
kubectl cluster-info
kubectl get nodes -o wide
