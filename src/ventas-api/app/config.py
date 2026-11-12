from pydantic_settings import BaseSettings
from pydantic import Field, ConfigDict


class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = Field(
        default="postgresql://minimarket_user:minimarket_password@localhost:5433/minimarket_db",
        description="URL de conexión a la base de datos PostgreSQL o SQLite de prueba",
    )
    APP_NAME: str = "MiniMarket Cloud — Ventas API"
    APP_PORT: int = 8000
    LOW_STOCK_THRESHOLD: int = 5
    CORS_ORIGINS: str = "*"

    # Configuración de pool calibrada para PostgreSQL max_connections=100
    # Con 5 réplicas HPA: 5 * (5 pool + 5 overflow) = 50 conexiones máx.
    # Deja 50 conexiones libres para reportes-api (10), Spark JDBC (20) y Kubelet/admin (20).
    DB_POOL_SIZE: int = Field(default=5, description="Tamaño base del pool de conexiones")
    DB_MAX_OVERFLOW: int = Field(default=5, description="Conexiones adicionales máximas sobre el pool")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Timeout en segundos para obtener conexión")
    DB_POOL_RECYCLE: int = Field(default=1800, description="Tiempo de reciclaje de conexiones en segundos")


settings = Settings()
