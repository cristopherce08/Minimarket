import os
import sys
import types
import importlib.util
import logging
import tempfile
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import NullPool
from fastapi.testclient import TestClient

logger = logging.getLogger("tests")

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENTAS_PATH = os.path.join(BASE_DIR, "src", "ventas-api")
REPORTES_APP_DIR = os.path.join(BASE_DIR, "src", "reportes-api", "app")

if VENTAS_PATH not in sys.path:
    sys.path.insert(0, VENTAS_PATH)

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

# Base de datos autorizada exclusivamente para pruebas de integración
AUTHORIZED_TEST_DATABASES = frozenset([
    "minimarket_test_db",
])

# Puerto reservado exclusivamente para la base de datos de desarrollo
FORBIDDEN_PORTS = frozenset([5433])


def validate_test_database_target(url_str: str) -> None:
    """
    Validador estricto de seguridad que intercepta y aborta de inmediato
    cualquier intento de ejecutar pruebas contra bases de desarrollo o producción.
    """
    if not url_str:
        raise ValueError("La URL de base de datos de pruebas no puede estar vacía.")

    parsed_url = make_url(url_str)

    # 1. Validación para motor SQLite
    if parsed_url.drivername.startswith("sqlite"):
        db_path = parsed_url.database or ""
        if db_path != ":memory:" and not ("test" in db_path.lower() or "tmp" in db_path.lower()):
            raise RuntimeError(
                f"SEGURIDAD CRÍTICA INTERCEPTADA: Base de datos SQLite no autorizada para pruebas: '{db_path}'. "
                f"Solo se permiten bases en memoria (:memory:) o con 'test'/'tmp' en la ruta."
            )
        return

    # 2. Validación de puertos protegidos (desarrollo / producción)
    if parsed_url.port in FORBIDDEN_PORTS:
        raise RuntimeError(
            f"SEGURIDAD CRÍTICA INTERCEPTADA: El puerto {parsed_url.port} corresponde al PostgreSQL "
            f"de desarrollo ('minimarket_db'). Prohibido su uso para pruebas."
        )

    # 3. Validación de nombre de base de datos
    db_name = (parsed_url.database or "").strip().lower()

    if db_name in FORBIDDEN_DATABASES:
        raise RuntimeError(
            f"SEGURIDAD CRÍTICA INTERCEPTADA: Intento de conexión a la base protegida '{db_name}'. "
            f"Las pruebas tienen PROHIBICIÓN TOTAL de acceder a la base de datos de desarrollo 'minimarket_db'."
        )

    if db_name not in AUTHORIZED_TEST_DATABASES:
        raise RuntimeError(
            f"SEGURIDAD CRÍTICA INTERCEPTADA: La base de datos '{db_name}' no está autorizada para pruebas. "
            f"Las pruebas de integración están restringidas exclusivamente a 'minimarket_test_db'."
        )


def assert_connected_database_is_safe(connection) -> None:
    """
    Comprobación en caliente (live check) antes de cualquier operación destructiva.
    """
    if connection.dialect.name == "postgresql":
        live_db = connection.execute(text("SELECT current_database();")).scalar()
        live_db = (live_db or "").strip().lower()
        if live_db in FORBIDDEN_DATABASES:
            raise RuntimeError(
                f"INTERCEPCIÓN EN VIVO: La sesión conectada reporta la base protegida '{live_db}'. "
                f"Operación cancelada inmediatamente por protección de datos."
            )
        if live_db not in AUTHORIZED_TEST_DATABASES:
            raise RuntimeError(
                f"INTERCEPCIÓN EN VIVO: La base '{live_db}' no está en la lista de bases autorizadas ('minimarket_test_db')."
            )


# ==============================================================================
# RESOLUCIÓN FAIL-CLOSED Y CONFIGURACIÓN TEMPRANA DEL ENTORNO
# ==============================================================================
USE_SQLITE_FLAG = os.getenv("USE_SQLITE_UNIT_TESTS", "0").strip().lower() in ("1", "true", "yes")
DEFAULT_POSTGRES_TEST_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://test_user:test_password@localhost:5434/minimarket_test_db",
)


def init_test_engine(custom_url: str = None, force_sqlite: bool = False):
    """
    Inicializa el motor de pruebas con comportamiento fail-closed:
    - Si force_sqlite o USE_SQLITE_UNIT_TESTS=1, inicializa SQLite aislado para unit tests.
    - De lo contrario, exige PostgreSQL de pruebas en localhost:5434 (minimarket_test_db).
      Si no responde, falla con mensaje explícito sin fallback silencioso a SQLite.
    """
    is_sqlite = force_sqlite or USE_SQLITE_FLAG
    if is_sqlite:
        sqlite_path = os.path.join(tempfile.gettempdir(), "minimarket_test_isolated.db")
        sqlite_url = f"sqlite:///{sqlite_path}"
        validate_test_database_target(sqlite_url)
        os.environ["DATABASE_URL"] = sqlite_url

        eng = create_engine(
            sqlite_url,
            poolclass=NullPool,
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        with eng.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL;"))
            conn.execute(text("PRAGMA busy_timeout=30000;"))
        print(f"\n[TEST ENVIRONMENT] Modo Unitario Explícito: SQLite (WAL) | Archivo: {sqlite_path}")
        return eng, "sqlite", sqlite_url

    # Modo Integración PostgreSQL (Fail-Closed)
    test_url = custom_url or os.getenv("TEST_DATABASE_URL", DEFAULT_POSTGRES_TEST_URL)
    validate_test_database_target(test_url)

    # Pre-configurar DATABASE_URL en el entorno ANTES de cualquier importación de aplicación
    os.environ["DATABASE_URL"] = test_url

    try:
        eng = create_engine(test_url, pool_pre_ping=True, pool_size=10, max_overflow=5)
        with eng.connect() as conn:
            conn.execute(text("SELECT 1;"))
            assert_connected_database_is_safe(conn)
        safe_display_url = eng.url.render_as_string(hide_password=True)
        print(f"\n[TEST ENVIRONMENT] Motor: PostgreSQL | Base autorizada: {safe_display_url}")
        return eng, "postgresql", test_url
    except Exception as e:
        if "SEGURIDAD CRÍTICA" in str(e) or "INTERCEPCIÓN" in str(e):
            raise
        # Fail-Closed: Mensaje claro con instrucciones precisas para levantar el entorno
        raise RuntimeError(
            "\n" + "=" * 80 + "\n"
            "FALLO DE CONEXIÓN AL POSTGRESQL DE PRUEBAS (COMPORTAMIENTO FAIL-CLOSED):\n"
            f"No fue posible conectar a la base de pruebas autorizada: {test_url}\n"
            f"Error reportado: {e}\n\n"
            "Las pruebas de integración y concurrencia requieren PostgreSQL de pruebas.\n"
            "El fallback silencioso a SQLite está deshabilitado para evitar falsos positivos.\n\n"
            "Para iniciar la instancia PostgreSQL de pruebas en RAM (puerto 5434), ejecute:\n"
            "    docker compose -f docker-compose.test.yml up -d\n\n"
            "Para ejecutar únicamente pruebas unitarias con SQLite, defina:\n"
            "    export USE_SQLITE_UNIT_TESTS=1\n"
            + "=" * 80
        ) from e


# 1. Inicializar motor y fijar DATABASE_URL en os.environ antes de importar modelos o apps
engine_test, DB_DIALECT, ACTIVE_TEST_DB_URL = init_test_engine()
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine_test)

# 2. AHORA importar los módulos de ventas-api (ya con DATABASE_URL apuntando a la base de prueba)
from app.models import Base
import app.database as ventas_db
import app.main as ventas_main
from app.database import get_db as ventas_get_db
from app.main import app as ventas_app

# 3. Forzar explícitamente que todos los componentes de ventas-api utilicen engine_test
ventas_db.engine = engine_test
ventas_db.SessionLocal = TestingSessionLocal
ventas_main.engine = engine_test

# 4. Cargar reportes-api en namespace propio asegurando también engine_test
def get_reportes_app():
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

    # Inyectar motor de pruebas en reportes-api
    sys.modules["reportes_pkg.database"].engine = engine_test
    sys.modules["reportes_pkg.database"].SessionLocal = TestingSessionLocal

    return sys.modules["reportes_pkg.main"].app


reportes_app = get_reportes_app()
reportes_get_db = sys.modules["reportes_pkg.database"].get_db

# Crear tablas en la base de pruebas antes de iniciar
Base.metadata.create_all(bind=engine_test)


# ==============================================================================
# FIXTURES PYTEST
# ==============================================================================
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
