# Arquitectura del Cluster Kubernetes y Dimensionamiento — Integrante 1

## 1. Perfil del Cluster Minikube

El cluster opera bajo un perfil exclusivo para no interferir con otros proyectos o configuraciones globales del host:

- **Nombre de Perfil:** `minimarket`
- **Driver de Virtualización:** `docker` (containerd 2.3.4 sobre macOS Sequoia / Apple Silicon ARM64)
- **Versión de Kubernetes:** `v1.37.0`
- **Capacidad Asignada:**
  - **CPUs:** 4 cores virtuales dedicados (del procesador Apple M4 Pro de 14 cores).
  - **Memoria RAM:** 6144 MB (~6 GB) dedicados (del host de 24 GB).
- **Controlador CNI:** **Calico v3.28+** (`--cni=calico`), indispensable para la ejecución obligatoria de NetworkPolicies en Kubernetes.

---

## 2. Segmentación de Namespaces

La arquitectura divide las cargas en 3 namespaces principales:

```mermaid
graph TD
    subgraph "Cluster Kubernetes: minimarket"
        subgraph "minimarket-frontend"
            FE[Frontend SPA Nginx\nNodePort: 30080 / Port: 80]
        end

        subgraph "minimarket-backend"
            VAPI1[ventas-api Pod 1\nPort: 8000]
            VAPI2[ventas-api Pod 2\nPort: 8000]
            RAPI[reportes-api Pod 1\nPort: 8001]
        end

        subgraph "minimarket-data"
            PG[PostgreSQL 16 Pod\nPort: 5432\nPVC: 2Gi]
        end
    end

    FE -->|HTTP REST 8000/8001\n(Permitido)| VAPI1
    FE -->|HTTP REST 8000/8001\n(Permitido)| VAPI2
    FE -->|HTTP REST 8000/8001\n(Permitido)| RAPI

    VAPI1 -->|TCP 5432 ACID\n(Permitido)| PG
    VAPI2 -->|TCP 5432 ACID\n(Permitido)| PG
    RAPI -->|TCP 5432 Analítica\n(Permitido)| PG

    FE -.->|TCP 5432\n(BLOQUEADO POR CALICO)| PG
```

### Tabla de Namespaces
| Namespace | Propósito | Etiquetas Clave | Aislamiento de Red |
|---|---|---|---|
| `minimarket-frontend` | Aloja la interfaz web Nginx SPA | `name: minimarket-frontend`, `environment: production` | Ingress público puerto 80. Salida solo a backend y DNS. |
| `minimarket-backend` | Aloja microservicios FastAPI (`ventas-api`, `reportes-api`) | `name: minimarket-backend`, `environment: production` | Ingress solo desde frontend y monitoreo. Salida a BD y DNS. |
| `minimarket-data` | Aloja la base de datos PostgreSQL y su volumen | `name: minimarket-data`, `environment: production` | `DefaultDeny`. Entrada solo autorizada a backend en puerto 5432. |

---

## 3. Presupuesto y Límites de Recursos (CPU y RAM)

Cada pod tiene configurados explícitamente sus `requests` (garantía mínima) y `limits` (techo de contención):

| Componente | Namespace | Réplicas | CPU Request | CPU Limit | RAM Request | RAM Limit |
|---|---|:---:|:---:|:---:|:---:|:---:|
| **frontend** | `minimarket-frontend` | 1 | 50m | 200m | 64Mi | 128Mi |
| **ventas-api** | `minimarket-backend` | 2 | 100m c/u (200m) | 500m c/u (1000m) | 128Mi c/u (256Mi) | 256Mi c/u (512Mi) |
| **reportes-api** | `minimarket-backend` | 1 | 100m | 500m | 128Mi | 256Mi |
| **postgres** | `minimarket-data` | 1 | 100m | 500m | 128Mi | 512Mi |
| **Total Aplicación** | - | **5 pods** | **450m** | **2200m** | **576Mi** | **1408Mi** |

### Consumo Real Verificado en el Nodo Minikube
```text
Resource           Requests     Limits
--------           --------     ------
cpu                1450m (10%)  2200m (15%)
memory             746Mi (9%)   1578Mi (19%)
```
*Observación:* El cluster apenas utiliza el 10% de CPU y el 9% de RAM asignados al nodo, garantizando estabilidad total para la posterior inyección de carga con `hey`, Metrics Server (HPA) y Chaos Mesh.
