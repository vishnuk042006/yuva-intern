from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Telecom REST API"
    database_url: str = "sqlite:///./telecom.db"

    # JWT
    jwt_secret: str = "dev-only-change-me-use-a-long-random-secret-in-prod"
    jwt_algorithm: str = "HS256"
    access_token_minutes: int = 60
    bcrypt_rounds: int = 12

    # Redis cache (optional; API works without it)
    redis_url: str | None = None
    cache_ttl_seconds: int = 60

    # Abuse protection
    rate_limit_per_minute: int = 600
    auth_rate_limit_per_minute: int = 10
    max_body_bytes: int = 1_048_576
    cors_origins: list[str] = []

    # Demo data
    seed_on_startup: bool = True
    seed_admin_password: str = "Admin@12345"
    seed_staff_password: str = "Staff@12345"
    seed_user_password: str = "User@12345"

    log_level: str = "INFO"
