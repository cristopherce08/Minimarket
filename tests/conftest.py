import os
import sys
import types
import importlib.util
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
VENTAS_PATH = os.path.join(BASE_DIR, "src", "ventas-api")
REPORTES_APP_DIR = os.path.join(BASE_DIR, "src", "reportes-api", "app")

if VENTAS_PATH not in sys.path:
    sys.path.insert(0, VENTAS_PATH)

from app.models import Base
from app.database import get_db as ventas_get_db
from app.main import app as ventas_app

# URLs candidatas para base de datos de pruebas (PostgreSQL independiente vs SQLite fallback)
PG_CANDIDATE_URLS = [
    os.getenv("TEST_DATABASE_URL"),
    "postgresql+psycopg://test_user:test_password@localhost:5434/minimarket_test_db",
    "postgresql+psycopg://minimarket_user:minimarket_password@localhost:5433/minimarket_db",
]

def init_test_engine():
    # 1. Probar conexiones PostgreSQL reales independientes
    for url in PG_CANDIDATE_URLS:
        if not url:
            continue
        try:
            eng = create_engine(url, pool_pre_ping=True, pool_size=20, max_overflow=10)
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            return eng, "postgresql"
        except Exception:
            continue

    # 2. Fallback a SQLite en archivo temporal con modo WAL para permitir concurrencia en pruebas aisladas
    import tempfile
    from sqlalchemy.pool import NullPool
    
    sqlite_path = os.path.join(tempfile.gettempdir(), "minimarket_test_isolated.db")
    eng = create_engine(
        f"sqlite:///{sqlite_path}",
        poolclass=NullPool,
        connect_args={"check_same_thread": False, "timeout": 30},
    )
    with eng.connect() as conn:
        conn.execute(text("PRAGMA journal_mode=WAL;"))
        conn.execute(text("PRAGMA busy_timeout=30000;"))
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
    """Limpia las tablas y entrega una sesión lista para cada prueba."""
    Base.metadata.create_all(bind=engine_test)
    session = TestingSessionLocal()
    
    # Limpieza previa de tablas para aislamiento completo
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
    """TestClient para ventas-api entregando sesiones de base de datos independientes."""
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
    """TestClient para reportes-api apuntando a la misma base de datos."""
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
