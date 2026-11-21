import re
import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

JOB_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{8,64}$")


def validate_job_id(job_id: str) -> str:
    """Validates job_id format to prevent path traversal or injection."""
    if not JOB_ID_PATTERN.match(job_id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid job ID format.",
        )
    return job_id


class InMemoryRateLimiter:
    """Sliding-window per-IP rate limiter for single-instance protection.

    Note: For multi-worker or multi-instance production deployments, replace
    with a Redis-backed rate limiter (e.g., slowapi + Redis).
    """

    def __init__(self) -> None:
        self._hits: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        if limit <= 0:
            return
        now = time.monotonic()
        cutoff = now - window_seconds
        with self._lock:
            bucket = self._hits[key]
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit exceeded. Please wait a moment before creating another video.",
                )
            bucket.append(now)


rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(request: Request) -> None:
    settings = get_settings()
    client_ip = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    rate_limiter.check(
        key=client_ip,
        limit=settings.RATE_LIMIT_REQUESTS_PER_MINUTE,
        window_seconds=60,
    )
