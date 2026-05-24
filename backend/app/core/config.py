from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # AI
    gemini_api_key: str = ""

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "dev_secret_change_in_production"
    cors_origins: list[str] = ["http://localhost:3000"]

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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
