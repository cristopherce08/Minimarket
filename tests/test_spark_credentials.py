"""
Pruebas unitarias para el parseo seguro y robusto de credenciales de base de datos en Spark.
Valida compatibilidad con esquemas postgresql:// y postgresql+psycopg://,
soporte para caracteres especiales percent-encoded y ausencia de fugas de secretos.
"""
import pytest
from src.spark.jobs.ventas_spark import parse_database_url, obtener_credenciales_bd


def test_parse_database_url_standard():
    url = "postgresql://minimarket_user:mi_password_seguro@postgres-svc:5432/minimarket_db"
    jdbc, user, password = parse_database_url(url)
    assert jdbc == "jdbc:postgresql://postgres-svc:5432/minimarket_db"
    assert user == "minimarket_user"
    assert password == "mi_password_seguro"


def test_parse_database_url_psycopg_scheme():
    url = "postgresql+psycopg://test_user:pass456@db.internal:5433/test_db"
    jdbc, user, password = parse_database_url(url)
    assert jdbc == "jdbc:postgresql://db.internal:5433/test_db"
    assert user == "test_user"
    assert password == "pass456"


def test_parse_database_url_default_port():
    url = "postgresql://user:pass@db-host/minimarket_db"
    jdbc, user, password = parse_database_url(url)
    assert jdbc == "jdbc:postgresql://db-host:5432/minimarket_db"
    assert user == "user"
    assert password == "pass"


def test_parse_database_url_percent_encoded_special_characters():
    # Contraseña con '@', ':', '/', '#' codificados en URL:
    # "p@ss:w/ord#1" -> "p%40ss%3Aw%2Ford%231"
    raw_password = "p@ss:w/ord#1"
    url = f"postgresql://app_user:p%40ss%3Aw%2Ford%231@postgres.minimarket-data.svc.cluster.local:5432/minimarket_db"
    jdbc, user, password = parse_database_url(url)
    assert jdbc == "jdbc:postgresql://postgres.minimarket-data.svc.cluster.local:5432/minimarket_db"
    assert user == "app_user"
    assert password == raw_password


def test_parse_database_url_invalid_scheme():
    with pytest.raises(ValueError) as excinfo:
        parse_database_url("mysql://user:pass@host:3306/db")
    assert "Esquema de base de datos no compatible" in str(excinfo.value)
    # Verificar que las credenciales no se filtren
    assert "user" not in str(excinfo.value)
    assert "pass" not in str(excinfo.value)


def test_parse_database_url_empty_or_none():
    with pytest.raises(ValueError):
        parse_database_url("")
    with pytest.raises(ValueError):
        parse_database_url(None)  # type: ignore


def test_obtener_credenciales_bd_via_database_url(monkeypatch):
    monkeypatch.delenv("JDBC_URL", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://k8s_user:k8s_secret@postgres.minimarket-data:5432/minimarket_db",
    )
    jdbc, user, password = obtener_credenciales_bd()
    assert jdbc == "jdbc:postgresql://postgres.minimarket-data:5432/minimarket_db"
    assert user == "k8s_user"
    assert password == "k8s_secret"


def test_obtener_credenciales_bd_via_explicit_jdbc(monkeypatch):
    monkeypatch.setenv("JDBC_URL", "jdbc:postgresql://standalone:5432/db")
    monkeypatch.setenv("DB_USER", "direct_user")
    monkeypatch.setenv("DB_PASSWORD", "direct_pass")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    jdbc, user, password = obtener_credenciales_bd()
    assert jdbc == "jdbc:postgresql://standalone:5432/db"
    assert user == "direct_user"
    assert password == "direct_pass"


def test_obtener_credenciales_bd_missing_raises_security_error(monkeypatch):
    monkeypatch.delenv("JDBC_URL", raising=False)
    monkeypatch.delenv("DB_USER", raising=False)
    monkeypatch.delenv("DB_PASSWORD", raising=False)
    monkeypatch.delenv("DATABASE_URL", raising=False)
    with pytest.raises(RuntimeError) as excinfo:
        obtener_credenciales_bd()
    assert "SEGURIDAD: Faltan credenciales" in str(excinfo.value)
