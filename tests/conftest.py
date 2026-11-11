import os
import sys
import types
import importlib.util
import logging
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

logger = logging.getLogger("tests")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENTAS_PATH = os.path.join(BASE_DIR, "src", "ventas-api")
REPORTES_APP_DIR = os.path.join(BASE_DIR, "src", "reportes-api", "app")

if VENTAS_PATH not in sys.path:
    sys.path.insert(0, VENTAS_PATH)

from app.models import Base
from app.database import get_db as ventas_get_db
from app.main import app as ventas_app

# ==============================================================================
# SEGURIDAD Y AISLAMIENTO ESTRICTO DE BASES DE DATOS DE PRUEBA
# ==============================================================================
# Nombres de bases de datos explícitamente prohibidas (desarrollo / producción / k8s)
FORBIDDEN_DATABASES = frozenset([
    "minimarket_db",
    "minimarket",
    "postgres",
    "production",
    "prod",
    "default",
])

# Nombres o patrones autorizados exclusivamente para pruebas
AUTHORIZED_TEST_DATABASES = frozenset([
    "minimarket_test_db",
])

def validate_test_database_target(url_str: str) -> None:
    """
    Validador estricto que intercepta y aborta cualquier intento de ejecutar
    pruebas contra la base de datos de desarrollo o producción.
    """
    if not url_str:
        raise ValueError("La URL de base de datos de pruebas no puede estar vacía.")

    parsed_url = make_url(url_str)

    # 1. Validación para motor SQLite
    if parsed_url.drivername.startswith("sqlite"):
        db_path = parsed_url.database or ""
        if db_path != ":memory:" and not ("test" in db_path.lower() or "tmp" in db_path.lower()):
            raise RuntimeError(
                f"SEGURIDAD CRÍTICA: Base de datos SQLite no autorizada para pruebas: '{db_path}'. "
                f"Solo se permiten bases en memoria (:memory:) o con 'test' en la ruta."
            )
        return

    # 2. Validación para motor PostgreSQL
    db_name = (parsed_url.database or "").strip().lower()

    if db_name in FORBIDDEN_DATABASES:
        raise RuntimeError(
            f"SEGURIDAD CRÍTICA INTERCEPTADA: Intento de conexión a la base protegida '{db_name}'. "
            f"Las pruebas tienen PROHIBICIÓN TOTAL de acceder a la base de datos de desarrollo 'minimarket_db'."
        )

    is_authorized = (
        db_name in AUTHORIZED_TEST_DATABASES or
        db_name.endswith("_test") or
        db_name.endswith("_test_db")
    )
    if not is_authorized:
        raise RuntimeError(
            f"SEGURIDAD CRÍTICA INTERCEPTADA: El nombre de base de datos '{db_name}' no está autorizado para pruebas. "
            f"La base debe llamarse explícitamente 'minimarket_test_db' o tener sufijo '_test'."
        )


def assert_connected_database_is_safe(connection) -> None:
    """
    Comprobación en caliente (live check) ejecutada antes de cualquier operación
    destructiva (DELETE, DROP, TRUNCATE) contra la conexión activa de la base de datos.
    """
    if connection.dialect.name == "postgresql":
        live_db = connection.execute(text("SELECT current_database();")).scalar()
        live_db = (live_db or "").strip().lower()
        if live_db in FORBIDDEN_DATABASES or not (
            live_db in AUTHORIZED_TEST_DATABASES or live_db.endswith("_test") or live_db.endswith("_test_db")
        ):
            raise RuntimeError(
                f"INTERCEPCIÓN EN VIVO: La sesión conectada reporta la base de datos '{live_db}'. "
                f"Operación destructiva cancelada inmediatamente por protección de datos."
            )


# ==============================================================================
# INICIALIZACIÓN SEGURA DEL MOTOR DE PRUEBAS
# ==============================================================================
# Puerto 5434: puerto dedicado exclusivo para postgres de pruebas (docker-compose.test.yml)
DEFAULT_POSTGRES_TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://test_user:test_password@localhost:5434/minimarket_test_db",
)

def init_test_engine():
    # 1. Intentar conectar a PostgreSQL de pruebas en puerto aislado (5434) o TEST_DATABASE_URL
    test_url = os.getenv("TEST_DATABASE_URL", DEFAULT_POSTGRES_TEST_URL)
    
    # Validar destino antes de intentar conectar
    try:
        validate_test_database_target(test_url)
        eng = create_engine(test_url, pool_pre_ping=True, pool_size=10, max_overflow=5)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
            assert_connected_database_is_safe(conn)
        safe_display_url = eng.url.render_as_string(hide_password=True)
        print(f"\n[TEST ENVIRONMENT] Motor: PostgreSQL | Base autorizada: {safe_display_url}")
        return eng, "postgresql"
    except Exception as e:
        # Si la validación de seguridad falló explícitamente, propagar el error de inmediato
        if "SEGURIDAD CRÍTICA" in str(e) or "INTERCEPCIÓN" in str(e):
            raise
        # Si falló la conexión por no estar levantado el puerto 5434, fallback a SQLite aislado
        pass

    # 2. Fallback seguro a SQLite en archivo temporal con modo WAL para pruebas unitarias
    import tempfile
    from sqlalchemy.pool import NullPool

    sqlite_path = os.path.join(tempfile.gettempdir(), "minimarket_test_isolated.db")
    validate_test_database_target(f"sqlite:///{sqlite_path}")

    eng = create_engine(
        f"sqlite:///{sqlite_path}",
        poolclass=NullPool,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    with eng.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.execute(text("PRAGMA busy_timeout=30000;"))
    print(f"\n[TEST ENVIRONMENT] Motor: SQLite (WAL) | Archivo temporal aislado: {sqlite_path}")
    return eng, "sqlite"


engine_test, DB_DIALECT = init_test_engine()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)


def get_reportes_app():
    """Carga reportes-api en un namespace propio (reportes_pkg) para evitar colisiones."""
    if "reportes_pkg.main" in sys.modules:
        return sys.modules["reportes_pkg.main"].app

    reportes_pkg = types.ModuleType("reportes_pkg")
    reportes_pkg.__path__ = [REPORTES_APP_DIR]
    sys.modules["reportes_pkg"] = reportes_pkg

    for mod_name in ["config", "database", "schemas", "metrics", "main"]:
        file_path = os.path.join(REPORTES_APP_DIR, f"{mod_name}.py")
        spec = importlib.util.spec_from_file_location(f"reportes_pkg.{mod_name}", file_path)
        mod = importlib.util.module_from_spec(spec)
        mod.__package__ = "reportes_pkg"
        sys.modules[f"reportes_pkg.{mod_name}"] = mod
        spec.loader.exec_module(mod)

    return sys.modules["reportes_pkg.main"].app


reportes_app = get_reportes_app()
reportes_get_db = sys.modules["reportes_pkg.database"].get_db


@pytest.fixture(scope="function")
def db():
    """Limpia las tablas y entrega una sesión lista para cada prueba en la base de tests."""
    with engine_test.connect() as conn:
        assert_connected_database_is_safe(conn)

    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()

    try:
        session.execute(text("DELETE FROM sale_items;"))
        session.execute(text("DELETE FROM sales;"))
        session.execute(text("DELETE FROM products;"))
        session.commit()
    except Exception:
        session.rollback()

    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def client(db):
    """TestClient para ventas-api entregando sesiones de base de datos de prueba independientes."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    ventas_app.dependency_overrides[ventas_get_db] = override_get_db
    with TestClient(ventas_app) as c:
        yield c
    ventas_app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def reportes_client(db):
    """TestClient para reportes-api apuntando a la misma base de datos de prueba."""
    def override_get_db():
        session = TestingSessionLocal()
        try:
            yield session
        finally:
            session.close()

    reportes_app.dependency_overrides[reportes_get_db] = override_get_db
    with TestClient(reportes_app) as c:
        yield c
    reportes_app.dependency_overrides.clear()
