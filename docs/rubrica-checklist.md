# Rúbrica UTP de MiniMarket Cloud

Esta matriz usa el [informe de validación final](validacion-final-utp.md) para los resultados del pre-release. La calificación definitiva corresponde al docente.

| Criterio | Requisito e implementación | Evidencia y estado |
|---|---|---|
| 1. Infraestructura Base y Redes | Multipass y [Cloud-init](../infra/multipass/cloud-init.yaml), [tres namespaces](../infra/k8s/namespaces/namespaces.yaml) y [políticas Calico](../infra/k8s/network-policies/). | Evidencia de la VM Ubuntu ARM64 en la [guía Multipass](infraestructura/guia-multipass-ubuntu.md). En la integración se probaron DNS, sondas y conexiones permitidas y denegadas en Minikube. **Aprobado en el alcance documentado.** |
| 2. Orquestación K8s y Empaquetado | [Minikube con Calico](../infra/minikube/setup-minikube.sh), [Helm](../infra/helm/minimarket/) y límites y requests CPU/RAM. | Chart instalado en namespaces de validación, Deployments Ready y cinco Dockerfiles validados con BuildKit. **Aprobado en el alcance documentado.** |
| 3. Procesamiento y Datos Locales | PostgreSQL 16 con [PV/PVC](../infra/helm/minimarket/templates/postgres-pvc.yaml), [Alembic](datos/guia-migraciones-alembic.md), [Spark](../src/spark/k8s/) y [contratos API](contratos-api.md). | Se mantuvo el baseline de 41 pruebas y se añadieron tres de idempotencia. Consulta en el informe la comprobación de Spark distribuido y persistencia. **Aprobado en el alcance documentado.** |
| 4. Resiliencia, Caos y Elasticidad | [HPA](../infra/helm/minimarket/templates/ventas-api-hpa.yaml), [Istio](../observability/istio/) y [Chaos Mesh](../observability/chaos-mesh/) con PostgreSQL de pruebas separado. | Cuatro experimentos inyectados en pods de prueba, reposición del pod eliminado y errores 503 registrados durante `pod-failure`. El informe detalla el margen de escalamiento demostrado y las limitaciones de la prueba. **Aprobado en el alcance documentado.** |
| 5. Telemetría y Dimensionamiento Físico | [Prometheus y Grafana](../observability/prometheus-grafana/), PromQL para ambas APIs y el gateway, y [script de TCO](../infra/tco/dimensionamiento_tco.sh). | El informe registra los targets, las consultas comprobadas y los cálculos manuales de Watts, BTU/h, UPS, energía y costos. **Aprobado en el alcance documentado.** |

Para repetir la evaluación de red o de caos, usa la [guía de políticas](infraestructura/guia-redes-networkpolicies.md) y el [procedimiento del laboratorio](../observability/README.md).
