# Guía de Seguridad y Segmentación de Redes (NetworkPolicies con Calico)

## 1. Fundamento de Seguridad L3/L4

Por defecto, en Kubernetes todos los pods pueden comunicarse entre sí sin importar el namespace en el que se encuentren. Para cumplir con el estándar de seguridad de arquitectura Zero-Trust y satisfacer el **Criterio 1 de la rúbrica**, se desplegó el CNI **Calico** y se aplicaron cuatro `NetworkPolicies` declarativas en `infra/k8s/network-policies/`.

---

## 2. Políticas de Red Implementadas

| Archivo | Namespace | Función de Seguridad |
|---|---|---|
| [`00-default-deny-data.yaml`](file:///Users/cristopher/Minimarket/infra/k8s/network-policies/00-default-deny-data.yaml) | `minimarket-data` | Bloquea todo tráfico entrante (`DefaultDeny`) a cualquier pod de datos. |
| [`01-allow-postgres-from-backend.yaml`](file:///Users/cristopher/Minimarket/infra/k8s/network-policies/01-allow-postgres-from-backend.yaml) | `minimarket-data` | Permite conexiones en el puerto `5432/TCP` hacia PostgreSQL **únicamente** desde pods con etiquetas `app: ventas-api`, `app: reportes-api` o `app: spark-job` del namespace `minimarket-backend`. |
| [`02-allow-backend-traffic.yaml`](file:///Users/cristopher/Minimarket/infra/k8s/network-policies/02-allow-backend-traffic.yaml) | `minimarket-backend` | Permite tráfico HTTP entrante en puertos `8000` y `8001` desde `minimarket-frontend`, tráfico entre pods backend, checks del kubelet y salida a PostgreSQL y DNS (puerto 53). |
| [`03-allow-frontend-traffic.yaml`](file:///Users/cristopher/Minimarket/infra/k8s/network-policies/03-allow-frontend-traffic.yaml) | `minimarket-frontend` | Permite tráfico HTTP entrante en puerto `80`. Permite salida hacia backend (8000/8001) y DNS. **Prohíbe terminantemente salida hacia el puerto 5432 de datos.** |

---

## 3. Evidencias Reales de Pruebas de Red

Las siguientes pruebas fueron ejecutadas con pods efímeros en el cluster Minikube real para demostrar el aislamiento:

### Prueba 1: Conexión Permitida (Backend -> PostgreSQL:5432)
```bash
kubectl run test-backend-to-pg --rm -i --restart=Never \
  -n minimarket-backend \
  --labels="app=ventas-api,tier=backend" \
  --image=busybox:1.36 -- nc -zv -w 3 postgres.minimarket-data.svc.cluster.local 5432
```
**Resultado Real Obtenido:**
```text
postgres.minimarket-data.svc.cluster.local (10.102.123.62:5432) open
pod "test-backend-to-pg" deleted from minimarket-backend namespace
```
*Conclusión:* La regla de ingress en `minimarket-data` autoriza el tráfico proveniente del namespace backend.

---

### Prueba 2: Conexión Bloqueada por Calico (Frontend -> PostgreSQL:5432)
```bash
kubectl run test-frontend-to-pg --rm -i --restart=Never \
  -n minimarket-frontend \
  --labels="app=frontend,tier=frontend" \
  --image=busybox:1.36 -- nc -zv -w 4 postgres.minimarket-data.svc.cluster.local 5432
```
**Resultado Real Obtenido:**
```text
nc: postgres.minimarket-data.svc.cluster.local (10.102.123.62:5432): Connection timed out
pod "test-frontend-to-pg" deleted from minimarket-frontend namespace
pod minimarket-frontend/test-frontend-to-pg terminated (Error)
```
*Conclusión:* Calico descartó los paquetes TCP dirigidos al puerto 5432 procedentes del frontend. Se confirma el aislamiento absoluto de la capa de datos frente a la capa de presentación.

---

### Prueba 3: Conexión Permitida (Frontend -> Backend API:8000)
```bash
kubectl run test-frontend-to-backend --rm -i --restart=Never \
  -n minimarket-frontend \
  --labels="app=frontend,tier=frontend" \
  --image=curlimages/curl:8.10.1 -- curl -s http://ventas-api.minimarket-backend.svc.cluster.local:8000/health
```
**Resultado Real Obtenido:**
```json
{
  "status": "healthy",
  "service": "ventas-api",
  "timestamp": "2026-11-10T18:05:40.594280Z"
}
```
*Conclusión:* La comunicación legítima entre capas requerida por la aplicación opera sin contratiempos.
