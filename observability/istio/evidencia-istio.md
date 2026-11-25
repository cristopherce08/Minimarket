# Evidencia de Istio: proxies y estado de mTLS

Este documento responde a la corrección del revisor sobre Istio: mostrar que los proxies están funcionando y aclarar en qué modo está el mTLS. Los datos se tomaron el 2026-11-24 con el clúster `minimarket`, usando solo comandos de lectura (más 20 peticiones `GET` por el gateway para generar tráfico).

## 1. Estado de los proxies

Comando:

```bash
istioctl proxy-status
```

| Pod | Namespace | Versión | Tipos suscritos |
|---|---|---|---|
| `istio-ingressgateway` | `istio-system` | 1.32.0 | CDS, LDS, EDS, RDS |
| `istio-egressgateway` | `istio-system` | 1.32.0 | CDS, LDS, EDS |
| `ventas-api` (2 réplicas) | `minimarket-backend` | 1.32.0 | CDS, LDS, EDS, RDS |
| `reportes-api` | `minimarket-backend` | 1.32.0 | CDS, LDS, EDS, RDS |

En total son 5 proxies conectados a `istiod`, todos con la misma versión. Los pods de las APIs muestran `2/2` en `READY`: la aplicación y el sidecar de Istio. El egressgateway no recibe rutas (RDS) porque no tiene ninguna configurada.

Nota: el job `alembic-migration` aparece como `Completed` y no cuenta, porque ya terminó.

## 2. Estado del mTLS

El mTLS es el cifrado y la verificación de identidad entre dos servicios. Istio tiene dos modos:

- **Permisivo (PERMISSIVE):** acepta conexiones cifradas y también en texto plano.
- **Estricto (STRICT):** solo acepta conexiones cifradas.

Comando:

```bash
kubectl get peerauthentication -A
```

Resultado: `No resources found`. No se definió ninguna política, así que **el mTLS está en modo permisivo**, que es el valor por defecto de Istio.

## 3. Prueba de que el tráfico entre servicios sí va cifrado

Se enviaron 20 peticiones `GET /api/v1/productos` desde el gateway y se leyeron las métricas del proxy que recibe (el de `ventas-api`):

```bash
kubectl exec -n minimarket-backend <pod-ventas-api> -c istio-proxy -- \
  pilot-agent request GET stats/prometheus | grep istio_requests_total
```

| Origen de la petición | `connection_security_policy` | Peticiones (en las 2 réplicas) |
|---|---|---|
| `istio-ingressgateway` (tiene sidecar) | `mutual_tls` | 20 (16 + 4) |
| Orígenes sin sidecar (frontend, Prometheus, kubelet) | `none` | 732 (365 + 367) |

Las 20 peticiones del gateway llegaron cifradas y con identidad verificada. En las métricas aparece la identidad del gateway (`spiffe://cluster.local/ns/istio-system/sa/istio-ingressgateway-service-account`).

El tráfico en texto plano viene de componentes que no tienen sidecar. Se acepta justamente porque el modo es permisivo. Los contadores son desde el último reinicio del proxy, por eso se acumulan lecturas de salud y de métricas.

## 4. Limitaciones

- **No está en modo estricto.** Pasar a STRICT rompería al frontend y a Prometheus, que entran sin sidecar. Habría que meterlos a la malla o hacer excepciones.
- **Las métricas de Prometheus no sirven para probar el cifrado.** Prometheus solo recoge las métricas del gateway, que reporta desde el lado de quien envía, y ahí el campo `connection_security_policy` sale como `unknown`. Por eso la prueba se hizo leyendo el proxy que recibe.
- Las políticas de red (carpeta `network-policies`) y el mTLS son cosas distintas: las primeras controlan **quién puede conectarse**, el segundo **cifra y verifica** la conexión.

## 5. Cómo repetirlo

```bash
istioctl proxy-status
kubectl get peerauthentication -A
kubectl get pods -n minimarket-backend
```
