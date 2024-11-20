import json
import logging
from typing import Any
from fastapi import Response
import redis.asyncio as redis  # type: ignore[import-untyped]
from redis import RedisError

from app.config import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()


class RedisClient:
    def __init__(self):
        self.redis_client = redis.from_url(
            str(settings.redis_url), decode_responses=True
        )
        self.default_expiration_time = settings.redis_default_expiration_time

    async def get_cached_value_by_key(
        self, cache_key: str, response: Response | None = None
    ) -> Any:
        try:
            if cached_value := await self.redis_client.get(cache_key):
                if response:
                    response.headers["X-Cache-Status"] = "HIT"
                return json.loads(cached_value)
            elif response:
                response.headers["X-Cache-Status"] = "MISS"
                return None
        except RedisError as e:
            logger.warning("Redis error: %s", e)
            return None

    async def set_cache_value(
        self, cache_key: str, value: Any, ex: int | None = None
    ) -> None:
        await self.redis_client.set(
            cache_key,
            json.dumps(value),
            ex=ex or self.default_expiration_time,
        )

    async def key_exists(self, cache_key: str) -> bool:
        return await self.redis_client.exists(cache_key)

    async def delete_key(self, cache_key: str):
        return await self.redis_client.delete(cache_key)


def get_redis_client():
    return RedisClient()
