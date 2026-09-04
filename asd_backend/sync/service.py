"""
Privacy-safe metric sync service — M3.4

Reads pending entries from the sync queue, validates them against
the allow-list, and sends them to the therapist server over TLS.

Design properties
-----------------
- Idempotency: each packet carries a unique idempotency key sent as
  X-Idempotency-Key HTTP header so the server can deduplicate on retry.
- Offline-safe: if the network is unavailable, the queue is left as-is
  and the therapy session continues uninterrupted.
- Exponential back-off: failed entries are retried up to max_retries.
- Malformed entries: skipped (not retried) to avoid blocking the queue.
- Privacy gate: allow-list validation runs before every HTTP call.
"""

from __future__ import annotations

import asyncio
import json
import time

import httpx
import structlog

from asd_backend.config import settings
from asd_backend.db.database import get_session_factory
from asd_backend.db.repositories import SyncQueueRepository
from asd_backend.sync.allow_list import validate_sync_payload, SyncPolicyViolation

log = structlog.get_logger(__name__)


class SyncService:
    """
    Background sync service.

    Call ``run_once()`` to drain the queue once (useful for testing).
    Call ``run_forever()`` to start a long-running background loop.
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_token: str | None = None,
        max_retries: int | None = None,
        backoff_factor: float | None = None,
        timeout_s: float | None = None,
    ) -> None:
        self._base_url = (base_url or settings.sync_base_url).rstrip("/")
        self._token = api_token or settings.sync_api_token
        self._max_retries = max_retries if max_retries is not None else settings.sync_max_retries
        self._backoff = backoff_factor if backoff_factor is not None else settings.sync_backoff_factor
        self._timeout = timeout_s if timeout_s is not None else settings.sync_timeout_s

    async def run_once(self) -> int:
        """
        Process all pending queue entries.

        Returns
        -------
        int
            Number of successfully sent packets.
        """
        sent = 0
        async with get_session_factory()() as db:
            repo = SyncQueueRepository(db)
            pending = await repo.pending()

            if not pending:
                log.debug("sync.nothing_pending")
                return 0

            log.info("sync.processing", count=len(pending))

            async with httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": f"Bearer {self._token}",
                    "Content-Type": "application/json",
                },
                timeout=self._timeout,
                verify=True,   # enforce TLS certificate validation
            ) as client:
                for entry in pending:
                    entry_id = entry.entry_id
                    try:
                        payload = json.loads(entry.payload_json)
                    except json.JSONDecodeError:
                        log.error("sync.malformed_json", entry_id=entry_id)
                        await repo.skip_malformed(entry_id)
                        await db.commit()
                        continue

                    # Privacy gate: re-validate before every send
                    try:
                        validate_sync_payload(payload)
                    except SyncPolicyViolation as exc:
                        log.error("sync.policy_violation_at_send", entry_id=entry_id, error=str(exc))
                        await repo.skip_malformed(entry_id)
                        await db.commit()
                        continue

                    # Send with idempotency key
                    try:
                        response = await client.post(
                            "/therapist/ingest",
                            json=payload,
                            headers={"X-Idempotency-Key": entry.idempotency_key},
                        )
                        response.raise_for_status()
                        await repo.mark_sent(entry_id)
                        await db.commit()
                        sent += 1
                        log.info("sync.sent", entry_id=entry_id)

                    except httpx.RequestError:
                        # Network unavailable — leave pending, do not fail
                        log.warning("sync.offline", entry_id=entry_id)
                        break  # no point trying more entries

                    except httpx.HTTPStatusError as exc:
                        if exc.response.status_code == 409:
                            # Server already has this idempotency key → mark sent
                            await repo.mark_sent(entry_id)
                            await db.commit()
                            log.info("sync.duplicate_skipped", entry_id=entry_id)
                        else:
                            log.warning(
                                "sync.http_error",
                                entry_id=entry_id,
                                status=exc.response.status_code,
                            )
                            await repo.mark_failed(entry_id, self._max_retries)
                            await db.commit()

                    except Exception as exc:
                        log.error("sync.unexpected_error", entry_id=entry_id, error=str(exc))
                        await repo.mark_failed(entry_id, self._max_retries)
                        await db.commit()

        return sent

    async def run_forever(self, interval_s: float = 60.0) -> None:
        """
        Continuously drain the sync queue at regular intervals.
        Designed to run as a background asyncio task.
        """
        log.info("sync.loop_started", interval_s=interval_s)
        while True:
            try:
                await self.run_once()
            except Exception as exc:
                log.error("sync.loop_error", error=str(exc))
            await asyncio.sleep(interval_s)
