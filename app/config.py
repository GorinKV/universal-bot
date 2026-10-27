"""Загрузка конфигурации из .env через pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Telegram
    bot_token: str
    admin_id: int

    # Logging
    log_level: str = "INFO"

    # GigaChat (Ф1b)
    gigachat_client_id: str = ""
    gigachat_client_secret: str = ""

    # MariaDB (Ф3)
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""


settings = Settings()

