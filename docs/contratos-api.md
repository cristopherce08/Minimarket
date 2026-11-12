# Contratos de API y Especificación de Datos — MiniMarket Cloud

Este documento define la especificación técnica de esquemas de base de datos, endpoints REST, códigos de estado HTTP y contratos JSON entre el **Frontend**, el microservicio **`ventas-api`** (puerto `8000`) y el microservicio **`reportes-api`** (puerto `8001`).

---

## 1. Esquema Relacional de Base de Datos (PostgreSQL 16)

```mermaid
erDiagram
    products ||--o{ sale_items : "se incluye en"
    sales ||--|{ sale_items : "contiene"

    products {
        int id PK
        varchar(150) name
        numeric(10,2) price
        int stock
        timestamp created_at
    }

    sales {
        int id PK
        numeric(10,2) total
        timestamp created_at
    }

    sale_items {
        int id PK
        int sale_id FK
        int product_id FK
        int quantity
        numeric(10,2) unit_price
        numeric(10,2) subtotal
    }
```

### Reglas de Integridad y Restricciones
- `products.price`: `CHECK (price > 0)`
- `products.stock`: `CHECK (stock >= 0)`
- `sale_items.quantity`: `CHECK (quantity > 0)`
- `sale_items.unit_price`: `CHECK (unit_price > 0)` (Precio histórico congelado en el momento exacto de la venta)
- `sales.total`: `CHECK (total >= 0)`
- `sale_items.sale_id`: `FOREIGN KEY REFERENCES sales(id) ON DELETE CASCADE`
- `sale_items.product_id`: `FOREIGN KEY REFERENCES products(id)`

---

## 2. Microservicio `ventas-api` (Puerto 8000)

Prefijo base: `/api/v1`

### 2.1. Endpoints de Diagnóstico y Métricas

- **`GET /health`**
  - **Propósito:** Liveness probe de Kubernetes.
  - **Respuesta (`200 OK`):**
    ```json
    {
      "status": "healthy",
      "service": "ventas-api",
      "timestamp": "2026-11-10T05:30:00Z"
    }
    ```

- **`GET /ready`**
  - **Propósito:** Readiness probe de Kubernetes (valida conectividad con PostgreSQL).
  - **Respuesta (`200 OK`):**
    ```json
    {
      "status": "ready",
      "database": "connected",
      "latency_ms": 1.25
    }
    ```
  - **Respuesta (`503 Service Unavailable`):**
    ```json
    {
      "status": "unhealthy",
      "database": "disconnected",
      "error": "Error de conexión a PostgreSQL"
    }
    ```

- **`GET /metrics`**
  - **Propósito:** Scrapeo Prometheus (`prometheus-client`).
  - **Formato:** Texto plano `text/plain` estándar OpenMetrics.

---

### 2.2. Endpoints del Módulo de Productos

#### `GET /api/v1/productos`
- **Query Params:**
  - `buscar` (string opcional)
  - `solo_bajo_stock` (bool opcional, default: `false`)
- **Respuesta (`200 OK`):**
```json
[
  {
    "id": 1,
    "name": "Arroz Costeño 1kg",
    "price": 4.50,
    "stock": 50,
    "is_low_stock": false,
    "created_at": "2026-11-10T00:00:00Z"
  },
  {
    "id": 2,
    "name": "Aceite Primor 1L",
    "price": 9.20,
    "stock": 3,
    "is_low_stock": true,
    "created_at": "2026-11-10T00:00:00Z"
  }
]
```

#### `POST /api/v1/productos`
- **Payload (`application/json`):**
```json
{
  "name": "Leche Gloria Azul 400g",
  "price": 4.20,
  "stock": 100
}
```
- **Validaciones:**
  - `name`: No vacío, longitud entre 2 y 150 caracteres.
  - `price`: Número decimal mayor que cero.
  - `stock`: Entero mayor o igual a cero.
- **Respuesta (`201 Created`):**
```json
{
  "id": 3,
  "name": "Leche Gloria Azul 400g",
  "price": 4.20,
  "stock": 100,
  "is_low_stock": false,
  "created_at": "2026-11-10T05:32:00Z"
}
```

#### `GET /api/v1/productos/{id}`
- **Respuesta (`200 OK`):** Objeto producto individual.
- **Respuesta (`404 Not Found`):**
```json
{
  "detail": "Producto con ID 99 no encontrado."
}
```

#### `PUT /api/v1/productos/{id}`
- **Payload (`application/json`):**
```json
{
  "name": "Leche Gloria Azul 400g (Lata)",
  "price": 4.50,
  "stock": 95
}
```
- **Respuesta (`200 OK`):** Objeto producto actualizado.

#### `GET /api/v1/productos/alertas/bajo-stock`
- **Query Params:**
  - `threshold` (int opcional, default: `5`)
- **Respuesta (`200 OK`):** Lista de productos con stock menor o igual al umbral.

---

### 2.3. Endpoints del Módulo de Ventas

#### `POST /api/v1/ventas`
- **Descripción:** Registro atómico de venta multi-producto. Bloquea filas en PostgreSQL con `with_for_update()`, valida stock disponible de todos los ítems, descuenta el inventario y genera la venta con su detalle. Si falla cualquier producto por stock insuficiente, se cancela toda la venta mediante `ROLLBACK`.
- **Payload (`application/json`):**
```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    },
    {
      "product_id": 2,
      "quantity": 1
    }
  ]
}
```
- **Respuesta Exitosa (`201 Created`):**
```json
{
  "id": 1,
  "total": 18.20,
  "created_at": "2026-11-10T05:35:00Z",
  "items": [
    {
      "id": 1,
      "product_id": 1,
      "product_name": "Arroz Costeño 1kg",
      "quantity": 2,
      "unit_price": 4.50,
      "subtotal": 9.00
    },
    {
      "id": 2,
      "product_id": 2,
      "product_name": "Aceite Primor 1L",
      "quantity": 1,
      "unit_price": 9.20,
      "subtotal": 9.20
    }
  ]
}
```
- **Error por Stock Insuficiente (`400 Bad Request`):**
```json
{
  "error": "STOCK_INSUFICIENTE",
  "detail": "Stock insuficiente para 'Aceite Primor 1L'. Disponible: 3, Solicitado: 5."
}
```

#### `GET /api/v1/ventas`
- **Query Params:** `limit` (default: 50), `offset` (default: 0)
- **Respuesta (`200 OK`):** Lista de ventas con resumen de total y fecha.

#### `GET /api/v1/ventas/{id}`
- **Respuesta (`200 OK`):** Detalle completo de la venta y sus ítems.

---

### 2.4. Endpoints del Módulo de Inventario

#### `GET /api/v1/inventario/resumen`
- **Descripción:** Consulta agregada directa de PostgreSQL sobre el estado del inventario.
- **Respuesta (`200 OK`):**
```json
{
  "total_productos": 15,
  "total_unidades_en_stock": 420,
  "productos_agotados": 2,
  "productos_stock_bajo": 4,
  "items_agotados": [
    {"id": 5, "name": "Galletas Soda San Jorge", "stock": 0}
  ],
  "items_stock_bajo": [
    {"id": 2, "name": "Aceite Primor 1L", "stock": 3}
  ]
}
```

---

## 3. Microservicio `reportes-api` (Puerto 8001)

Prefijo base: `/api/v1/reportes`

### 3.1. Endpoints de Diagnóstico
- `GET /health`: Estado liveness.
- `GET /ready`: Estado readiness (conexión a PostgreSQL).
- `GET /metrics`: Métricas Prometheus.

3.2 GET /api/v1/reportes/spark

Resultados del último procesamiento distribuido con Apache Spark (tablas agg_*).

Query params: limite (1-50, default 10) = productos del ranking; dias (1-365, default 30) = últimos N días.

Respuesta 200 (job ejecutado): { "disponible": true, "procesado_en": "2026-11-11T04:00:59", "resumen": {"total_ventas": 200000, "ingresos_totales": "2649828.80", "total_productos": 12}, "productos_top": [{"ranking": 1, "product_id": 5, "product_name": "Coca Cola 500ml", "unidades_vendidas": 50641, "total_recaudado": "177243.50"}], "ventas_por_dia": [{"fecha": "2026-11-10", "numero_ventas": 6514, "total_ingresos": "86241.50"}] }

Respuesta 200 (job aún no ejecutado): {"disponible": false, "resumen": null, "productos_top": [], "ventas_por_dia": []} Errores: 422 parámetros fuera de rango; 500 error al leer tablas (¿migración 002 aplicada?).

### 3.3. Endpoints de Reportes Estadísticos

#### `GET /api/v1/reportes/ventas-hoy`
- **Respuesta (`200 OK`):**
```json
{
  "fecha": "2026-11-10",
  "total_ventas": 12,
  "total_ingresos": 348.50,
  "ticket_promedio": 29.04
}
```

#### `GET /api/v1/reportes/productos-top`
- **Query Params:** `limite` (default: 5)
- **Respuesta (`200 OK`):**
```json
[
  {
    "ranking": 1,
    "product_id": 1,
    "product_name": "Arroz Costeño 1kg",
    "unidades_vendidas": 45,
    "total_recaudado": 202.50
  },
  {
    "ranking": 2,
    "product_id": 3,
    "product_name": "Leche Gloria Azul 400g",
    "unidades_vendidas": 38,
    "total_recaudado": 159.60
  }
]
```

#### `GET /api/v1/reportes/ventas-agrupadas-dia`
- **Query Params:** `dias` (default: 7)
- **Respuesta (`200 OK`):**
```json
[
  {
    "fecha": "2026-11-09",
    "numero_ventas": 8,
    "total_ingresos": 215.00
  },
  {
    "fecha": "2026-11-10",
    "numero_ventas": 12,
    "total_ingresos": 348.50
  }
]
```

#### `GET /api/v1/reportes/resumen-general`
- **Respuesta (`200 OK`):**
```json
{
  "total_ventas_historicas": 120,
  "ingresos_totales_historicos": 4520.80,
  "total_productos_activos": 15
}
```
