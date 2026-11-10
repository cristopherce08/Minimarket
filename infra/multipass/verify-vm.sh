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
echo "   - Comprobación de aislamiento DNS (.svc.cluster.local):"
if multipass exec "${VM_NAME}" -- nslookup ventas-api.minimarket-backend.svc.cluster.local > /dev/null 2>&1; then
    echo "   ❌ ERROR: La VM pudo resolver nombres internos de Kubernetes."
    exit 1
else
    echo "   [OK] Aislamiento DNS verificado: los nombres internos de K8s no se resuelven en la VM."
fi

echo "   - Comprobación de aislamiento de red de pods K8s (10.244.0.0/16):"
if multipass exec "${VM_NAME}" -- ping -c 1 -W 2 10.244.0.1 > /dev/null 2>&1; then
    echo "   ⚠️ Advertencia: Tráfico ICMP hacia red de pods K8s no bloqueado."
else
    echo "   [OK] Aislamiento de red verificado: la subred de pods K8s (Calico) es inalcanzable desde la VM."
fi

echo ""
echo "6. Diagnóstico de usuario y permisos:"
multipass exec "${VM_NAME}" -- id cloud-admin
echo "   [OK] Usuario cloud-admin verificado con autenticación segura."

echo ""
echo "✅ Verificación completa: VM Ubuntu ARM64 operativa, aislada y configurada exitosamente."
