from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="BULLYMARKET_",
        extra="ignore",
    )

    app_name: str = "BullyMarket API"
    environment: str = "development"
    database_url: str = "postgresql+asyncpg://bullymarket:bullymarket@localhost/bullymarket"
    jwt_secret: str = Field(
        default="development-only-change-me-use-at-least-32-bytes",
        min_length=32,
    )
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 1440
    default_starting_balance: int = 1000
    default_liquidity_seed: int = 100
    default_lmsr_liquidity: int = 100
    minimum_trade_amount: int = 1
    refill_amount: int = 500
    refill_interval_days: int = 7
    cors_origins: list[str] = ["http://localhost:3000"]
    frontend_url: str = "http://localhost:3000"
    verification_code_minutes: int = 10
    verification_max_attempts: int = 5
    verification_resend_seconds: int = 60
    email_enabled: bool = False
    smtp_host: str = "smtp-relay.brevo.com"
    smtp_port: int = 587
    smtp_security: Literal["starttls", "ssl", "none"] = "starttls"
    smtp_username: str = ""
    smtp_password: SecretStr | None = None
    email_from_address: str = "no-reply@example.com"
    email_from_name: str = "BullyMarket"
    notification_worker_interval_seconds: int = 30
    email_delivery_batch_size: int = 20


@lru_cache
def get_settings() -> Settings:
    return Settings()
