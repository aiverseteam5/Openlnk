"""Application configuration from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Environment-based settings. Loaded from .env or Infisical in prod."""

    # Database (Supabase Mumbai — DB-only, ADR-007)
    database_url: str = "postgresql+asyncpg://openlnk_app:dev_password@localhost:5433/openlnk_dev"

    # Redis — two instances per eng review A1 decision
    redis_jobs_url: str = "redis://localhost:6379/0"  # AOF on, durable arq
    redis_extraction_url: str = "redis://localhost:6380/0"  # No persistence, ADR-002

    # Auth (MSG91 OTP — ADR-007)
    msg91_auth_key: str = ""
    jwt_secret: str = "dev-secret-change-in-prod"  # noqa: S105
    jwt_algorithm: str = "HS256"

    # Extraction (ADR-002)
    extraction_timeout_text_secs: int = 60
    extraction_timeout_media_secs: int = 120  # voice/camera — eng review tension resolution

    # Extraction confidence threshold (OL-029a — versioned, not hardcoded)
    extraction_confidence_threshold: float = 0.85

    # LLM (provider TBD — TODOS T-001 DPDP review)
    llm_api_key: str = ""
    llm_model: str = ""
    llm_base_url: str = ""

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
