from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+asyncpg://auth:auth_pass@localhost:5432/auth_db"
    redis_url: str = "redis://localhost:6379/0"

    jwt_private_key: str = ""  # RSA PEM, loaded from env or file
    jwt_public_key: str = ""
    jwt_private_key_path: str = ""
    jwt_public_key_path: str = ""
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 30

    smtp_host: str = "localhost"
    smtp_port: int = 1025
    smtp_from: str = "noreply@consulting-pm.local"

    log_level: str = "INFO"
    environment: str = "development"
    cors_origins: str = "http://localhost:3000"

    def get_private_key(self) -> str:
        if self.jwt_private_key:
            return self.jwt_private_key
        if self.jwt_private_key_path:
            with open(self.jwt_private_key_path) as f:
                return f.read()
        raise ValueError("JWT_PRIVATE_KEY or JWT_PRIVATE_KEY_PATH must be set")

    def get_public_key(self) -> str:
        if self.jwt_public_key:
            return self.jwt_public_key
        if self.jwt_public_key_path:
            with open(self.jwt_public_key_path) as f:
                return f.read()
        raise ValueError("JWT_PUBLIC_KEY or JWT_PUBLIC_KEY_PATH must be set")


settings = Settings()
