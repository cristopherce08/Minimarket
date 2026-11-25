# Guía de Ejecución Spark en Kubernetes y Soporte ARM64

## 1. Construcción de Imagen Docker Multi-Arquitectura

Para garantizar compatibilidad con Apple Silicon (M1/M2/M3 ARM64) y servidores AMD64, se utiliza la imagen oficial multi-arch `apache/spark:3.5.3-python3`:

- **Dockerfile Kubernetes**: [`src/spark/Dockerfile.k8s`](file:///Users/cristopher/Minimarket/src/spark/Dockerfile.k8s)
- **Comando de construcción**:
  ```bash
  docker build -t minimarket-spark:latest -f src/spark/Dockerfile.k8s src/spark
  ```
- **Carga directa en Minikube**:
  ```bash
  minikube -p minimarket image load minimarket-spark:latest
  ```

---

## 2. Configuración del Job Spark Distribuido

El Job se define en [`src/spark/k8s/spark-job.yaml`](file:///Users/cristopher/Minimarket/src/spark/k8s/spark-job.yaml):

- **Driver**:
  - Corre como Pod en el namespace `minimarket-backend`.
  - Modo: `--deploy-mode client`.
  - ServiceAccount: `spark` (vinculado a `spark-role` mediante RBAC de mínimo privilegio).
- **Ejecutores**:
  - `spark.executor.instances=2` (dos pods ejecutores reales creados dinámicamente por el driver).
  - `spark.executor.cores=1`
  - `spark.executor.memory=512m`
  - Etiqueta de seguridad: `spark.kubernetes.executor.label.app=spark-job` (autorizada por la NetworkPolicy de PostgreSQL).
- **Particionado**:
  - `NUM_PARTICIONES=8` (reparto equitativo de carga entre los ejecutores).
- **Volumen de datos**:
  - `NUM_VENTAS=200000` (doscientas mil ventas sintéticas generadas en memoria y procesadas por lotes).

---

## 3. Gestión Segura de Credenciales

El Job extrae la configuración de base de datos directamente del Secret preexistente de Kubernetes:

```yaml
env:
  - name: DATABASE_URL
    valueFrom:
      secretKeyRef:
        name: backend-db-secret
        key: DATABASE_URL
```

No se versionan contraseñas en Git ni se imprimen secretos en la salida estándar de Spark.

---

## 4. Ejecución del Job en el Clúster

```bash
# 1. Aplicar permisos RBAC
kubectl apply -f src/spark/k8s/spark-rbac.yaml

# 2. Desplegar el Job de Spark
kubectl apply -f src/spark/k8s/spark-job.yaml

# 3. Monitorear la creación del driver y los dos ejecutores
kubectl get pods -n minimarket-backend -l app=spark-job -w

# 4. Ver los logs del driver
kubectl logs -f job/ventas-spark -n minimarket-backend
```

---

## 5. Limpieza del Job

```bash
kubectl delete job ventas-spark -n minimarket-backend
```
