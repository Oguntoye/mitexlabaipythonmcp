import redis
import os
from typing import Optional
from ..env import settings

redis_client: redis.Redis = redis.Redis(
    host=settings.REDISHOST,
    port=settings.REDISPORT,
    decode_responses=True
)

def test_redis_connection():
    """Test Redis connection on import"""
    try:
        redis_client.ping()
    except redis.ConnectionError as e:
        raise RuntimeError(f"Cannot connect to Redis at {settings.REDISHOST}:{settings.REDISPORT}") from e

test_redis_connection()