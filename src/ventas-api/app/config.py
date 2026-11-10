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


settings = Settings()
