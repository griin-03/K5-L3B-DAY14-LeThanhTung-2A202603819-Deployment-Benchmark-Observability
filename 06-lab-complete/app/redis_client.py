"""
Kết nối Redis dùng chung cho rate limiter và cost guard.
"""
import urllib.parse
import redis
from app.config import settings

r = None
if settings.redis_url:
    try:
        r = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1.0)
    except Exception:
        r = None


def get_redis_client():
    global r
    if r is not None:
        return r
    if settings.redis_url:
        try:
            r = redis.from_url(settings.redis_url, decode_responses=True, socket_timeout=1.0)
            return r
        except Exception:
            return None
    return None


def redis_healthy() -> bool:
    client = get_redis_client()
    if client is None:
        return False
    try:
        return bool(client.ping())
    except Exception:
        return False
