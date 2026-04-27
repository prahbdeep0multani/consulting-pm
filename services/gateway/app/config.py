from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    jwt_public_key: str = ""
    jwt_public_key_path: str = ""

    upstream_auth: str = "http://auth:8001"
    upstream_projects: str = "http://projects:8002"
    upstream_timelog: str = "http://timelog:8003"
    upstream_billing: str = "http://billing:8004"
    upstream_resources: str = "http://resources:8005"
    upstream_notifications: str = "http://notifications:8006"

    redis_url: str = "redis://localhost:6379/0"

    rate_limit_per_ip_rps: int = 100
    rate_limit_per_tenant_rps: int = 500
    tenant_cache_ttl_seconds: int = 300

    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000"

    def get_public_key(self) -> str:
        if self.jwt_public_key:
            return self.jwt_public_key
        if self.jwt_public_key_path:
            with open(self.jwt_public_key_path) as f:
                return f.read()
        raise ValueError("JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH must be set")


settings = Settings()
