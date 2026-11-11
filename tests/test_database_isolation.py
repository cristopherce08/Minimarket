"""
Pruebas de Seguridad y Aislamiento de Base de Datos
Garantiza que la suite de pruebas rechace cualquier conexión a la base de desarrollo minimarket_db
y que las operaciones destructivas solo puedan ejecutarse contra minimarket_test_db.
"""
import pytest
from sqlalchemy import create_engine, text
from conftest import (
    validate_test_database_target,
    assert_connected_database_is_safe,
    FORBIDDEN_DATABASES,
    AUTHORIZED_TEST_DATABASES,
    engine_test,
    DB_DIALECT,
)


def test_reject_development_database_url():
    """
    Seguridad 1: Demostrar que el validador RECHAZA categóricamente
    cualquier URL que apunte a 'minimarket_db' (base de desarrollo / producción).
    """
    forbidden_urls = [
        "postgresql://minimarket_user:pass@localhost:5433/minimarket_db",
        "postgresql+psycopg://user:pass@localhost:5432/minimarket_db",
        "postgresql://user:pass@remote-host:5432/minimarket",
        "postgresql://user:pass@localhost:5432/postgres",
        "postgresql://user:pass@localhost:5432/production",
    ]

    for url in forbidden_urls:
        with pytest.raises(RuntimeError) as exc_info:
            validate_test_database_target(url)
        assert "SEGURIDAD CRÍTICA INTERCEPTADA" in str(exc_info.value)
        assert "PROHIBICIÓN TOTAL" in str(exc_info.value) or "no está autorizado" in str(exc_info.value)


def test_reject_unauthorized_database_names():
    """
    Seguridad 2: Demostrar que se rechazan bases de datos que no tengan
    nomenclatura explícita de pruebas (minimarket_test_db o sufijo _test).
    """
    unauthorized_urls = [
        "postgresql://user:pass@localhost:5434/clientes_db",
        "postgresql://user:pass@localhost:5434/ventas_online",
        "postgresql://user:pass@localhost:5434/staging_db",
    ]

    for url in unauthorized_urls:
        with pytest.raises(RuntimeError) as exc_info:
            validate_test_database_target(url)
        assert "no está autorizado para pruebas" in str(exc_info.value)


def test_allow_authorized_test_database_urls():
    """
    Seguridad 3: Demostrar que el validador acepta únicamente URLs legítimas de prueba.
    """
    valid_urls = [
        "postgresql+psycopg://test_user:pass@localhost:5434/minimarket_test_db",
        "postgresql://test_user:pass@localhost:5434/my_service_test",
        "postgresql://test_user:pass@localhost:5434/integration_test_db",
        "sqlite:///:memory:",
        "sqlite:////tmp/minimarket_test_isolated.db",
    ]

    for url in valid_urls:
        # No debe lanzar excepción
        validate_test_database_target(url)


def test_live_engine_is_not_connected_to_development():
    """
    Seguridad 4: Demostrar en vivo que el motor activo en la suite actual (engine_test)
    está conectado a una base de pruebas y NO a minimarket_db.
    """
    with engine_test.connect() as conn:
        # La comprobación de seguridad debe pasar sin lanzar excepciones
        assert_connected_database_is_safe(conn)

        if DB_DIALECT == "postgresql":
            live_db = conn.execute(text("SELECT current_database();")).scalar()
            assert live_db == "minimarket_test_db", f"La base de datos activa debe ser minimarket_test_db, no {live_db}"
            assert live_db not in FORBIDDEN_DATABASES, f"La base activa {live_db} está en la lista prohibida!"
        else:
            assert DB_DIALECT == "sqlite"
            db_path = str(engine_test.url.database)
            assert "test" in db_path.lower() or db_path == ":memory:"
