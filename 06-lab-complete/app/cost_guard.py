"""
Cost guard (tiêu chí 8).
Cộng dồn chi phí LLM vào Redis. Vượt DAILY_BUDGET_USD → HTTP 402.
"""
import time
from datetime import datetime, timezone
from fastapi import HTTPException
from app.config import settings
from app.redis_client import get_redis_client

PRICE_INPUT_PER_1K = 0.00015
PRICE_OUTPUT_PER_1K = 0.0006


def _budget_key() -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    return f"cost:{today}"


def check_budget() -> None:
    client = get_redis_client()
    if client is None:
        return
    try:
        total = float(client.get(_budget_key()) or 0.0)
        if total >= settings.daily_budget_usd:
            raise HTTPException(
                status_code=402,
                detail=f"Daily budget exceeded: ${total:.6f} >= ${settings.daily_budget_usd:.6f}",
            )
    except HTTPException:
        raise
    except Exception:
        pass


def record_cost(input_tokens: int, output_tokens: int) -> float:
    client = get_redis_client()
    cost = (input_tokens / 1000.0) * PRICE_INPUT_PER_1K + (output_tokens / 1000.0) * PRICE_OUTPUT_PER_1K
    if client is None:
        return cost
    try:
        key = _budget_key()
        client.incrbyfloat(key, cost)
        client.expire(key, 86400 * 2)
    except Exception:
        pass
    return cost
