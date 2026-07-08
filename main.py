import asyncio
import os
import time
import uuid
from collections import defaultdict, deque
from typing import Deque

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse


ASSIGNED_ORIGIN = "https://app-3urmir.example.com"
RATE_LIMIT = 14
RATE_LIMIT_WINDOW_SECONDS = 10.0


def get_allowed_origins() -> list[str]:
    origins = [ASSIGNED_ORIGIN]
    exam_origin = os.getenv("EXAM_ORIGIN", "").strip()
    if exam_origin and exam_origin not in origins:
        origins.append(exam_origin)
    return origins


app = FastAPI(title="Middleware Stack Assignment")

_rate_limit_buckets: dict[str, Deque[float]] = defaultdict(deque)
_rate_limit_lock = asyncio.Lock()


@app.middleware("http")
async def per_client_rate_limit_middleware(request: Request, call_next):
    if request.method.upper() == "OPTIONS":
        return await call_next(request)

    client_id = request.headers.get("x-client-id") or "anonymous"
    now = time.monotonic()

    async with _rate_limit_lock:
        bucket = _rate_limit_buckets[client_id]
        while bucket and now - bucket[0] >= RATE_LIMIT_WINDOW_SECONDS:
            bucket.popleft()

        if len(bucket) >= RATE_LIMIT:
            return JSONResponse(
                status_code=429,
                content={"detail": "Rate limit exceeded"},
            )

        bucket.append(now)

    return await call_next(request)


@app.middleware("http")
async def request_context_middleware(request: Request, call_next):
    request_id = request.headers.get("x-request-id")
    if request_id is None or request_id == "":
        request_id = str(uuid.uuid4())

    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["X-Request-ID", "X-Client-Id", "Content-Type"],
)


@app.get("/")
async def root():
    return {
        "status": "ok",
        "service": "Middleware Stack Assignment",
        "ping": "/ping",
    }


@app.get("/ping")
async def ping(request: Request):
    return {
        "email": os.getenv("EMAIL", ""),
        "request_id": request.state.request_id,
    }
