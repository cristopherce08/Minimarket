# Guía de Migraciones de Base de Datos con Alembic

## 1. Estructura de Versiones

Las migraciones residen en [`src/ventas-api/alembic/versions/`](file:///Users/cristopher/Minimarket/src/ventas-api/alembic/versions/):

1. [`001_initial_schema.py`](file:///Users/cristopher/Minimarket/src/ventas-api/alembic/versions/001_initial_schema.py):
   - Crea las tablas transaccionales: `products`, `sales`, `sale_items`.
   - Índices y restricciones de integridad (`price > 0`, `stock >= 0`).
2. [`002_agregados_spark.py`](file:///Users/cristopher/Minimarket/src/ventas-api/alembic/versions/002_agregados_spark.py):
   - Añade las tablas de analítica: `agg_ventas_diarias`, `agg_productos_top`, `agg_resumen_general`.
   - Downgrade idempotente implementado con `DROP TABLE IF EXISTS ... CASCADE`.

---

## 2. Automatización en Kubernetes mediante Helm Hooks

Para evitar carreras de concurrencia entre múltiples réplicas de la API, las migraciones se ejecutan mediante un **Kubernetes Job dedicado** orquestado como un Helm Hook:

- **Plantilla**: [`infra/helm/minimarket/templates/alembic-job.yaml`](file:///Users/cristopher/Minimarket/infra/helm/minimarket/templates/alembic-job.yaml)
- **Anotaciones de ciclo de vida**:
  ```yaml
  annotations:
    "helm.sh/hook": post-install,post-upgrade
    "helm.sh/hook-weight": "1"
    "helm.sh/hook-delete-policy": before-hook-creation
  ```
- **Ventajas**:
  1. Ejecuta una sola instancia del contenedor, eliminando deadlocks y condiciones de carrera en DDL.
  2. Limpia automáticamente el Job anterior antes de crear uno nuevo (`before-hook-creation`).
  3. Reutiliza la imagen base de `ventas-api` y el Secret `backend-db-secret`.

---

## 3. Comandos de Operación y Verificación

### Inspección de versión instalada
```bash
# En el contenedor o entorno local con DATABASE_URL configurada:
alembic -c src/ventas-api/alembic.ini current

# Consulta directa en PostgreSQL:
psql -U minimarket_user -d minimarket_db -c "SELECT version_num FROM alembic_version;"
```

### Aplicación de migraciones hacia la versión más reciente
```bash
alembic -c src/ventas-api/alembic.ini upgrade head
```

### Reversión controlada (rollback)
```bash
alembic -c src/ventas-api/alembic.ini downgrade -1
```
