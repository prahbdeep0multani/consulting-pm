from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://billing:billing_pass@localhost:5432/billing_db"
    redis_url: str = "redis://localhost:6379/0"
    timelog_service_url: str = "http://timelog:8003"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"


settings = Settings()
