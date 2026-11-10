import pytest
from decimal import Decimal


def test_reports_queries(client, reportes_client):
    """
    Prueba 9: Consultar correctamente los reportes analíticos:
    - Ventas de hoy.
    - Ranking de productos más vendidos.
    - Ventas agrupadas por día.
    - Resumen general histórico.
    """
    # 1. Crear productos a través de ventas-api
    p1 = client.post("/api/v1/productos", json={"name": "Arroz Costeño 5kg", "price": 20.00, "stock": 50}).json()
    p2 = client.post("/api/v1/productos", json={"name": "Aceite Capri 1L", "price": 10.00, "stock": 50}).json()
    p3 = client.post("/api/v1/productos", json={"name": "Azúcar Rubia 1kg", "price": 4.00, "stock": 50}).json()

    # 2. Registrar ventas
    # Venta 1: 3 de arroz (60.00) + 1 de aceite (10.00) = 70.00
    client.post("/api/v1/ventas", json={"items": [{"product_id": p1["id"], "quantity": 3}, {"product_id": p2["id"], "quantity": 1}]})

    # Venta 2: 5 de azúcar (20.00) + 2 de arroz (40.00) = 60.00
    client.post("/api/v1/ventas", json={"items": [{"product_id": p3["id"], "quantity": 5}, {"product_id": p1["id"], "quantity": 2}]})

    # 3. Consultar /api/v1/reportes/ventas-hoy
    res_hoy = reportes_client.get("/api/v1/reportes/ventas-hoy")
    assert res_hoy.status_code == 200
    data_hoy = res_hoy.json()
    assert data_hoy["total_ventas"] == 2
    assert float(data_hoy["total_ingresos"]) == 130.00
    assert float(data_hoy["ticket_promedio"]) == 65.00

    # 4. Consultar /api/v1/reportes/productos-top
    res_top = reportes_client.get("/api/v1/reportes/productos-top?limite=3")
    assert res_top.status_code == 200
    top_items = res_top.json()
    assert len(top_items) == 3

    # Ranking 1: Arroz (5 unidades vendidas, 100 soles recaudados)
    # Ranking 2: Azúcar (5 unidades vendidas, 20 soles recaudados)
    # Ranking 3: Aceite (1 unidad vendida, 10 soles recaudados)
    assert top_items[0]["product_id"] == p1["id"]
    assert top_items[0]["unidades_vendidas"] == 5
    assert float(top_items[0]["total_recaudado"]) == 100.00

    # 5. Consultar /api/v1/reportes/ventas-agrupadas-dia
    res_dias = reportes_client.get("/api/v1/reportes/ventas-agrupadas-dia?dias=7")
    assert res_dias.status_code == 200
    dias_data = res_dias.json()
    assert len(dias_data) >= 1
    today_entry = dias_data[-1]
    assert today_entry["numero_ventas"] == 2
    assert float(today_entry["total_ingresos"]) == 130.00

    # 6. Consultar /api/v1/reportes/resumen-general
    res_gen = reportes_client.get("/api/v1/reportes/resumen-general")
    assert res_gen.status_code == 200
    gen_data = res_gen.json()
    assert gen_data["total_ventas_historicas"] == 2
    assert float(gen_data["ingresos_totales_historicos"]) == 130.00
    assert gen_data["total_productos_activos"] == 3
