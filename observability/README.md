# Observabilidad y resiliencia

MiniMarket expone las APIs del entorno base en `minimarket.local` y las ventas de laboratorio en `pruebas.minimarket.local`. Las pruebas de caos usan un namespace y una instancia PostgreSQL independientes.

## Instalación en un laboratorio autorizado

Verifica el contexto, la versión de Kubernetes y las CRDs antes de aplicar. Las versiones probadas están en el [informe UTP](../docs/validacion-final-utp.md).

1. Instala Istio con un Ingress Gateway `ClusterIP` en `istio-system`. Habilita la inyección en el namespace de las APIs y renueva solo sus Deployments. Aplica `gateway.yaml`, `virtualservice.yaml`, `destinationrule.yaml` y `peerauthentication.yaml` desde [`istio/`](istio/). Usa las [políticas canónicas](../docs/infraestructura/guia-redes-networkpolicies.md).
2. Instala [Prometheus y Grafana](prometheus-grafana/README.md) y carga el ServiceMonitor, el PodMonitor y el dashboard. La autenticación mTLS de las APIs queda en `PERMISSIVE`, lo que conserva el acceso del frontend y Prometheus sin sidecars.
3. Instala Chaos Mesh con el runtime y socket del nodo. Para Minikube con containerd usa `chaosDaemon.runtime=containerd`, `chaosDaemon.socketPath=/run/containerd/containerd.sock` y `controllerManager.enableFilterNamespace=true`. Solo el namespace de pruebas lleva la anotación de inyección.

Si existe el Gateway histórico `minimarket-backend/minimarket-gateway`, inspecciona sus propietarios y sus VirtualServices antes de retirarlo por nombre exacto. El Gateway actual está en `istio-system` y admite los hosts declarados de ambos namespaces. La ruta de reportes admite reintentos limitados. Las rutas de ventas desactivan reintentos del gateway.

## Ensayo de carga y caos

1. Aplica [`pruebas/namespace.yaml`](pruebas/namespace.yaml) y las [políticas de pruebas](../infra/k8s/network-policies/pruebas/aislamiento.yaml). Crea `backend-db-pruebas-secret` en `minimarket-pruebas` usando el gestor de secretos. Las claves requeridas son `POSTGRES_PASSWORD` y `DATABASE_URL`. Ambas usan la misma contraseña. La URL apunta a `postgres-pruebas.minimarket-pruebas.svc.cluster.local:5432/minimarket_pruebas` con usuario `minimarket_pruebas`.
2. Aplica [PostgreSQL y el validador](pruebas/postgres-pruebas.yaml). Espera que PostgreSQL esté Ready. Aplica [el Job de migraciones](pruebas/alembic-job-pruebas.yaml) y espera `Complete` antes de aplicar [la API, el Service, el HPA y la ruta](pruebas/ventas-api-pruebas.yaml). El validador rechaza `minimarket_db` y verifica el nombre de la base conectada antes de arrancar.
3. Abre un port-forward del Gateway. Verifica que `GET /api/v1/productos` retorne 200 con `Host: pruebas.minimarket.local`, que un host desconocido retorne 404 y que los EndpointSlices apunten a pods de `ventas-api-pruebas` Ready. Comprueba el destino del Secret sin mostrar sus valores, confirma que los Services y pods PostgreSQL sean distintos y registra los conteos iniciales de `products`, `sales` y `sale_items` en ambas bases. En la base original usa una sesión de solo lectura.
4. Empieza con carga moderada de lectura. Para cada experimento, confirma que `spec.selector` exija el namespace `minimarket-pruebas`, `app=ventas-api-pruebas` y `entorno=pruebas`. Crea un recurso cada vez, registra `AllInjected` y los pods afectados, mide la recuperación y retira ese objeto por nombre exacto.
5. Para medir ventas, crea inventario de prueba y envía solicitudes acotadas con una `Idempotency-Key` única por venta. Ante un timeout, consulta las claves confirmadas en `sale_requests` o repite la misma clave con el mismo cuerpo. Contrasta respuestas, ventas, detalles y descuento de stock. Compara los conteos finales de la base original con los conteos iniciales.

```bash
kubectl -n istio-system port-forward svc/istio-ingressgateway 18080:80
hey -n 120 -c 3 -q 5 -t 4 -host pruebas.minimarket.local http://127.0.0.1:18080/api/v1/productos
kubectl -n minimarket-pruebas get hpa ventas-api-pruebas-hpa -w
```

Los cuatro escenarios están en [`chaos-mesh/`](chaos-mesh/). Los resultados históricos registraron errores 503 y 504. Ocho ventas se confirmaron en PostgreSQL aunque el cliente recibió 504. El [contrato de idempotencia](../docs/contratos-api.md) documenta cómo recuperar una respuesta sin repetir el descuento.

## Dimensionamiento

Ejecuta `./infra/tco/dimensionamiento_tco.sh -y` para comprobar los supuestos predeterminados. El modelo calcula potencia, refrigeración y TCO a tres años para un centro de datos hipotético. Los números son supuestos de dimensionamiento del proyecto.
