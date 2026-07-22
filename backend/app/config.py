from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parent.parent / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")

    PROJECT_NAME: str = "Vet Clinic Workflow Automation"
    ENVIRONMENT: str = "development"
    DATABASE_URL: str = "postgresql+psycopg://vetclinic:vetclinic@localhost:5432/vetclinic"
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173"]

    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    GOOGLE_API_KEY: str | None = None
    GROQ_API_KEY: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
