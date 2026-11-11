"""
Pruebas de Seguridad y Aislamiento Estricto de Base de Datos
Garantiza que la suite de pruebas rechace cualquier conexión a la base de desarrollo minimarket_db (puerto 5433),
que todos los motores SQLAlchemy en memoria apunten exclusivamente a minimarket_test_db (puerto 5434),
y que el sistema opere en modo Fail-Closed sin fallback silencioso a SQLite para integración.
"""
import sys
import pytest
from sqlalchemy import text
from conftest import (
    validate_test_database_target,
    assert_connected_database_is_safe,
    init_test_engine,
    FORBIDDEN_DATABASES,
    AUTHORIZED_TEST_DATABASES,
    FORBIDDEN_PORTS,
    engine_test,
    DB_DIALECT,
)
import app.database as ventas_db
import app.main as ventas_main


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
        assert ("PROHIBICIÓN TOTAL" in str(exc_info.value) or
                "no está autorizada" in str(exc_info.value) or
                "puerto 5433" in str(exc_info.value))


def test_reject_development_port_5433():
    """
    Seguridad 2: Demostrar que el validador RECHAZA cualquier conexión al puerto 5433
    (puerto exclusivo de desarrollo), incluso si intentara usar otro nombre de base.
    """
    dev_port_urls = [
        "postgresql://test_user:pass@localhost:5433/minimarket_test_db",
        "postgresql+psycopg://test_user:pass@127.0.0.1:5433/minimarket_test_db",
    ]

    for url in dev_port_urls:
        with pytest.raises(RuntimeError) as exc_info:
            validate_test_database_target(url)
        assert "El puerto 5433 corresponde al PostgreSQL de desarrollo" in str(exc_info.value)


def test_reject_unauthorized_database_names():
    """
    Seguridad 3: Demostrar que se rechazan bases de datos que no sean exactamente
    la instancia autorizada 'minimarket_test_db'.
    """
    unauthorized_urls = [
        "postgresql://user:pass@localhost:5434/clientes_db",
        "postgresql://user:pass@localhost:5434/ventas_online",
        "postgresql://user:pass@localhost:5434/staging_db",
        "postgresql://user:pass@localhost:5434/otra_base_test",
        "postgresql://user:pass@localhost:5434/empresa_test_db",
    ]

    for url in unauthorized_urls:
        with pytest.raises(RuntimeError) as exc_info:
            validate_test_database_target(url)
        assert "no está autorizada para pruebas" in str(exc_info.value)


def test_allow_authorized_test_database_urls():
    """
    Seguridad 4: Demostrar que el validador acepta únicamente la base autorizada de pruebas.
    """
    valid_urls = [
        "postgresql+psycopg://test_user:pass@localhost:5434/minimarket_test_db",
        "postgresql://test_user:pass@127.0.0.1:5434/minimarket_test_db",
        "sqlite:///:memory:",
        "sqlite:////tmp/minimarket_test_isolated.db",
    ]

    for url in valid_urls:
        validate_test_database_target(url)


def test_all_in_memory_engines_point_to_test_database():
    """
    Seguridad 5: Demostrar que TODOS los motores SQLAlchemy en memoria:
    - engine_test (conftest)
    - app.database.engine (ventas-api)
    - app.main.engine (ventas-api lifespan)
    - reportes_pkg.database.engine (reportes-api)
    apuntan estrictamente a la base de pruebas y NINGUNO al puerto 5433 ni minimarket_db.
    """
    reportes_db = sys.modules.get("reportes_pkg.database")
    assert reportes_db is not None, "El módulo reportes_pkg.database debe estar cargado"

    engines_to_check = {
        "conftest.engine_test": engine_test,
        "ventas_db.engine": ventas_db.engine,
        "ventas_main.engine": ventas_main.engine,
        "reportes_db.engine": reportes_db.engine,
    }

    for name, eng in engines_to_check.items():
        assert eng is not None, f"{name} no debe ser None"
        eng_url = eng.url
        # Comprobar que no apunta al puerto 5433 de desarrollo
        assert eng_url.port != 5433, f"PELIGRO: {name} apunta al puerto 5433 de desarrollo!"
        # Comprobar que la base no es minimarket_db
        db_name = (eng_url.database or "").strip().lower()
        assert db_name != "minimarket_db", f"PELIGRO: {name} apunta a la base minimarket_db!"
        # Comprobar que apunta a la base de pruebas autorizada
        if DB_DIALECT == "postgresql":
            assert db_name == "minimarket_test_db", f"{name} debe apuntar a minimarket_test_db, no a {db_name}"
            assert eng_url.port == 5434, f"{name} debe usar el puerto 5434 de pruebas"
        else:
            assert "test" in db_name or "tmp" in db_name or db_name == ":memory:"


def test_fail_closed_when_postgres_unreachable():
    """
    Seguridad 6: Comportamiento Fail-Closed.
    Si la instancia PostgreSQL de pruebas no responde (por ejemplo, puerto cerrado 5439),
    init_test_engine() DEBE fallar inmediatamente con RuntimeError explicativo,
    y NO debe realizar fallback silencioso a SQLite.
    """
    unreachable_url = "postgresql+psycopg://test_user:test_password@localhost:5439/minimarket_test_db"
    with pytest.raises(RuntimeError) as exc_info:
        init_test_engine(custom_url=unreachable_url, force_sqlite=False)

    err_text = str(exc_info.value)
    assert "FALLO DE CONEXIÓN AL POSTGRESQL DE PRUEBAS (COMPORTAMIENTO FAIL-CLOSED)" in err_text
    assert "docker compose -f docker-compose.test.yml up -d" in err_text
    assert "El fallback silencioso a SQLite está deshabilitado" in err_text


def test_explicit_sqlite_unit_test_mode():
    """
    Seguridad 7: Modo Unitario Explícito SQLite.
    Demostrar que SQLite solo se inicializa cuando se solicita explícitamente,
    usando un archivo temporal seguro en /tmp/ con modo WAL.
    """
    sqlite_eng, dialect, url = init_test_engine(force_sqlite=True)
    try:
        assert dialect == "sqlite"
        assert "minimarket_test_isolated.db" in url
        with sqlite_eng.connect() as conn:
            mode = conn.execute(text("PRAGMA journal_mode;")).scalar()
            assert mode.lower() == "wal"
    finally:
        sqlite_eng.dispose()


def test_live_engine_is_not_connected_to_development():
    """
    Seguridad 8: Demostrar en vivo que la conexión activa contra el motor actual
    está conectada a la base autorizada minimarket_test_db.
    """
    with engine_test.connect() as conn:
        assert_connected_database_is_safe(conn)

        if DB_DIALECT == "postgresql":
            live_db = conn.execute(text("SELECT current_database();")).scalar()
            assert live_db == "minimarket_test_db", f"La base de datos activa debe ser minimarket_test_db, no {live_db}"
            assert live_db not in FORBIDDEN_DATABASES, f"La base activa {live_db} está en la lista prohibida!"
        else:
            assert DB_DIALECT == "sqlite"
            db_path = str(engine_test.url.database)
            assert "test" in db_path.lower() or db_path == ":memory:"
