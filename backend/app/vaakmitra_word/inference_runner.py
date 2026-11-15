"""SES-003: a timed-out HTTP request must not release the actual model worker."""
import asyncio
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from fastapi import HTTPException


class InferenceRunner:
    def __init__(self):
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="word-inference")
        self._occupied = Lock()

    @property
    def busy(self):
        return self._occupied.locked()

    async def run(self, function, *args, timeout: float):
        if not self._occupied.acquire(blocking=False):
            raise HTTPException(503, detail="model_busy", headers={"Retry-After": "2"})
        try:
            future = self._executor.submit(function, *args)
        except BaseException:
            self._occupied.release()
            raise
        future.add_done_callback(lambda _done: self._occupied.release())
        # Shield prevents cancellation of queued/running work from freeing capacity.
        return await asyncio.wait_for(asyncio.shield(asyncio.wrap_future(future)), timeout)

    def close(self):
        self._executor.shutdown(wait=False, cancel_futures=True)


inference_runner = InferenceRunner()
