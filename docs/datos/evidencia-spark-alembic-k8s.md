# Evidencia de Validación Práctica: Spark en Kubernetes y Migraciones Alembic

**Fecha de validación:** 2026-11-11  
**Rama:** `integration/minimarket-pre-release`  
**Entorno de ejecución:** Clúster Minikube local (Arquitectura ARM64 / containerd)  

---

## 1. Entorno Aislado de Validación

Para garantizar la protección absoluta de la base de datos de desarrollo y los recursos operativos de MiniMarket Cloud, se desplegó un entorno temporal y estrictamente segregado:

- **Namespace aislado:** `minimarket-test`
- **Instancia PostgreSQL independiente:** Pod `postgres-test` con almacenamiento efímero `emptyDir` (sin persistencia compartida ni acceso al PVC de desarrollo `postgres-pvc`).
- **Base de datos de pruebas:** `minimarket_test_db` (usuario `minimarket_test_user`).
- **Secret independiente:** `backend-test-secret` (cero reutilización de `backend-db-secret` ni secretos del entorno de producción/desarrollo).
- **Aislamiento de red:** Tráfico acotado al namespace `minimarket-test`.

---

## 2. Validación de Migraciones Alembic en Kubernetes

### Manifiesto y Ejecución
Se ejecutó el Job [`alembic-migration-test`](file:///Users/cristopher/Minimarket/infra/helm/minimarket/templates/alembic-job.yaml) utilizando la imagen `minimarket-ventas-api:latest`.

### Logs de Ejecución (Primera Corrida)
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial_schema, Esquema inicial de MiniMarket Cloud (products, sales, sale_items)
INFO  [alembic.runtime.migration] Running upgrade 001_initial_schema -> 002_agregados_spark, Tablas de resultados agregados generados por Spark
```

### Relaciones Creadas en PostgreSQL (`minimarket_test_db`)
```text
                      List of relations
 Schema |        Name         | Type  |        Owner         
--------+---------------------+-------+----------------------
 public | agg_productos_top   | table | minimarket_test_user
 public | agg_resumen_general | table | minimarket_test_user
 public | agg_ventas_diarias  | table | minimarket_test_user
 public | alembic_version     | table | minimarket_test_user
 public | products            | table | minimarket_test_user
 public | sale_items          | table | minimarket_test_user
 public | sales               | table | minimarket_test_user
(7 rows)
```

### Prueba de Idempotencia (Segunda Corrida)
Se reejecutó el Job con el esquema en `head`:
```text
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
```
- Resultado: **0 errores**, no se realizaron alteraciones redundantes.
- Hook de Helm: compatible con `"helm.sh/hook": post-install,post-upgrade`.

---

## 3. Validación de Apache Spark Distribuido en Kubernetes

### Parámetros de la Prueba
- **Driver:** Pod `ventas-spark-test-2bggl` (modo cliente dentro del clúster).
- **Ejecutores:** 2 pods dedicados gestionados dinámicamente por Spark en Kubernetes.
- **Particiones:** 8 particiones distribuidas (`NUM_PARTICIONES=8`).
- **Volumen de datos:** 1,000 ventas simuladas sobre un catálogo transaccional de 5 productos.

### Estado Operativo de los Pods Durante el Procesamiento
```text
NAME                                              READY   STATUS      RESTARTS   AGE
minimarket-ventas-spark-0430b0a1cd1a03a3-exec-1   1/1     Running     0          8s
minimarket-ventas-spark-0430b0a1cd1a03a3-exec-2   1/1     Running     0          8s
ventas-spark-test-2bggl                           1/1     Running     0          13s
```

### Distribución de Tareas Confirmada en Logs del Driver
```text
======================================================================
MINIMARKET CLOUD - Procesamiento distribuido con Apache Spark
Spark 3.5.3 | ventas simuladas: 1000 | particiones: 8 | dias: 30
======================================================================

Reparto del trabajo por ejecutor:
  - minimarket-ventas-spark-0430b0a1cd1a03a3-exec-1: 875 filas
  - minimarket-ventas-spark-0430b0a1cd1a03a3-exec-2: 125 filas
Ejecutores distintos que procesaron datos: 2
```

### Resultados de Agregación Calculados por Spark
```text
Productos mas vendidos:
+-------+----------+------------------------+-----------------+---------------+------------------------+
|ranking|product_id|product_name            |unidades_vendidas|total_recaudado|procesado_en            |
+-------+----------+------------------------+-----------------+---------------+------------------------+
|1      |1         |Inka Kola 1.5L          |655              |4257.50        |2026-11-12 00:13:29.9647|
|2      |4         |Aceite Primor 900ml     |635              |5397.50        |2026-11-12 00:13:29.9647|
|3      |5         |Fideos Don Vittorio 500g|579              |1852.80        |2026-11-12 00:13:29.9647|
|4      |2         |Arroz Costeño 1kg       |551              |2644.80        |2026-11-12 00:13:29.9647|
|5      |3         |Leche Gloria Azul 400g  |547              |2297.40        |2026-11-12 00:13:29.9647|
+-------+----------+------------------------+-----------------+---------------+------------------------+

Resumen general:
+---+------------+----------------+---------------+--------------------------+
|id |total_ventas|ingresos_totales|total_productos|procesado_en              |
+---+------------+----------------+---------------+--------------------------+
|1  |1000        |16450.00        |5              |2026-11-12 00:13:30.659599|
+---+------------+----------------+---------------+--------------------------+
```

### Escritura JDBC a PostgreSQL
```text
Resultados guardados en PostgreSQL: agg_ventas_diarias, agg_productos_top, agg_resumen_general
```
- Inserción limpia con `truncate=true`, preservando la definición de tipos de datos de Alembic.

### Integridad de Tablas Transaccionales
Consultas ejecutadas directamente sobre PostgreSQL tras finalizar el job de Spark:
```sql
SELECT count(*) AS total_products FROM products;   -- Resultado: 5 (catálogo intacto)
SELECT count(*) AS total_sales FROM sales;         -- Resultado: 0 (cero escrituras indebidas)
SELECT count(*) AS total_items FROM sale_items;    -- Resultado: 0 (cero escrituras indebidas)
```

---

## 4. Verificación del Microservicio de Reportes (`reportes-api`)

Se desplegó el pod de prueba `reportes-api-test` conectado a la base aislada:

### Consulta Previa al Procesamiento Spark
```http
GET /api/v1/reportes/spark
```
```json
{
  "disponible": false,
  "procesado_en": null,
  "resumen": null,
  "productos_top": [],
  "ventas_por_dia": []
}
```
- Código de respuesta: **HTTP 200 OK** (tolerante a la ausencia inicial de datos, sin errores 500).

### Consulta Posterior al Procesamiento Spark
```http
GET /api/v1/reportes/spark
```
```json
{
  "disponible": true,
  "procesado_en": "2026-11-12T00:13:32.996703Z",
  "resumen": {
    "total_ventas": 1000,
    "ingresos_totales": "16450.00",
    "total_productos": 5
  },
  "productos_top": [
    {"ranking": 1, "product_id": 1, "product_name": "Inka Kola 1.5L", "unidades_vendidas": 655, "total_recaudado": "4257.50"},
    {"ranking": 2, "product_id": 4, "product_name": "Aceite Primor 900ml", "unidades_vendidas": 635, "total_recaudado": "5397.50"},
    {"ranking": 3, "product_id": 5, "product_name": "Fideos Don Vittorio 500g", "unidades_vendidas": 579, "total_recaudado": "1852.80"},
    {"ranking": 4, "product_id": 2, "product_name": "Arroz Costeño 1kg", "unidades_vendidas": 551, "total_recaudado": "2644.80"},
    {"ranking": 5, "product_id": 3, "product_name": "Leche Gloria Azul 400g", "unidades_vendidas": 547, "total_recaudado": "2297.40"}
  ],
  "ventas_por_dia": [
    {"fecha": "2026-11-11", "numero_ventas": 38, "total_ingresos": "679.10"},
    {"fecha": "2026-11-10", "numero_ventas": 38, "total_ingresos": "611.40"}
    /* ... 30 días ordenados cronológicamente ... */
  ]
}
```
- Consistencia exacta entre los agregados generados por Spark y la API REST.

---

## 5. Verificación de Integridad de la Base de Desarrollo

Al concluir la validación y eliminar el namespace temporal `minimarket-test`, se verificó el estado de PostgreSQL en `minimarket-data`:

```sql
SELECT count(*) FROM products;   -- 12
SELECT count(*) FROM sales;      -- 5
SELECT count(*) FROM sale_items; -- 7
```
**Garantía:** Cero modificaciones, pérdida de datos ni colisiones con el entorno de desarrollo.
