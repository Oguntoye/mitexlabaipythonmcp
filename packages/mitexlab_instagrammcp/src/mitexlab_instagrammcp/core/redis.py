import redis.asyncio as redis
from typing import Optional
from ..env import settings


# Use the asyncio Redis client
redis_client: redis.Redis = redis.Redis(
    host=settings.REDISHOST,
    port=settings.REDISPORT,
    decode_responses=True
)


async def test_redis_connection():
    """Test Redis connection on import"""
    try:
        await redis_client.ping()
    except redis.ConnectionError as e:
        raise RuntimeError(
            f"Cannot connect to Redis at {settings.REDISHOST}:{settings.REDISPORT}"
        ) from e