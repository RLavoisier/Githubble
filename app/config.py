import os
from functools import lru_cache
from typing import Optional

from pydantic import PostgresDsn, RedisDsn, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = os.path.join(os.path.dirname(__file__), ".env")


class Settings(BaseSettings):
    postgres_db: PostgresDsn

    # GitHub
    github_api_base_url: HttpUrl = "https://api.github.com/"
    github_token: Optional[str] = None

    # Redis
    redis_url: RedisDsn
    redis_default_expiration_time: int = 3600 * 24
    use_redis_cache: bool

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8")


@lru_cache
def get_settings() -> Settings:
    return Settings()
