from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    database_url: str = "sqlite:///./afisha.db"
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    admin_username: str = "admin"
    admin_password: str
    admin_email: str = "admin@afisha.ru"
    login_account_limit: int = Field(default=5, ge=1, le=1000)
    login_source_limit: int = Field(default=30, ge=1, le=10000)
    login_window_seconds: int = Field(default=900, ge=1, le=86400)

    @field_validator("secret_key")
    @classmethod
    def validate_secret(cls, value: str) -> str:
        if len(value) < 32 or value in {"your-secret-key-here", "change-me"} or value.startswith("REPLACE_"):
            raise ValueError("SECRET_KEY must be a random secret with at least 32 characters")
        return value

    @field_validator("admin_password")
    @classmethod
    def validate_admin_password(cls, value: str) -> str:
        if len(value) < 12 or value in {"admin123", "password", "changeme"} or value.startswith("REPLACE_"):
            raise ValueError("ADMIN_PASSWORD must be a strong password (12+ characters)")
        return value

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


settings = Settings()
