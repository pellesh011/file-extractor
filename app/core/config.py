from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://app:secret@localhost:5432/file_extractor"
    redis_url: str = "redis://localhost:6379/0"

    s3_endpoint_url: str = "http://localhost:9000"
    s3_access_key_id: str = "minioadmin"
    s3_secret_access_key: str = "minioadmin123"
    s3_bucket_name: str = "files"

    external_api_base_url: str = "http://localhost:8080"
    external_api_timeout_seconds: int = 30
    external_api_max_retries: int = 3

    log_level: str = "INFO"
    log_format: str = "structured"

    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/0"

    outbox_poll_interval_seconds: int = 5
    outbox_max_events_per_batch: int = 50


settings = Settings()
