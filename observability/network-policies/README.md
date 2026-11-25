# NetworkPolicies del MiniMarket

Este documento explica qué reglas de red se aplicaron al clúster, por qué se hicieron y cómo se comprobó que funcionan. Corresponde a la corrección del revisor sobre las NetworkPolicies, que antes no existían.

## 1. ¿Por qué hacían falta?

En Kubernetes, por defecto, cualquier pod puede conectarse a cualquier otro. Antes de aplicar estas reglas, el comando `kubectl get networkpolicy -A` respondía *No resources found*, así que, por ejemplo, el frontend podía hablar directo con la base de datos.

Una NetworkPolicy es una regla que define qué pods pueden conectarse a cuáles. En este clúster las hace cumplir Calico.

## 2. Qué se aplicó

Hay 7 políticas, en dos archivos.

| Archivo | Namespace | Qué hace |
|---|---|---|
| `01-postgres-solo-apis.yaml` | `minimarket-data` | Postgres (5432) solo acepta conexiones de `ventas-api`, `reportes-api` y el job `alembic-migration` |
| `02-backend-ingress.yaml` | `minimarket-backend` | Bloquea todo lo que entra a las APIs y deja pasar solo lo necesario (tabla siguiente) |

Lo que el archivo `02` deja pasar hacia las APIs:

| Quién entra | Puertos | Para qué |
|---|---|---|
| Gateway de Istio | 8000, 8001 | Es la entrada de los usuarios |
| Pod `frontend` | 8000, 8001 | Su nginx reenvía las peticiones a las APIs |
| Prometheus | 8000, 8001, 15090 | Lee las métricas de las APIs y de los sidecars |
| Pods del mismo namespace | todos | Comunicación interna |
| Nodo de minikube (`192.168.49.2`) | todos | Las revisiones de salud (probes) del kubelet |

## 3. Alcance y limitaciones

- Solo se restringe el tráfico de **entrada** (ingress). El tráfico de salida (egress) sigue abierto.
- Se decidió así porque restringir la salida exige permitir DNS y la comunicación de los sidecars de Istio con `istiod`, y es lo que más fácil rompe la app. Queda como mejora.
- Los namespaces `minimarket-frontend`, `istio-system` y `monitoring` no tienen políticas propias.

## 4. Cómo se probó

Las pruebas se hicieron con la app en marcha y solo con operaciones de lectura, para no tocar la base de datos real.

### Pruebas positivas (lo permitido debe funcionar)

| Prueba | Resultado |
|---|---|
| Pod nuevo con label `app=ventas-api` → Postgres:5432 | `open` |
| `ventas-api` `/ready` (consulta la BD) | 200, `database: connected` |
| Gateway → `ventas-api` (`GET /api/v1/productos`) | HTTP 200 |
| Gateway → `reportes-api` (`/health`) | HTTP 200 |
| Frontend → `ventas-api` | Conecta |
| Prometheus: targets de `minimarket-backend` | Los 3 en `UP` (1 de `reportes-api` y 2 de `ventas-api`) |

### Pruebas negativas (lo no permitido debe bloquearse)

| Prueba | Resultado |
|---|---|
| Pod en `default` → Postgres:5432 | `Connection timed out` |
| Pod con label `app=otro`, mismo namespace de las APIs → Postgres:5432 | `Connection timed out` |
| Frontend → Postgres:5432 | Bloqueado (la conexión no se completa) |
| Pod en `default` → `ventas-api`:8000 | `Connection timed out` |
| Postgres → `ventas-api`:8000 | Bloqueado (la conexión no se completa) |

Una nota importante: las políticas no cortan conexiones que ya estaban abiertas. Por eso la prueba positiva de Postgres se hizo con un pod nuevo, para forzar una conexión nueva, y los targets de Prometheus se revisaron otra vez unos minutos después de aplicar las reglas. Seguían en `UP`, con lecturas posteriores a la aplicación.

## 5. Cómo aplicarlas y cómo revertirlas

```bash
kubectl apply -f observability/network-policies/01-postgres-solo-apis.yaml
kubectl apply -f observability/network-policies/02-backend-ingress.yaml

# Verificar
kubectl get networkpolicy -A

# Revertir
kubectl delete -f observability/network-policies/02-backend-ingress.yaml
kubectl delete -f observability/network-policies/01-postgres-solo-apis.yaml
```
