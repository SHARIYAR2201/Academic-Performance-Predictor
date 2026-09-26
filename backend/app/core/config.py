from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central application configuration, loaded from environment / .env.

    Never hard-code secrets here — every value is overridable via env vars,
    and defaults below are safe only for local development.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # App
    PROJECT_NAME: str = "Academic Performance Prediction & Early-Warning System"
    ENVIRONMENT: str = "development"
    API_V1_PREFIX: str = "/api"

    # Database
    DATABASE_URL: str = "postgresql+psycopg2://postgres:postgres@localhost:5432/academic_predictor"

    # Auth / JWT
    SECRET_KEY: str = "CHANGE_ME_IN_PRODUCTION"  # noqa: S105 - dev-only default, must be overridden
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    # ML artifacts
    MODEL_REGISTRY_DIR: str = "../ml/inference/registry"


@lru_cache
def get_settings() -> Settings:
    return Settings()
