#!/usr/bin/env bash
# ==============================================================================
# MiniMarket Cloud — Prueba de Carga y Autoescalado Horizontal (HPA)
# Integrante 2: Aplicación, Escalabilidad y HPA
# Rúbrica UTP: Criterio 4 (Resiliencia, Caos y Elasticidad)
# ==============================================================================

set -euo pipefail

# Parámetros configurables con valores por defecto
TARGET_URL="${1:-${TARGET_URL:-http://localhost:8005/api/v1/productos}}"
DURATION="${2:-${DURATION:-60s}}"
CONCURRENCY="${3:-${CONCURRENCY:-25}}"
NAMESPACE="minimarket-backend"
HPA_NAME="ventas-api-hpa"
DEPLOYMENT_NAME="ventas-api"

echo "======================================================================"
echo "  MINIMARKET CLOUD — Demostración de Autoescalado HPA con hey"
echo "======================================================================"
echo "  Destino:        ${TARGET_URL}"
echo "  Duración:       ${DURATION}"
echo "  Concurrencia:   ${CONCURRENCY} workers"
echo "  Namespace K8s:  ${NAMESPACE}"
echo "  HPA Evaluado:   ${HPA_NAME}"
echo "======================================================================"

# 1. Validar prerrequisitos
if ! command -v hey &> /dev/null; then
    echo "❌ Error: 'hey' no está instalado en el sistema."
    echo "   Instálalo con: brew install hey"
    exit 1
fi

if ! command -v kubectl &> /dev/null; then
    echo "❌ Error: 'kubectl' no está disponible."
    exit 1
fi

# Verificar conectividad con la API
echo "1. Comprobando conectividad con la API objetivo..."
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "${TARGET_URL}" || echo "000")
if [ "${HTTP_STATUS}" != "200" ]; then
    echo "❌ Fallo al conectar a ${TARGET_URL} (código HTTP: ${HTTP_STATUS})."
    echo "   Asegúrate de que el túnel port-forward esté activo:"
    echo "   kubectl port-forward -n ${NAMESPACE} svc/${DEPLOYMENT_NAME} 8005:8000 &"
    exit 1
fi
echo "   [OK] Conexión establecida exitosamente (HTTP 200)."

# 2. Capturar estado inicial
echo ""
echo "2. Estado inicial del clúster antes de la prueba:"
echo "--- HPA ---"
kubectl get hpa "${HPA_NAME}" -n "${NAMESPACE}"
echo "--- Pods activos de ${DEPLOYMENT_NAME} ---"
kubectl get pods -n "${NAMESPACE}" -l app=ventas-api -o wide

REPLICAS_INICIALES=$(kubectl get deployment "${DEPLOYMENT_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.replicas}')
echo "   Réplicas iniciales: ${REPLICAS_INICIALES}"

# 3. Lanzar monitor en segundo plano
echo ""
echo "3. Iniciando monitoreo periódico del HPA cada 5 segundos..."
MONITOR_FILE=$(mktemp)
(
    while true; do
        FECHA=$(date +"%T")
        HPA_INFO=$(kubectl get hpa "${HPA_NAME}" -n "${NAMESPACE}" --no-headers 2>/dev/null | awk '{print "CPU: " $3 " | Réplicas: " $6}' || echo "N/A")
        echo "[${FECHA}] ${HPA_INFO}" >> "${MONITOR_FILE}"
        sleep 5
    done
) &
MONITOR_PID=$!
trap 'kill "${MONITOR_PID}" 2>/dev/null || true; rm -f "${MONITOR_FILE}"' EXIT

# 4. Ejecutar la prueba de estrés con hey
echo ""
echo "4. 🚀 Disparando ráfaga de tráfico HTTP con hey..."
echo "   (Generando carga continua durante ${DURATION} sin modificar inventario)..."
echo ""

RESULT_FILE=$(mktemp)
hey -z "${DURATION}" -c "${CONCURRENCY}" "${TARGET_URL}" > "${RESULT_FILE}" 2>&1 || true

echo ""
echo "======================================================================"
echo "  RESULTADOS DEL BENCHMARK HTTP (hey)"
echo "======================================================================"
cat "${RESULT_FILE}"
rm -f "${RESULT_FILE}"

# 5. Detener monitor y mostrar trazabilidad de escalado
kill "${MONITOR_PID}" 2>/dev/null || true
echo ""
echo "5. Trazabilidad del consumo de CPU y autoescalado durante la carga:"
cat "${MONITOR_FILE}"

# 6. Estado pico / posterior de réplicas
echo ""
echo "6. Estado del HPA tras la finalización de la carga:"
kubectl get hpa "${HPA_NAME}" -n "${NAMESPACE}"
echo ""
echo "Pods activos de ${DEPLOYMENT_NAME}:"
kubectl get pods -n "${NAMESPACE}" -l app=ventas-api -o wide

REPLICAS_FINALES=$(kubectl get deployment "${DEPLOYMENT_NAME}" -n "${NAMESPACE}" -o jsonpath='{.status.replicas}')
echo ""
echo "======================================================================"
echo "  RESUMEN DE AUTOESCALADO"
echo "======================================================================"
echo "  Réplicas antes de la carga:  ${REPLICAS_INICIALES}"
echo "  Réplicas detectadas:         ${REPLICAS_FINALES}"
if [ "${REPLICAS_FINALES}" -gt "${REPLICAS_INICIALES}" ]; then
    echo "  ✅ ÉXITO: El HPA detectó el incremento de CPU y escaló réplicas correctamente."
else
    echo "  ℹ️  El clúster procesó el tráfico dentro del umbral de capacidad."
fi
echo "======================================================================"
