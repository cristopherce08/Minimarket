# Guía de Empaquetado y Despliegue con Helm (Criterio 2 UTP)

## 1. Estructura del Chart Modular (`infra/helm/minimarket`)

El empaquetado de Kubernetes sigue la especificación de Helm 3 (`apiVersion: v2`):

```text
infra/helm/minimarket/
├── Chart.yaml                          # Metadatos del chart (versión 0.1.0, appVersion 1.0.0)
├── values.yaml                         # Valores configurables por entorno
└── templates/
    ├── _helpers.tpl                    # Etiquetas y funciones comunes de interpolación
    ├── secret.yaml                     # Credenciales de base de datos
    ├── configmap-backend.yaml          # Variables de entorno para microservicios
    ├── configmap-frontend.yaml         # Configuración Nginx reverse proxy multicapa
    ├── postgres-pvc.yaml               # Reclamo de volumen persistente (StorageClass standard)
    ├── postgres-deployment.yaml        # Despliegue de PostgreSQL 16
    ├── postgres-service.yaml           # ClusterIP port 5432
    ├── ventas-api-deployment.yaml      # Despliegue ventas-api (2 réplicas)
    ├── ventas-api-service.yaml         # ClusterIP port 8000
    ├── reportes-api-deployment.yaml    # Despliegue reportes-api (1 réplica)
    ├── reportes-api-service.yaml       # ClusterIP port 8001
    ├── frontend-deployment.yaml        # Despliegue frontend SPA
    └── frontend-service.yaml           # NodePort port 80 (nodePort: 30080)
```

---

## 2. Validación y Pruebas del Chart

### A. Linter de Helm (`helm lint`)
```bash
helm lint infra/helm/minimarket
```
**Resultado Real:**
```text
==> Linting infra/helm/minimarket
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed
```

### B. Renderizado en Seco (`helm template`)
```bash
helm template minimarket infra/helm/minimarket
```
Verifica la correcta interpolación de variables sin necesidad de comunicarse con el cluster.

### C. Despliegue Oficial en Minikube (`helm install`)
```bash
helm install minimarket infra/helm/minimarket
```
**Resultado Real:**
```text
NAME: minimarket
LAST DEPLOYED: Tue Nov 10 13:01:11 2026
NAMESPACE: default
STATUS: deployed
REVISION: 1
```

---

## 3. Verificación de Health Checks y Probes

Todos los microservicios cuentan con sondas de vitalidad (`livenessProbe`) y disponibilidad (`readinessProbe`):

```bash
kubectl describe deployment/ventas-api -n minimarket-backend | grep -E "Liveness|Readiness"
```
**Salida:**
- **Liveness:** `http-get http://:8000/health delay=5s timeout=3s period=10s #success=1 #failure=3`
- **Readiness:** `http-get http://:8000/ready delay=5s timeout=3s period=5s #success=1 #failure=3`

---

## 4. Coordinación Inter-Módulos

1. **Con Integrante 2 (Desarrollo / HPA):**
   - El Deployment `ventas-api` se configuró con `resources.requests` y `resources.limits` precisos, condición indispensable para que el Metrics Server de Kubernetes pueda calcular el porcentaje de utilización de CPU/RAM y activar el `HorizontalPodAutoscaler` (HPA).
   - Se definieron 2 réplicas base para soportar balanceo de carga inicial.
2. **Con Integrante 3 (Datos / Persistencia):**
   - El chart incluye la plantilla de base de datos relacional y PVC base (`postgres-pvc`). El Integrante 3 puede personalizar el backend de almacenamiento o convertirlo en StatefulSet dedicado para Apache Spark sin alterar la estructura del Helm Chart.
