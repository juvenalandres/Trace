from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://trace:trace@localhost:5432/trace"
    storage_dir: str = "./data/gpx"
    simplified_time_series_nth: int = 10
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    jwt_refresh_token_expire_days: int = 7
    cors_origins: str = "*"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False
    max_upload_size_mb: int = 50
    rate_limit_per_minute: int = 10
    allow_signup: bool = True
    segment_match_radius_m: int = 50
    segment_match_max: int = 5000

    model_config = {"env_prefix": "TRACE_", "env_file": ".env"}


settings = Settings()

if settings.jwt_secret in ("change-me-in-production", "change-me"):
    raise RuntimeError(
        "TRACE_JWT_SECRET is set to a placeholder value. "
        "Generate a real secret with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
    )
