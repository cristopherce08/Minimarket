# Políticas de red de MiniMarket

El conjunto canónico está en [`infra/k8s/network-policies/`](../../infra/k8s/network-policies/). Las políticas de Kubernetes suman permisos. Un `default-deny` deja de ser suficiente si una regla antigua sigue autorizando el mismo tráfico.

| Flujo | Autorización |
|---|---|
| PostgreSQL TCP 5432 | Desde `ventas-api`, `reportes-api`, `spark-job` y `alembic-migration` en `minimarket-backend`. |
| APIs TCP 8000/8001 | Desde los pods del frontend, las otras APIs del mismo namespace, Istio Ingress Gateway en `istio-system` y Prometheus en `monitoring`. |
| Envoy | Salida desde las APIs hacia `istiod` TCP 15012 para xDS y certificados. El PodMonitor lee el gateway directamente en TCP 15090. |
| DNS | TCP/UDP 53 hacia los pods `k8s-app=kube-dns` del namespace `kube-system`. |
| Spark | TCP 7078/7079 entre pods `app=spark-job`, además de acceso a PostgreSQL y al API Server mediante su ServiceAccount. |
| Frontend | HTTP de entrada, salida hacia las APIs y DNS. La conexión directa a PostgreSQL queda bloqueada. |
| Pruebas | El subconjunto [`pruebas/`](../../infra/k8s/network-policies/pruebas/) exige identidad y namespace de pruebas. El único destino PostgreSQL permitido es el pod `postgres-pruebas`. |

Los selectores de namespaces usan `kubernetes.io/metadata.name`. Calico permite las sondas del kubelet desde el nodo que aloja el pod. La regla canónica prescinde de excepciones para rangos IP de Minikube. Los trabajos Spark y Alembic se ejecutan sin sidecar.

Prometheus lee `/metrics` por los mismos puertos HTTP de las APIs. NetworkPolicy opera a nivel TCP y autoriza esos puertos al pod de Prometheus. La selección de la ruta `/metrics` la hace ServiceMonitor.

## Actualización de un clúster existente

Primero confirma el contexto, el CNI, los labels de cada pod y los namespaces. En un laboratorio que usa otros nombres de namespaces, adapta coherentemente `metadata.namespace` y los selectores de namespace antes de validar.

```bash
kubectl config current-context
kubectl get namespaces --show-labels
kubectl get networkpolicy -A
kubectl apply --dry-run=server -f infra/k8s/network-policies/
kubectl diff -f infra/k8s/network-policies/
```

Las políticas `allow-postgres-from-backend`, `allow-backend-traffic`, `allow-frontend-traffic` y `backend-default-deny-ingress` se actualizan con el mismo nombre. Después de aplicar el conjunto canónico en el entorno autorizado, revisa estas políticas heredadas por nombre exacto.

| Namespace | Políticas que pueden haber quedado instaladas |
|---|---|
| `minimarket-data` | `postgres-solo-apis` |
| `minimarket-backend` | `backend-allow-ingressgateway`, `backend-allow-frontend`, `backend-allow-prometheus`, `backend-allow-same-namespace`, `backend-allow-kubelet` |

Para cada candidata, compara su especificación con `git show baad4f2:observability/network-policies/01-postgres-solo-apis.yaml` o `git show baad4f2:observability/network-policies/02-backend-ingress.yaml`. Verifica las anotaciones y el administrador del recurso. Conserva una copia y elimina solo las coincidencias confirmadas como versiones anteriores de MiniMarket.

```bash
kubectl -n NAMESPACE get networkpolicy NOMBRE -o yaml
kubectl -n NAMESPACE delete networkpolicy NOMBRE --dry-run=server
kubectl -n NAMESPACE delete networkpolicy NOMBRE
```

Abre conexiones nuevas para verificar que frontend y pods sin rol queden bloqueados hacia PostgreSQL. Comprueba también frontend → API, API → PostgreSQL, DNS, sondas, gateway y scraping antes de dar por terminada la actualización. En una API con sidecar, un SYN aceptado por Envoy no acredita que el PostgreSQL remoto respondió. Usa una conexión de aplicación o una respuesta del protocolo PostgreSQL.
