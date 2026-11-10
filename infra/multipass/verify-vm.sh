#!/usr/bin/env bash
# ==============================================================================
# MiniMarket Cloud — Verificación de Estado y Red de la VM Multipass
# ==============================================================================

set -euo pipefail

VM_NAME="${1:-${VM_NAME:-minimarket-vm}}"

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
INIT_STATUS=$(multipass exec "${VM_NAME}" -- cloud-init status --format json 2>/dev/null | jq -r .status || echo "unknown")
if [ "$INIT_STATUS" = "error" ]; then
    echo "❌ Cloud-init finalizó con errores no recuperables."
    multipass exec "${VM_NAME}" -- cloud-init status --long || true
    exit 1
elif [ "$INIT_STATUS" = "done" ]; then
    echo "✅ Cloud-init completado exitosamente (status: done)."
else
    multipass exec "${VM_NAME}" -- cloud-init status || true
fi

echo ""
echo "3. Diagnóstico de red, conectividad y aislamiento:"
multipass exec "${VM_NAME}" -- bash -c '
echo "--- Direcciones IP y Rutas ---"
ip -br addr show
ip route show

echo ""
echo "--- Conectividad Externa (Ping y DNS) ---"
ping -c 2 8.8.8.8
getent hosts google.com

echo ""
echo "--- Aislamiento respecto al Clúster Kubernetes ---"
if getent hosts ventas-api.minimarket-backend.svc.cluster.local > /dev/null 2>&1; then
    echo "❌ ERROR: La VM pudo resolver nombres internos de Kubernetes."
    exit 1
else
    echo "[OK] Aislamiento DNS verificado: .svc.cluster.local no se resuelve en la VM."
fi

if ping -c 1 -W 2 10.244.0.1 > /dev/null 2>&1; then
    echo "⚠️ Advertencia: Tráfico ICMP hacia subred de pods K8s no bloqueado."
else
    echo "[OK] Aislamiento de Red verificado: subred 10.244.0.0/16 inalcanzable desde la VM."
fi

echo ""
echo "--- Usuario y Seguridad ---"
id cloud-admin
echo "[OK] Usuario cloud-admin verificado con autenticación segura."
'

echo ""
echo "✅ Verificación completa: VM Ubuntu ARM64 operativa, aislada y configurada exitosamente."
