# Diagnóstico del Entorno de Ejecución — Etapa 0

Este documento consolida la inspección técnica realizada sobre el equipo anfitrión para evaluar su viabilidad respecto al despliegue completo de **MiniMarket Cloud**.

---

## 1. Características del Sistema Host

| Parámetro | Valor Detectado | Estado / Evaluación |
|---|---|---|
| **Sistema Operativo** | macOS Sequoia (Version 26.6.2, Darwin Kernel 25.6.0) | Soportado para desarrollo Cloud-native |
| **Arquitectura** | `arm64` (Apple Silicon) | Compatible con contenedores multi-arch |
| **Procesador (CPU)** | Apple M4 Pro (14 núcleos: físicos y lógicos) | **Excelente capacidad** de cómputo paralelo |
| **Memoria RAM** | 25.769.803.776 bytes (~24 GB LPDDR5) | **Suficiente** para cluster K8s completo (~12 GB requeridos) |
| **Almacenamiento** | 208 GiB disponibles en `/System/Volumes/Data` | **Óptimo** para imágenes Docker y volúmenes persistentes |

---

## 2. Inventario de Herramientas y Estado de Instalación

| Herramienta | Ruta / Detección | Versión Detectada | Estado Operativo | Acción Requerida para Etapa 1 |
|---|---|---|---|---|
| **Git** | `/usr/bin/git` | `2.50.1` | ✅ Listo | Ninguna |
| **Python** | `/opt/homebrew/bin/python3` | `3.14.7` | ✅ Listo | Se recomienda usar entorno virtual (`venv`) con Python 3.11/3.12 si librerías de Spark lo requieren |
| **Node.js** | `~/.nvm/.../bin/node` | `v24.21.0` (npm 11.x) | ✅ Listo | Frontend utiliza Vanilla JS (sin build step forzoso) |
| **Docker CLI** | `/usr/local/bin/docker` | `29.9.2` (Docker Desktop 4.98.0) | ⚠️ Servicio inactivo | Iniciar Docker Desktop antes de levantar Minikube |
| **kubectl** | `/usr/local/bin/kubectl` | `v1.36.1` (darwin/arm64) | ✅ Listo | Compatible con clusters v1.28 - v1.36 |
| **Minikube** | *No encontrado* | N/A | ❌ Pendiente | Instalar vía `brew install minikube` |
| **Helm** | *No encontrado* | N/A | ❌ Pendiente | Instalar vía `brew install helm` |
| **Multipass** | *No encontrado* | N/A | ❌ Pendiente | Opcional para demo Ubuntu VM (`brew install --cask multipass`) |
| **hey (Load test)**| *No encontrado* | N/A | ❌ Pendiente | Instalar vía `brew install hey` |
| **Java / JRE** | Wrapper `/usr/bin/java` | Sin JRE en host | ℹ️ En contenedor | Spark ejecutará dentro de contenedores Docker/K8s |
| **Package Manager**| `/opt/homebrew/bin/brew` | Homebrew activo | ✅ Listo | Facilita la instalación de binarios faltantes |

---

## 3. Factibilidad de Máquina Virtual Ubuntu

El equipo anfitrión es una arquitectura **Apple Silicon (`arm64`)**:
1. **Opción A (Multipass Nativo):** Canonical Multipass funciona sobre el hypervisor nativo de macOS (`Hypervisor.framework`) y descarga automáticamente imágenes oficiales de **Ubuntu 22.04 / 24.04 LTS para ARM64**. Permite aplicar scripts de aprovisionamiento declarativo mediante **Cloud-init** sin sobrecargar el sistema.
2. **Opción B (Minikube con driver Docker):** Minikube puede ejecutarse directamente sobre el motor de Docker Desktop creando un nodo Linux containerizado. Esta es la opción más eficiente en consumo de memoria para sostener el cluster completo en un solo host.
3. **Estrategia Combinada:** Para satisfacer con excelencia la rúbrica académica (que solicita redes con Multipass y Cloud-init):
   - Se diseñará el archivo `infra/multipass/cloud-init.yaml` para levantar una VM Ubuntu de prueba/jumpbox si el evaluador lo solicita.
   - El cluster principal de Kubernetes operará sobre **Minikube (driver docker)** con 10-12 GB de RAM asignados para garantizar estabilidad al ejecutar Istio, Chaos Mesh, Prometheus, Spark y PostgreSQL en simultáneo.

---

## 4. Presupuesto y Asignación de Recursos para el Cluster

| Componente / Servicio | Réplicas | CPU Estimada | RAM Estimada |
|---|---|---|---|
| **Control Plane Minikube** | 1 nodo | 1.0 core | 1.5 GB |
| **PostgreSQL 16** | 1 pod (StatefulSet) | 0.5 core | 512 MB |
| **ventas-api (FastAPI)** | 2 a 5 pods (HPA) | 0.5 - 1.5 cores | 256 MB - 512 MB |
| **reportes-api (FastAPI)**| 1 a 2 pods | 0.5 core | 256 MB |
| **Apache Spark (Driver/Exec)**| On-demand | 1.5 cores | 1.5 GB |
| **Frontend Nginx (SPA)** | 1 a 2 pods | 0.2 core | 128 MB |
| **Istio Service Mesh (Istiod + Proxies)** | 1 daemon + sidecars | 1.0 core | 1.2 GB |
| **Chaos Mesh Controller & Daemon** | 1 daemon | 0.5 core | 512 MB |
| **kube-prometheus-stack + Grafana** | 3 pods | 1.0 core | 2.0 GB |
| **Metrics Server** | 1 pod | 0.1 core | 100 MB |
| **Margen de seguridad del Cluster** | - | 1.2 cores | 1.5 GB |
| **TOTAL CLUSTER ESTIMADO** | - | **~8 cores** | **~10.0 - 11.5 GB** |
| **RECURSOS DISPONIBLES EN HOST** | Host M4 Pro | **14 cores** | **24.0 GB** |

> [!NOTE]
> La máquina anfitriona cuenta con 14 núcleos y 24 GB de memoria física. El cluster requerirá aproximadamente un 45-50% de la capacidad total del equipo, dejando 12 GB de RAM libres para el sistema operativo macOS y las herramientas de desarrollo. No existe riesgo de estrangulamiento de hardware (*OOMKilled* general).

---

## 5. Matriz de Compatibilidad ARM64

- **PostgreSQL (`postgres:16-alpine`):** Imágenes oficiales multi-arch `linux/arm64`.
- **FastAPI / Python (`python:3.11-slim`):** Soporte nativo `linux/arm64`.
- **Apache Spark (`apache/spark:3.5.1` o `bitnami/spark`):** Soporte oficial multi-arch `arm64`.
- **Istio (`istioctl 1.22+`):** Binarios oficiales darwin-arm64 e imágenes de proxy `arm64`.
- **Chaos Mesh (v2.6+):** Cuenta con imágenes oficiales `linux/arm64`.
- **kube-prometheus-stack:** Totalmente compatible con arquitecturas ARM64.

---

## 6. Prerrequisitos para Autorizar en Etapa 1

Cuando el usuario lo autorice, las únicas instalaciones a realizar vía Homebrew serán:
```bash
brew install minikube helm hey
# Opcional si se desea ejecutar la VM Ubuntu física local:
brew install --cask multipass
```
Y arrancar la aplicación **Docker Desktop**.
