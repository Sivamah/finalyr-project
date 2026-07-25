from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI-Powered Unified Mobility and Delivery System"

    # Optional direct DB URL (takes precedence)
    DATABASE_URL: Optional[str] = None

    # PostgreSQL settings (used if DATABASE_URL is not set)
    POSTGRES_USER:     Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_SERVER:   Optional[str] = "localhost"
    POSTGRES_PORT:     Optional[str] = "5432"
    POSTGRES_DB:       Optional[str] = None

    SECRET_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:5173"  # Comma-separated in production


    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        # 1. Explicit DATABASE_URL
        if self.DATABASE_URL:
            return self.DATABASE_URL
        # 2. Full PostgreSQL URI from individual settings
        if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        # 3. SQLite fallback for local development (no external DB needed)
        return "sqlite:///./dmfe_dev.db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
