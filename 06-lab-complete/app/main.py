"""
Production AI Agent — Part 6 Final Project
"""
import json
import logging
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, Request, Response, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.config import settings
from app.auth import verify_api_key
from app.rate_limiter import check_rate_limit
from app.cost_guard import check_budget, record_cost
from app.redis_client import redis_healthy
from utils.mock_llm import ask as llm_ask


# Tiêu chí 10 — Structured logging: Mỗi dòng log của app là 1 JSON object hợp lệ
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(record.created)),
            "lvl": record.levelname,
            "msg": record.getMessage(),
            "logger": record.name,
        }
        if hasattr(record, "props"):
            log_entry.update(record.props)
        return json.dumps(log_entry)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())

logger = logging.getLogger("app")
logger.setLevel(logging.INFO)
logger.handlers = [handler]
logger.propagate = False

is_ready = False


@asynccontextmanager
async def lifespan(app: FastAPI):
    global is_ready
    logger.info("Application starting up", extra={"props": {"event": "startup"}})
    is_ready = True
    yield
    is_ready = False
    logger.info("Application shutting down gracefully", extra={"props": {"event": "shutdown"}})


app = FastAPI(title="Production AI Agent", lifespan=lifespan)


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    user_id: Optional[str] = "default"


# Tiêu chí 4: GET /health — liveness: luôn trả 200 khi process còn chạy
@app.get("/health")
def health():
    return {"status": "ok"}


# Tiêu chí 5: GET /ready — readiness: 200 khi sẵn sàng, 503 khi Redis không kết nối được
@app.get("/ready")
def ready():
    if not is_ready or not redis_healthy():
        return JSONResponse(status_code=503, content={"status": "not ready", "redis": False})
    return {"status": "ready", "redis": True}


@app.post("/ask")
def ask(body: AskRequest, key: str = Depends(verify_api_key)):
    start_time = time.time()
    # Tiêu chí 7: Rate limit check (429)
    check_rate_limit(key)
    # Tiêu chí 8: Cost guard check (402)
    check_budget()

    # Gọi Mock LLM
    answer = llm_ask(body.question)

    # Ước lượng tokens & lưu chi phí
    in_tok = max(1, len(body.question.split()))
    out_tok = max(1, len(answer.split()))
    cost = record_cost(in_tok, out_tok)

    duration_ms = round((time.time() - start_time) * 1000, 2)
    logger.info(
        "Handled ask request",
        extra={"props": {"event": "request", "path": "/ask", "status": 200, "ms": duration_ms, "cost_usd": cost}},
    )
    return {"question": body.question, "answer": answer}
