from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://notifications:notif_pass@localhost:5432/notifications_db"
    )
    redis_url: str = "redis://localhost:6379/0"
    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@consulting-pm.local"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
