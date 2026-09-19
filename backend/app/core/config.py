from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # AI
    gemini_api_key: str = ""

    # Ollama (local AI)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "deepseek-v4-flash:cloud"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "dev_secret_change_in_production"
    # Comma-separated list, e.g. "http://localhost:3000,https://example.com"
    cors_origins: str = "http://localhost:3000"

    # Storage
    storage_backend: str = "local"  # "local" | "s3"
    local_storage_path: str = "/tmp/repurposer_jobs"
    file_ttl_seconds: int = 86400  # 24 hours

    # S3 (optional)
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "eu-central-1"
    s3_bucket: str = ""

    # Rate limiting
    rate_limit_per_day: int = 5

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
