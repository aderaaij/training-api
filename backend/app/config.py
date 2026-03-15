from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / "config" / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str
    api_key: str
    environment: str = "LOCAL"
    db_host: str | None = None

    @property
    def db_uri(self) -> str:
        uri = self.database_url
        if self.db_host:
            # Replace hostname in URI for Docker networking
            import re
            uri = re.sub(r"@[^:]+:", f"@{self.db_host}:", uri)
        return uri


@lru_cache()
def get_settings() -> Settings:
    return Settings()
