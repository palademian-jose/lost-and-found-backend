from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="LOSTFOUND_",
        extra="ignore",
    )

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/lostfound"
    environment: str = "development"
    db_echo: bool = False
    jwt_secret_key: str = "SECRET_KEY"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30
    auth_login_rate_limit: int = 10
    auth_login_rate_window_seconds: int = 60
    auth_register_rate_limit: int = 5
    auth_register_rate_window_seconds: int = 300
    item_write_rate_limit: int = 20
    item_write_rate_window_seconds: int = 60
    claim_submit_rate_limit: int = 10
    claim_submit_rate_window_seconds: int = 300
    claim_decision_rate_limit: int = 20
    claim_decision_rate_window_seconds: int = 60
    cors_allowed_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_create_schema_on_startup: bool = True
    repair_schema_on_startup: bool = True

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, value):
        if isinstance(value, str):
            if value.startswith("postgres://"):
                return value.replace("postgres://", "postgresql+asyncpg://", 1)

            if value.startswith("postgresql://"):
                return value.replace("postgresql://", "postgresql+asyncpg://", 1)

        return value

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_allowed_origins.split(",")
            if origin.strip()
        ]

    @model_validator(mode="after")
    def require_secure_jwt_secret(self):
        if (
            self.environment.lower() not in {"development", "dev", "local", "test"}
            and self.jwt_secret_key == "SECRET_KEY"
        ):
            raise ValueError("LOSTFOUND_JWT_SECRET_KEY must be set outside development.")

        return self


settings = Settings()
