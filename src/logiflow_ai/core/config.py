from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_hostaddr: str | None = None
    app_name: str = "LogiFlow AI"
    app_version: str = "0.1.0"
    app_env: str = "development"

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "logiflow"
    db_user: str = "logiflow"
    db_password: str = "logiflow_dev_password"
    alerts_email_to: str = "operacoes@example.com"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def database_url(self) -> str:
        return (
            "postgresql+psycopg://"
            f"{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
