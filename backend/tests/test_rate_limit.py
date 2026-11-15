"""Unit tests for the in-memory rate limiter."""
import asyncio
import pytest
from fastapi import HTTPException

from app.utils.rate_limit import RateLimiter


class _FakeClient:
    def __init__(self, host):
        self.host = host


class _FakeURL:
    def __init__(self, path):
        self.path = path


class _FakeRequest:
    """Minimal stand-in for starlette Request (only needs client + url.path)."""
    def __init__(self, host="1.2.3.4", path="/api/test"):
        self.client = _FakeClient(host)
        self.url = _FakeURL(path)


def _run(coro):
    # Python 3.12 no longer creates an implicit loop for synchronous callers.
    return asyncio.run(coro)


def setup_function():
    # isolate the shared class-level store between tests
    RateLimiter._hits.clear()


def test_allows_requests_under_limit():
    limiter = RateLimiter(times=3, seconds=60)
    req = _FakeRequest(host="10.0.0.1", path="/login")
    for _ in range(3):
        _run(limiter(req))  # should not raise


def test_blocks_requests_over_limit():
    limiter = RateLimiter(times=3, seconds=60)
    req = _FakeRequest(host="10.0.0.2", path="/login")
    for _ in range(3):
        _run(limiter(req))
    with pytest.raises(HTTPException) as exc:
        _run(limiter(req))
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


def test_different_ips_are_independent():
    limiter = RateLimiter(times=1, seconds=60)
    a = _FakeRequest(host="10.0.0.3", path="/login")
    b = _FakeRequest(host="10.0.0.4", path="/login")
    _run(limiter(a))
    _run(limiter(b))  # different IP, should not raise
    with pytest.raises(HTTPException):
        _run(limiter(a))


def test_different_paths_are_independent():
    limiter = RateLimiter(times=1, seconds=60)
    a = _FakeRequest(host="10.0.0.5", path="/login")
    b = _FakeRequest(host="10.0.0.5", path="/register")
    _run(limiter(a))
    _run(limiter(b))  # same IP, different path, should not raise
