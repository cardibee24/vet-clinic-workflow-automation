from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
DEFAULT_JWT_SECRET_KEY = "change-me-in-production"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    PROJECT_NAME: str = "Vet Clinic Workflow Automation"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+psycopg://vetclinic:vetclinic@localhost:5432/vetclinic"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    JWT_SECRET_KEY: str = DEFAULT_JWT_SECRET_KEY
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    if settings.ENVIRONMENT == "production" and settings.JWT_SECRET_KEY == DEFAULT_JWT_SECRET_KEY:
        raise RuntimeError(
            "JWT_SECRET_KEY is still the default placeholder. "
            "Set a real secret via the JWT_SECRET_KEY environment variable before running in production."
        )
    return settings
