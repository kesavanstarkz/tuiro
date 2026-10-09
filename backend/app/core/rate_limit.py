"""In-memory rate limiter for sensitive authentication endpoints."""
from __future__ import annotations

import time
from collections import defaultdict
from fastapi import HTTPException, Request, status

# In-memory attempt store: key -> list of timestamp floats
_ATTEMPTS: dict[str, list[float]] = defaultdict(list)


def check_rate_limit(key: str, max_attempts: int = 10, window_seconds: int = 60) -> None:
    """Enforces rate limiting. Raises HTTP 429 if limit is exceeded."""
    now = time.time()
    cutoff = now - window_seconds
    attempts = [t for t in _ATTEMPTS[key] if t > cutoff]
    if len(attempts) >= max_attempts:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many requests. Please try again in {window_seconds} seconds.",
        )
    attempts.append(now)
    _ATTEMPTS[key] = attempts


def reset_rate_limits() -> None:
    """Helper for testing to clear rate limiter state."""
    _ATTEMPTS.clear()
