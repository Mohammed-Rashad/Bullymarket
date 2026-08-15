from functools import lru_cache

from pydantic import Field
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


@lru_cache
def get_settings() -> Settings:
    return Settings()
