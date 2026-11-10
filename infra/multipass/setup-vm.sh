#!/usr/bin/env bash
# ==============================================================================
# MiniMarket Cloud — Script de Aprovisionamiento de VM Ubuntu (Multipass)
# Integrante 1: Infraestructura y Redes
# Criterio 1: Infraestructura Base y Redes
# ==============================================================================

set -euo pipefail

VM_NAME="minimarket-vm"
CPUS="2"
MEMORY="2G"
DISK="10G"
UBUNTU_RELEASE="noble" # Ubuntu 24.04 LTS
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLOUD_INIT_FILE="${SCRIPT_DIR}/cloud-init.yaml"

echo "======================================================================"
echo "  MINIMARKET CLOUD — Despliegue de VM Ubuntu ARM64 con Cloud-init"
echo "======================================================================"

if ! command -v multipass &> /dev/null; then
    echo "❌ Error: Multipass no está instalado en el sistema."
    echo "   Instálalo ejecutando: brew install --cask multipass"
    exit 1
fi

if multipass list | grep -q "${VM_NAME}"; then
    echo "⚠️ La máquina virtual '${VM_NAME}' ya existe."
    multipass info "${VM_NAME}"
    echo "Para recrearla: multipass delete --purge ${VM_NAME} && $0"
    exit 0
fi

echo "🚀 Creando máquina virtual '${VM_NAME}' (Ubuntu ${UBUNTU_RELEASE} ARM64)..."
echo "   - CPUs:   ${CPUS}"
echo "   - Memoria: ${MEMORY}"
echo "   - Disco:   ${DISK}"
echo "   - Archivo Cloud-init: ${CLOUD_INIT_FILE}"

multipass launch \
    --name "${VM_NAME}" \
    --cpus "${CPUS}" \
    --memory "${MEMORY}" \
    --disk "${DISK}" \
    --cloud-init "${CLOUD_INIT_FILE}" \
    "${UBUNTU_RELEASE}"

echo ""
echo "⏳ Esperando a que Cloud-init complete la inicialización de paquetes..."
multipass exec "${VM_NAME}" -- cloud-init status --wait

echo ""
echo "✅ VM Ubuntu '${VM_NAME}' aprovisionada exitosamente:"
multipass info "${VM_NAME}"

echo ""
echo "🎉 Ejecutando prueba de conectividad y herramientas en la VM..."
multipass exec "${VM_NAME}" -- /home/cloud-admin/test-connectivity.sh
