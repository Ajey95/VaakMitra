"""SES-003: timeout cannot queue overlapping work on the same acoustic model."""
import asyncio
from threading import Event
import pytest
from fastapi import HTTPException
from app.vaakmitra_word.inference_runner import InferenceRunner


def test_ses003_timeout_holds_worker_until_actual_completion():
    runner = InferenceRunner()
    release = Event()
    async def scenario():
        try:
            with pytest.raises(TimeoutError):
                await runner.run(lambda: release.wait(3), timeout=0.02)
            assert runner.busy
            with pytest.raises(HTTPException) as conflict:
                await runner.run(lambda: 1, timeout=1)
            assert conflict.value.status_code == 503
        finally:
            release.set()
        for _ in range(100):
            if not runner.busy:
                break
            await asyncio.sleep(0.01)
        assert await runner.run(lambda: 42, timeout=1) == 42
    try:
        asyncio.run(scenario())
    finally:
        runner.close()
