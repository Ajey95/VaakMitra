"""Lightweight in-memory rate limiting.

A dependency-free sliding-window limiter usable as a FastAPI dependency:

    @router.post("/login", dependencies=[Depends(RateLimiter(times=10, seconds=60))])

Note: state is per-process. For a multi-worker / multi-instance deployment,
swap the backing store for Redis. For this project's single-instance scope the
in-memory window is sufficient and adds no new dependencies.
"""
from collections import defaultdict, deque
from time import monotonic
from typing import Deque, Dict

from fastapi import HTTPException, Request, status


class RateLimiter:
    """Sliding-window rate limiter keyed by client IP + route path."""

    # class-level store shared across instances: key -> deque[timestamps]
    _hits: Dict[str, Deque[float]] = defaultdict(deque)

    def __init__(self, times: int, seconds: int):
        self.times = times
        self.seconds = seconds

    async def __call__(self, request: Request) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"
        now = monotonic()
        window_start = now - self.seconds

        hits = self._hits[key]
        # drop timestamps outside the window
        while hits and hits[0] < window_start:
            hits.popleft()

        if len(hits) >= self.times:
            retry_after = int(self.seconds - (now - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please slow down and try again shortly.",
                headers={"Retry-After": str(retry_after)},
            )

        hits.append(now)
