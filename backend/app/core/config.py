from typing import Optional
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Orchestration Platform"

    DATABASE_URL: Optional[str] = None

    POSTGRES_USER:     Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_SERVER:   Optional[str] = "localhost"
    POSTGRES_PORT:     Optional[str] = "5432"
    POSTGRES_DB:       Optional[str] = None

    SECRET_KEY: str

    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440

    ALLOWED_ORIGINS: str = "http://localhost:5173"

    # Google Maps API key (optional) — enables real distance/time/route data
    # in the DMFE engine.  When absent, haversine-based fallbacks are used.
    GOOGLE_MAPS_API_KEY: Optional[str] = None


    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        if self.POSTGRES_USER and self.POSTGRES_PASSWORD and self.POSTGRES_DB:
            return (
                f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
                f"@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            )
        return "sqlite:///./dmfe_dev.db"

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
