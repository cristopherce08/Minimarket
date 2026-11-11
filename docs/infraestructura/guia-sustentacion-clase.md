# Guía para la Sustentación en Clase — Integrante 1 (Infraestructura)

Esta guía condensa la demostración técnica en vivo para defender el módulo de **Infraestructura Cloud, Redes y Kubernetes** frente al docente o jurado evaluador en **menos de 5 minutos**.

---

## ⏱️ Guión de Demostración en 6 Pasos

### Paso 1: Mostrar el Cluster Minikube y CNI Calico (30 segundos)
Explica: *"El cluster fue dimensionado con 4 CPUs y 6 GB de RAM con el driver Docker y CNI Calico para soporte estricto de NetworkPolicies."*
```bash
# Mostrar nodo operativo y motor de contenedores containerd
kubectl get nodes -o wide

# Demostrar que los controladores de Calico están activos en kube-system
kubectl get pods -n kube-system -l k8s-app=calico-node
```

---

### Paso 2: Mostrar la Segmentación en Tres Namespaces y el Helm Chart (45 segundos)
Explica: *"El sistema se encuentra empaquetado como un Helm Chart modular distribuido en tres namespaces aislados: frontend, backend y data."*
```bash
# Mostrar la release de Helm desplegada
helm list

# Listar los recursos en cada namespace
kubectl get all -n minimarket-frontend
kubectl get all -n minimarket-backend
kubectl get all -n minimarket-data
```

---

### Paso 3: Demostrar las Pruebas de Aislamiento de Red (2 minutos) — ¡Momento Clave!
Explica: *"A diferencia de una red abierta, aplicamos NetworkPolicies L3/L4 con Calico. Demostraremos que el backend puede comunicarse con PostgreSQL, pero el frontend es bloqueado."*

**A. Conexión Permitida (Backend a PostgreSQL):**
```bash
kubectl run test-backend --rm -i --restart=Never \
  -n minimarket-backend --labels="app=ventas-api,tier=backend" \
  --image=busybox:1.36 -- nc -zv -w 3 postgres.minimarket-data.svc.cluster.local 5432
```
*Se observa:* `postgres.minimarket-data.svc.cluster.local:5432 open`.

**B. Conexión Bloqueada (Frontend a PostgreSQL):**
```bash
kubectl run test-frontend --rm -i --restart=Never \
  -n minimarket-frontend --labels="app=frontend,tier=frontend" \
  --image=busybox:1.36 -- nc -zv -w 3 postgres.minimarket-data.svc.cluster.local 5432
```
*Se observa:* `Connection timed out`. Explicar al profesor que el paquete fue descartado por las reglas de Calico.

---

### Paso 4: Demostración de la Aplicación en Vivo y Venta Real (1 minuto)
Ejecutar el script de acceso:
```bash
# En una pestaña de terminal ejecutar:
bash infra/k8s/port-forward.sh
```
Abrir el navegador en `http://localhost:8085`:
1. Mostrar la vista de **Inicio** y **Catálogo** cargando datos reales desde PostgreSQL en Kubernetes.
2. Ir a **Nueva Venta**, agregar 2 unidades de un producto y hacer clic en **Confirmar y Registrar Venta**.
3. Mostrar la emisión del ticket y la actualización instantánea del stock en almacén.

---

### Paso 5: Mostrar Límites de Recursos y Preparación HPA (30 segundos)
Explica: *"Cada contenedor tiene definidos requests y limits para permitir que el Integrante 2 aplique autoescalado horizontal (HPA) con Metrics Server."*
```bash
kubectl get pods -A -o custom-columns='NAMESPACE:metadata.namespace,NAME:metadata.name,CPU_REQ:spec.containers[*].resources.requests.cpu,CPU_LIM:spec.containers[*].resources.limits.cpu,MEM_REQ:spec.containers[*].resources.requests.memory,MEM_LIM:spec.containers[*].resources.limits.memory' | grep minimarket
```

---

### Paso 6: Aprovisionamiento con Multipass y Cloud-init (30 segundos)
Explica: *"Para el Criterio 1 de virtualización, contamos con el aprovisionamiento automatizado mediante Cloud-init de una VM Ubuntu ARM64 que actúa como jumpbox perimetral."*
```bash
# Mostrar archivo cloud-init declarativo
cat infra/multipass/cloud-init.yaml | head -n 30

# Si la VM está encendida:
bash infra/multipass/verify-vm.sh
```
