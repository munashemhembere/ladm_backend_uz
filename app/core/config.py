from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )
    APP_NAME: str = "LADM UZ Smart Campus Digital Twin API"
    APP_VERSION: str = "2.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480
    DATABASE_URL: str = "postgresql+asyncpg://postgres:password@localhost:5432/ladm_uz"
    SYNC_DATABASE_URL: str = "postgresql://postgres:password@localhost:5432/ladm_uz"
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]


settings = Settings()
