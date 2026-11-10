import pytest


def test_ventas_api_health_ready_metrics(client):
    """Prueba 10A: Verificar salud, readiness y métricas Prometheus en ventas-api."""
    # 1. /health
    res_health = client.get("/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "ventas-api"

    # 2. /ready
    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    ready_data = res_ready.json()
    assert ready_data["status"] == "ready"
    assert ready_data["database"] == "connected"
    assert "latency_ms" in ready_data

    # 3. /metrics (formato Prometheus)
    res_metrics = client.get("/metrics")
    assert res_metrics.status_code == 200
    assert "text/plain" in res_metrics.headers.get("content-type", "")
    metrics_text = res_metrics.text
    assert "minimarket_requests_total" in metrics_text or "process_cpu_seconds_total" in metrics_text


def test_reportes_api_health_ready_metrics(reportes_client):
    """Prueba 10B: Verificar salud, readiness y métricas Prometheus en reportes-api."""
    # 1. /health
    res_health = reportes_client.get("/health")
    assert res_health.status_code == 200
    health_data = res_health.json()
    assert health_data["status"] == "healthy"
    assert health_data["service"] == "reportes-api"

    # 2. /ready
    res_ready = reportes_client.get("/ready")
    assert res_ready.status_code == 200
    ready_data = res_ready.json()
    assert ready_data["status"] == "ready"
    assert ready_data["database"] == "connected"

    # 3. /metrics
    res_metrics = reportes_client.get("/metrics")
    assert res_metrics.status_code == 200
    assert "text/plain" in res_metrics.headers.get("content-type", "")
