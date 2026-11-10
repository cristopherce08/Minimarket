import pytest
from decimal import Decimal


def test_create_valid_product(client):
    """Prueba 1: Crear un producto válido en el catálogo."""
    payload = {
        "name": "Arroz Paisana Superior 1kg",
        "price": 4.80,
        "stock": 25,
    }
    response = client.post("/api/v1/productos", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["id"] > 0
    assert data["name"] == "Arroz Paisana Superior 1kg"
    assert float(data["price"]) == 4.80
    assert data["stock"] == 25
    assert data["is_low_stock"] is False
    assert "created_at" in data


def test_reject_invalid_product_price(client):
    """Prueba 2: Rechazar productos con precio o stock inválido, o nombre vacío."""
    # Precio igual a cero
    res1 = client.post("/api/v1/productos", json={"name": "Aceite", "price": 0.00, "stock": 10})
    assert res1.status_code == 422

    # Precio negativo
    res2 = client.post("/api/v1/productos", json={"name": "Aceite", "price": -3.50, "stock": 10})
    assert res2.status_code == 422

    # Stock negativo
    res3 = client.post("/api/v1/productos", json={"name": "Aceite", "price": 8.50, "stock": -2})
    assert res3.status_code == 422

    # Nombre vacío o solo espacios
    res4 = client.post("/api/v1/productos", json={"name": "   ", "price": 5.00, "stock": 10})
    assert res4.status_code == 422


def test_modify_product_stock(client):
    """Prueba 3: Modificar stock y precio de un producto existente."""
    # 1. Crear producto
    create_res = client.post(
        "/api/v1/productos",
        json={"name": "Leche Gloria Evaporada", "price": 4.20, "stock": 15},
    )
    assert create_res.status_code == 201
    prod_id = create_res.json()["id"]

    # 2. Modificar stock y precio
    update_res = client.put(
        f"/api/v1/productos/{prod_id}",
        json={"price": 4.50, "stock": 8},
    )
    assert update_res.status_code == 200
    updated_data = update_res.json()
    assert float(updated_data["price"]) == 4.50
    assert updated_data["stock"] == 8

    # 3. Consultar producto individual para verificar persistencia
    get_res = client.get(f"/api/v1/productos/{prod_id}")
    assert get_res.status_code == 200
    assert float(get_res.json()["price"]) == 4.50
    assert get_res.json()["stock"] == 8


def test_get_low_stock_alerts(client):
    """Prueba complementaria: Identificar productos con inventario bajo o agotado."""
    client.post("/api/v1/productos", json={"name": "Producto Normal", "price": 10.00, "stock": 20})
    client.post("/api/v1/productos", json={"name": "Producto Crítico", "price": 5.00, "stock": 3})
    client.post("/api/v1/productos", json={"name": "Producto Agotado", "price": 2.50, "stock": 0})

    res = client.get("/api/v1/productos/alertas/bajo-stock?threshold=5")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    names = [p["name"] for p in data]
    assert "Producto Crítico" in names
    assert "Producto Agotado" in names
    assert "Producto Normal" not in names
