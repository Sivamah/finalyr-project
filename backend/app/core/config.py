from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    PROJECT_NAME: str = "AI Orchestration Platform"

    DATABASE_URL: Optional[str] = None

    POSTGRES_USER:     Optional[str] = None
    POSTGRES_PASSWORD: Optional[str] = None
    POSTGRES_SERVER:   Optional[str] = "localhost"
    POSTGRES_PORT:     Optional[str] = "5432"
    POSTGRES_DB:       Optional[str] = None

    # No hard default: the app exits at import time if SECRET_KEY is missing
    # from the environment/.env, which is a common cause of "backend won't
    # start" on fresh deploys.  Keep a dev fallback so the platform always
    # boots; a startup warning is logged when the fallback is used.
    SECRET_KEY: str = "aiorch-dev-secret-change-me-in-production"

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
        return f"sqlite:///{BACKEND_DIR / 'dmfe_dev.db'}"

    # Absolute path, independent of the CWD the backend is started from.
    # A relative ".env" breaks SECRET_KEY/DATABASE_URL/ALLOWED_ORIGINS
    # whenever uvicorn is launched from the repo root, which prevents
    # the backend from booting and makes login look broken.
    model_config = SettingsConfigDict(
        env_file=BACKEND_DIR / ".env",
        extra="ignore",
    )


settings = Settings()


if settings.SECRET_KEY in ("aiorch-dev-secret-change-me-in-production", "", None):
    import logging
    logging.getLogger("aiorch").warning(
        "SECRET_KEY not configured — using insecure development fallback. "
        "Set SECRET_KEY in backend/.env for production."
    )
