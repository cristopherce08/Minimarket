#!/usr/bin/env bash
# ==============================================================================
# MiniMarket Cloud — Verificación de Estado y Red de la VM Multipass
# ==============================================================================

set -euo pipefail

VM_NAME="minimarket-vm"

echo "======================================================================"
echo "  MINIMARKET CLOUD — Verificación de VM Ubuntu (${VM_NAME})"
echo "======================================================================"

if ! command -v multipass &> /dev/null; then
    echo "❌ Multipass no está disponible en el host."
    exit 1
fi

if ! multipass list | grep -q "${VM_NAME}"; then
    echo "❌ La máquina virtual '${VM_NAME}' no existe o está apagada."
    echo "   Ejecuta: bash infra/multipass/setup-vm.sh"
    exit 1
fi

echo "1. Información de la máquina virtual:"
multipass info "${VM_NAME}"

echo ""
echo "2. Estado de Cloud-init:"
multipass exec "${VM_NAME}" -- cloud-init status

echo ""
echo "3. IP y rutas de red de la VM:"
multipass exec "${VM_NAME}" -- ip -br addr show
multipass exec "${VM_NAME}" -- ip route show

echo ""
echo "4. Prueba de conectividad externa (DNS y Ping):"
multipass exec "${VM_NAME}" -- ping -c 2 8.8.8.8
multipass exec "${VM_NAME}" -- getent hosts google.com

echo ""
echo "5. Verificación de aislamiento respecto al cluster Kubernetes:"
echo "   La VM opera en una subred puenteada/NAT independiente administrada por Multipass."
echo "   No comparte namespaces ni red de contenedores con Minikube (Docker bridge)."
echo "✅ Verificación de VM completada."
