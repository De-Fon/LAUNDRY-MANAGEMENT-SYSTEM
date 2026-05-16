from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    app_name: str = "Campus Laundry O2O System"
    debug: bool = False
    database_url: str = "sqlite:///./laundry_management.db"
    redis_url: str = "redis://localhost:6379"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 30

    resend_api_key: str | None = None
    resend_from_email: str = "notifications@campuslaundry.co.ke"
    resend_from_name: str = "Campus Laundry"

    environment: str = "development"
    algorithm: str = "HS256"
    at_api_key: str | None = None
    at_username: str | None = "sandbox"

    daraja_environment: str = "sandbox"
    daraja_consumer_key: str | None = None
    daraja_consumer_secret: str | None = None
    daraja_business_short_code: str = "174379"
    daraja_passkey: str | None = None
    daraja_callback_url: str | None = None
    daraja_account_reference_prefix: str = "HELB"
    daraja_transaction_desc: str = "Loan repayment"
    daraja_request_timeout_seconds: int = 30
    daraja_stk_timeout_minutes: int = 3
    daraja_reconciliation_interval_minutes: int = 2
    daraja_max_query_retries: int = 5

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @field_validator("debug", mode="before")
    @classmethod
    def parse_debug_flag(cls, value: object) -> object:
        if isinstance(value, str) and value.lower() in {"release", "prod", "production"}:
            return False
        return value

@lru_cache
def get_settings() -> Settings:
    return Settings()
