# MiniMarket Cloud — Sistema de Ventas e Inventario Cloud-Native

Proyecto académico diseñado para el curso de **Servicios Cloud (UTP)**. MiniMarket Cloud es una solución cloud-native minimalista orientada a demostrar la implementación integral de arquitecturas de microservicios, orquestación en Kubernetes, procesamiento distribuido de datos, service mesh, ingeniería del caos y observabilidad avanzada.

---

## 🎯 Alcance Funcional

El sistema se enfoca estrictamente en las operaciones esenciales de bodega:
1. **Gestión básica de productos:** Registro y consulta de catálogo (nombre, precio unitario, stock).
2. **Registro de ventas multi-ítem:** Transacciones atómicas de compra con múltiples productos.
3. **Descuento automático de inventario:** Control de concurrencia y validación de stock disponible.
4. **Reportes analíticos:** Agregaciones diarias y ranking de productos más vendidos mediante procesamiento distribuido.

*Nota:* Fuera de alcance por diseño: pasarelas de pago, facturación electrónica SUNAT, contabilidad general, roles complejos de usuario y gestión de proveedores.

---

## 🏗️ Stack Tecnológico

| Capa / Dominio | Tecnología | Propósito |
|---|---|---|
| **Frontend** | HTML5, CSS3, Vanilla JavaScript (SPA) | Interfaz ligera de punto de venta y catálogo |
| **Backend APIs** | Python 3.11+, FastAPI, Uvicorn, Pydantic | Microservicios asíncronos de ventas y reportes |
| **Base de Datos** | PostgreSQL 16 | Almacenamiento relacional transaccional (ACID) |
| **Big Data** | Apache Spark 3.5+ (PySpark) | Procesamiento distribuido de métricas y analítica |
| **Contenedores** | Docker (Multi-stage builds) | Empaquetado estandarizado y portable |
| **Orquestación** | Kubernetes (Minikube local) | Gestión de ciclo de vida, replicación y autoescalado |
| **Empaquetado K8s** | Helm 3 | Chart modular para despliegue reproducible |
| **Networking & Seguridad** | Docker Networks, K8s NetworkPolicies, Multipass (Cloud-init) | Aislamiento de capas L3/L4 y provisión automatizada |
| **Service Mesh** | Istio | Enrutamiento inteligente, mTLS y telemetría de red |
| **Escalamiento** | Metrics Server + Horizontal Pod Autoscaler (HPA) | Autoescalado elástico basado en utilización de CPU/RAM |
| **Ingeniería del Caos** | Chaos Mesh | Pruebas de resiliencia mediante inyección de fallas |
| **Observabilidad** | kube-prometheus-stack (Prometheus + Grafana) | Recolección de métricas y tableros en tiempo real |
| **Pruebas de Carga** | `hey` | Generador HTTP de estrés para validación de HPA |
| **Dimensionamiento Físico** | Bash Shell Script | Modelo de cálculo de consumo energético, BTU y TCO |

---

## 👥 Equipo y División de Responsabilidades

| Integrante | Rol Principal | Módulos Asignados |
|---|---|---|
| **Integrante 1** | Especialista en Infraestructura & Cloud | Provisión Multipass/Cloud-init, Minikube, Helm Charts, NetworkPolicies |
| **Integrante 2** | Desarrollador Fullstack & Resiliencia | Frontend SPA, `ventas-api` (FastAPI), Dockerfiles, métricas y HPA |
| **Integrante 3** | Ingeniero de Datos & Persistencia | PostgreSQL DDL/DML, `reportes-api`, Jobs analíticos PySpark |
| **Integrante 4** | Ingeniero de Observabilidad & Caos | Istio Service Mesh, Chaos Mesh, Prometheus/Grafana, `hey`, Script TCO |

Para mayor detalle, consultar el archivo [`docs/plan-integrantes.md`](file:///Users/cristopher/Minimarket/docs/plan-integrantes.md).

---

## 📂 Estructura del Repositorio

```text
Minimarket/
├── docs/                      # Documentación arquitectónica y de sustentación
│   ├── arquitectura.md        # Arquitectura de software, datos e infraestructura
│   ├── rubrica-checklist.md   # Mapeo y evidencias de los 5 criterios de la rúbrica
│   ├── plan-integrantes.md    # Asignación detallada de tareas por integrante
│   ├── contratos-api.md       # Especificación OpenAPI de endpoints y payloads
│   └── diagnostico-entorno.md # Reporte técnico del hardware y herramientas del host
├── infra/                     # Infraestructura como código y despliegue
│   ├── multipass/             # Scripts de aprovisionamiento de VM Ubuntu y cloud-init
│   ├── minikube/              # Guías y scripts de inicialización del cluster
│   ├── helm/                  # Chart de Helm modular para MiniMarket Cloud
│   ├── k8s/                   # Manifiestos puros (Namespaces, NetworkPolicies, HPA)
│   └── tco/                   # Script de dimensionamiento físico y cálculo TCO
├── src/                       # Código fuente de las aplicaciones
│   ├── frontend/              # Aplicación Web cliente (HTML/CSS/JS)
│   ├── ventas-api/            # Microservicio transaccional de ventas y catálogo
│   ├── reportes-api/          # Microservicio de agregaciones analíticas
│   └── spark/                 # Jobs por lotes de PySpark
├── observability/             # Configuración de observabilidad y resiliencia
│   ├── istio/                 # Gateway, VirtualServices y DestinationRules
│   ├── prometheus-grafana/    # ServiceMonitors y Dashboards JSON
│   └── chaos-mesh/            # Experimentos de red, fallos de pods y latencia
├── tests/                     # Pruebas automatizadas y de estrés
│   └── load/                  # Scripts de pruebas de carga con hey
├── .gitignore
└── README.md
```

---

## 📋 Estado del Proyecto

- **Etapa 0 (Actual):** Diagnóstico de entorno, planificación técnica y estructura base completada.
- **Etapa 1 (Siguiente):** Preparación del entorno de ejecución (herramientas locales / Minikube) y modelado de datos.
