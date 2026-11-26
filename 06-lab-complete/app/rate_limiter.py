"""
Rate limiting (tiêu chí 7).
Tối đa RATE_LIMIT_PER_MINUTE request trong 60 giây (sliding window qua Redis sorted set).
Vượt giới hạn → HTTP 429 kèm Retry-After.
"""
import time
from fastapi import HTTPException
from app.config import settings
from app.redis_client import get_redis_client


def check_rate_limit(key: str) -> None:
    client = get_redis_client()
    if client is None:
        # Nếu Redis chưa sẵn sàng, cho qua để không chặn request
        return

    now = time.time()
    window = 60.0
    clear_before = now - window
    redis_key = f"ratelimit:{key}"

    try:
        pipe = client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, clear_before)
        pipe.zcard(redis_key)
        pipe.zadd(redis_key, {str(now): now})
        pipe.expire(redis_key, int(window) + 5)
        results = pipe.execute()

        request_count = results[1]
        if request_count >= settings.rate_limit_per_minute:
            # Lấy timestamp cũ nhất trong window để tính retry after
            oldest = client.zrange(redis_key, 0, 0, withscores=True)
            retry_after = int(window - (now - oldest[0][1])) if oldest else 60
            retry_after = max(1, retry_after)
            raise HTTPException(
                status_code=429,
                detail=f"Rate limit exceeded ({settings.rate_limit_per_minute} req/min).",
                headers={"Retry-After": str(retry_after)},
            )
    except HTTPException:
        raise
    except Exception:
        # Lỗi Redis thì bỏ qua để fail-open
        pass
