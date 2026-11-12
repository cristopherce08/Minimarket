# Guía de Pruebas de Carga y Demostración de HPA con `hey`
## MiniMarket Cloud — Criterio 4 (Resiliencia y Elasticidad)

Esta guía describe cómo ejecutar la prueba de estrés automatizada con `hey` para verificar en vivo el escalamiento horizontal elástico del microservicio `ventas-api` en Minikube.

---

## 1. Prerrequisitos

1. **Minikube Operativo con Metrics Server:**
   ```bash
   minikube status -p minimarket
   minikube -p minimarket addons enable metrics-server
   kubectl top pods -A
   ```
2. **Herramienta de Carga `hey` Instalada:**
   ```bash
   which hey || brew install hey
   ```
3. **Túnel de Acceso Local Activo:**
   El túnel puede ser provisto vía `minikube service frontend`:
   ```bash
   minikube -p minimarket service frontend -n minimarket-frontend --url
   ```
   O mediante el script de port-forward oficial:
   ```bash
   bash infra/k8s/port-forward.sh
   ```

---

## 2. Ejecución de la Prueba de Carga

El script automatizado se ubica en:
[`tests/load/generar_carga_hpa.sh`](../../tests/load/generar_carga_hpa.sh)

### Sintaxis y Parámetros

```bash
bash tests/load/generar_carga_hpa.sh [TARGET_URL] [DURACIÓN] [CONCURRENCIA]
```

- `TARGET_URL`: Endpoint HTTP a estresar. Por defecto `http://localhost:8005/api/v1/productos` (o la URL de Minikube service).
- `DURACIÓN`: Tiempo total de inyección de carga continua (e.g. `60s`, `90s`).
- `CONCURRENCIA`: Cantidad de workers HTTP simultáneos (e.g. `25` a `40`).

### Ejemplo de Ejecución en Vivo

```bash
# Ejecutar 45 segundos de carga con 30 workers concurrentes
bash tests/load/generar_carga_hpa.sh http://localhost:8005/api/v1/productos 45s 30
```

---

## 3. Comportamiento Observado y Evidencia de Autoescalado

Durante la prueba oficial documentada, se obtuvieron las siguientes métricas y estados:

### Fase 1: Estado Inicial (Reposado)
- **Réplicas:** 2 pods (`ventas-api-78x9r`, `ventas-api-d9n5j`).
- **Consumo de CPU:** `4m` por pod (~4% de los 100m requeridos).
- **HPA Target:** `cpu: 4%/25%`.

### Fase 2: Inyección de Carga HTTP
- **Throughput:** ~326 solicitudes por segundo continuas.
- **Total de solicitudes:** > 9,800 peticiones en 30 segundos.
- **Códigos HTTP:** 100% `200 OK`, 0 errores de servidor.
- **Latencia promedio:** 76.6 ms (P50: 89.5 ms, P95: 187.6 ms).
- **Consumo de CPU:** Saltó a 237% acumulado (> 50m por pod).

### Fase 3: Escalamiento Dinámico (Scale Up)
El controlador HPA detectó la sobrecarga y emitió los eventos de escalado:
```text
Events:
  Normal  SuccessfulRescale  New size: 4; reason: cpu resource utilization (percentage of request) above target
  Normal  SuccessfulRescale  New size: 5; reason: cpu resource utilization (percentage of request) above target
```
Se aprovisionaron 3 réplicas adicionales:
- `ventas-api-dcdkb` (1/1 Running)
- `ventas-api-lcj5r` (1/1 Running)
- `ventas-api-qx5gc` (1/1 Running)

### Fase 4: Operación a Capacidad Máxima (5 Réplicas)
El tráfico fue balanceado entre los 5 pods activos sin interrupción de servicio. Se confirmó una venta real vía `POST /api/v1/ventas` retornando HTTP 201 exitoso.

### Fase 5: Estabilización y Reducción (Scale Down)
Tras cesar el tráfico, el consumo de CPU retornó al reposo. Transcurridos los 60 segundos de la ventana de estabilización (`stabilizationWindowSeconds: 60`), el HPA comenzó la terminación ordenada de los pods excedentes, volviendo a las 2 réplicas mínimas.
