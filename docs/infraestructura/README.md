# Infraestructura Cloud y Kubernetes — Integrante 1 (MiniMarket Cloud)

Este directorio consolida la documentación técnica, evidencias de laboratorio y guías de reproducción correspondientes a las responsabilidades del **Integrante 1 (Especialista en Infraestructura Cloud, Virtualización, Kubernetes y Redes)** para el proyecto **MiniMarket Cloud** (Servicios Cloud - UTP).

---

## 🎯 Alcance y Criterios Cumplidos

| Criterio Rúbrica UTP | Entregables Clave | Estado | Evidencias Documentadas |
|---|---|:---:|---|
| **Criterio 1: Infraestructura Base y Redes** | Aprovisionamiento de VM Ubuntu ARM64 con Multipass y Cloud-init, diagnóstico de red, y NetworkPolicies L3/L4 en Kubernetes. | ✅ Verificado | [`guia-multipass-ubuntu.md`](guia-multipass-ubuntu.md)<br>[`guia-redes-networkpolicies.md`](guia-redes-networkpolicies.md) |
| **Criterio 2: Orquestación K8s y Empaquetado** | Cluster Minikube (driver Docker, CNI Calico, namespaces aislados), Helm Chart modular (`infra/helm/minimarket`), límites de CPU/RAM, probes y port-forward. | ✅ Verificado | [`arquitectura-k8s.md`](arquitectura-k8s.md)<br>[`guia-helm-despliegue.md`](guia-helm-despliegue.md)<br>[`guia-sustentacion-clase.md`](guia-sustentacion-clase.md) |

---

## 📂 Estructura de Documentación de Infraestructura

1. [`arquitectura-k8s.md`](arquitectura-k8s.md): Topología de nodos, segmentación por namespaces, dimensionamiento de CPU/RAM y configuración del CNI Calico.
2. [`guia-multipass-ubuntu.md`](guia-multipass-ubuntu.md): Procedimiento automatizado para instanciar la VM Ubuntu con cloud-init y diagnóstico de aislamiento de red.
3. [`guia-redes-networkpolicies.md`](guia-redes-networkpolicies.md): Resultados reales de pruebas con pods efímeros demostrando tráfico autorizado (Backend -> BD) vs. tráfico bloqueado (Frontend -> BD).
4. [`guia-helm-despliegue.md`](guia-helm-despliegue.md): Estructura del Chart Helm modular, linter, plantillas, `values.yaml` y verificación de despliegue.
5. [`guia-sustentacion-clase.md`](guia-sustentacion-clase.md): Script de demostración paso a paso para sustentar en vivo frente al docente en menos de 5 minutos.
