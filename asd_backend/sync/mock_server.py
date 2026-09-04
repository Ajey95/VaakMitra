"""
Mock therapist server for integration and offline tests.

Runs as an in-process uvicorn server on a free port.
Captures received packets for assertion in tests.
"""

from __future__ import annotations

import asyncio
import threading
from typing import Any

import uvicorn
from fastapi import FastAPI, Header, Request
from fastapi.responses import JSONResponse


class MockTherapistServer:
    """
    Lightweight mock therapist server.

    Usage
    -----
    >>> server = MockTherapistServer()
    >>> server.start()
    >>> # ... run tests ...
    >>> server.stop()
    >>> server.received_packets  # inspect what was sent
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 9099) -> None:
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.received_packets: list[dict] = []
        self._app = self._build_app()
        self._thread: threading.Thread | None = None
        self._server: uvicorn.Server | None = None

    def _build_app(self) -> FastAPI:
        app = FastAPI(title="Mock Therapist Server")
        server_self = self

        @app.post("/therapist/ingest")
        async def ingest(request: Request) -> JSONResponse:
            body = await request.json()
            server_self.received_packets.append(body)
            return JSONResponse({"received_count": 1, "status": "ok"})

        @app.get("/therapist/plan/{plan_id}")
        async def get_plan(plan_id: str) -> JSONResponse:
            return JSONResponse({
                "plan_id": plan_id,
                "therapist_ref": "mock-therapist",
                "policy_version": "0.0.1-dev",
                "plan_version": "1.0.0",
                "exercises": [
                    {
                        "id": "TA_AMMA_01",
                        "target_word": "அம்மா",
                        "target_phonemes": ["a", "m", "m", "a:"],
                        "syllables": ["அம்", "மா"],
                        "difficulty": "easy",
                    },
                    {
                        "id": "TA_APPA_01",
                        "target_word": "அப்பா",
                        "target_phonemes": ["a", "p", "p", "a:"],
                        "syllables": ["அப்", "பா"],
                        "difficulty": "easy",
                    },
                ],
            })

        @app.post("/therapist/plan")
        async def upload_plan(request: Request) -> JSONResponse:
            body = await request.json()
            return JSONResponse(body, status_code=201)

        return app

    def start(self) -> None:
        config = uvicorn.Config(
            self._app,
            host=self.host,
            port=self.port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)

        def _run():
            asyncio.run(self._server.serve())

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()
        # Give the server time to start
        import time
        time.sleep(0.5)

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=3)

    def clear(self) -> None:
        self.received_packets.clear()
