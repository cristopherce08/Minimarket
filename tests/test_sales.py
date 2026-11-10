import pytest
from decimal import Decimal
from concurrent.futures import ThreadPoolExecutor


def test_create_multi_item_sale(client):
    """Prueba 4: Registrar una venta con varios productos."""
    # Crear 2 productos
    p1 = client.post("/api/v1/productos", json={"name": "Inka Kola 1.5L", "price": 6.50, "stock": 20}).json()
    p2 = client.post("/api/v1/productos", json={"name": "Papas Lays Clásicas", "price": 3.00, "stock": 15}).json()

    # Venta de 2 Inka Kolas y 3 Papas Lays
    sale_payload = {
        "items": [
            {"product_id": p1["id"], "quantity": 2},
            {"product_id": p2["id"], "quantity": 3},
        ]
    }
    # Total esperado: (2 * 6.50) + (3 * 3.00) = 13.00 + 9.00 = 22.00
    res = client.post("/api/v1/ventas", json=sale_payload)
    assert res.status_code == 201
    sale_data = res.json()

    assert sale_data["id"] > 0
    assert float(sale_data["total"]) == 22.00
    assert len(sale_data["items"]) == 2

    # Verificar que el precio histórico unitario fue congelado
    items = {it["product_id"]: it for it in sale_data["items"]}
    assert float(items[p1["id"]]["unit_price"]) == 6.50
    assert float(items[p1["id"]]["subtotal"]) == 13.00
    assert float(items[p2["id"]]["unit_price"]) == 3.00
    assert float(items[p2["id"]]["subtotal"]) == 9.00


def test_inventory_deduction(client):
    """Prueba 5: Descontar correctamente el inventario tras una venta confirmada."""
    p = client.post("/api/v1/productos", json={"name": "Detergente Ariel 1kg", "price": 11.50, "stock": 30}).json()

    # Realizar venta de 7 unidades
    sale_res = client.post(
        "/api/v1/ventas",
        json={"items": [{"product_id": p["id"], "quantity": 7}]},
    )
    assert sale_res.status_code == 201

    # Verificar stock actualizado en PostgreSQL/DB
    prod_check = client.get(f"/api/v1/productos/{p['id']}").json()
    assert prod_check["stock"] == 23  # 30 - 7 = 23


def test_reject_sale_insufficient_stock(client):
    """Prueba 6: Rechazar ventas cuando un producto no dispone de stock suficiente."""
    p = client.post("/api/v1/productos", json={"name": "Aceite Vegetal 900ml", "price": 8.00, "stock": 3}).json()

    # Intentar comprar 5 unidades teniendo solo 3
    sale_res = client.post(
        "/api/v1/ventas",
        json={"items": [{"product_id": p["id"], "quantity": 5}]},
    )
    assert sale_res.status_code == 400
    err_data = sale_res.json()
    assert "Stock insuficiente" in err_data["detail"]
    assert "Stock disponible: 3, solicitado: 5" in err_data["detail"]

    # Comprobar que el stock original quedó intacto
    prod_check = client.get(f"/api/v1/productos/{p['id']}").json()
    assert prod_check["stock"] == 3


def test_rollback_on_failed_item(client):
    """
    Prueba 7: Verificar atomicidad y ROLLBACK cuando falla un elemento en una venta multi-producto.
    El inventario de TODOS los productos debe permanecer exactamente intacto.
    """
    # Producto 1 con stock abundante
    p1 = client.post("/api/v1/productos", json={"name": "Fideos Tallarín 500g", "price": 3.20, "stock": 50}).json()
    # Producto 2 con stock insuficiente
    p2 = client.post("/api/v1/productos", json={"name": "Atún en Trozos Campomar", "price": 6.00, "stock": 2}).json()

    # Venta combinada: solicita 10 unidades de Fideos (OK) y 5 unidades de Atún (FALLA)
    payload = {
        "items": [
            {"product_id": p1["id"], "quantity": 10},
            {"product_id": p2["id"], "quantity": 5},
        ]
    }
    res = client.post("/api/v1/ventas", json=payload)
    assert res.status_code == 400

    # Comprobar que NINGUNO de los productos fue descontado
    check_p1 = client.get(f"/api/v1/productos/{p1['id']}").json()
    check_p2 = client.get(f"/api/v1/productos/{p2['id']}").json()

    assert check_p1["stock"] == 50  # No se descontaron las 10 unidades
    assert check_p2["stock"] == 2   # Sigue en 2 unidades


def test_prevent_overselling_concurrency(client):
    """
    Prueba 8: Impedir sobreventa ante solicitudes concurrentes.
    Si hay 4 unidades disponibles y se envían 10 solicitudes concurrentes de 1 unidad cada una:
    Exactamente 4 deben completarse y 6 deben ser rechazadas. El stock final debe ser exactamente 0.
    """
    p = client.post("/api/v1/productos", json={"name": "Galletas Coronita Pack", "price": 1.50, "stock": 4}).json()
    prod_id = p["id"]

    results = []

    def make_purchase():
        response = client.post(
            "/api/v1/ventas",
            json={"items": [{"product_id": prod_id, "quantity": 1}]},
        )
        return response.status_code

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(make_purchase) for _ in range(10)]
        for f in futures:
            results.append(f.result())

    success_count = results.count(201)
    rejected_count = results.count(400)

    assert success_count == 4, f"Se esperaban 4 ventas exitosas, pero ocurrieron {success_count}"
    assert rejected_count == 6, f"Se esperaban 6 ventas rechazadas por falta de stock, pero ocurrieron {rejected_count}"

    # Verificar stock final en base de datos
    final_prod = client.get(f"/api/v1/productos/{prod_id}").json()
    assert final_prod["stock"] == 0, f"El stock final debería ser 0, pero es {final_prod['stock']}"
