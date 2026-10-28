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

    # GigaChat
    gigachat_credentials: str = ""
    gigachat_scope: str = "GIGACHAT_API_PERS"
    gigachat_model: str = "GigaChat-2"

    # Whisper (Ф2)
    whisper_cli: str = "/home/kvg/whisper.cpp/build/bin/whisper-cli"
    whisper_model: str = "/home/kvg/whisper.cpp/models/ggml-base.bin"

    # MariaDB (Ф3)
    db_host: str = "127.0.0.1"
    db_port: int = 3306
    db_user: str = ""
    db_password: str = ""
    db_name: str = ""


settings = Settings()  # type: ignore[call-arg]
