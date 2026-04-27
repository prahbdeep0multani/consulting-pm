from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://projects:projects_pass@localhost:5432/projects_db"
    redis_url: str = "redis://localhost:6379/0"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_attachments: str = "attachments"
    minio_use_ssl: bool = False
    presigned_url_expire_seconds: int = 300

    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
