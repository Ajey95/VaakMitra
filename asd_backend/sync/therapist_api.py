"""
Therapist-facing FastAPI router — M3.4

Endpoints for the therapist server (not Unity):
- POST /therapist/ingest   — receive sync packets from devices
- GET  /therapist/report   — aggregate session report per child
- GET  /therapist/plan     — download exercise plan + policy
- POST /therapist/plan     — upload new exercise plan

Privacy: these endpoints only handle pseudonymous IDs and
aggregate metrics. No audio, embeddings, or raw GOP scores.
"""

from __future__ import annotations

import hmac
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from asd_backend.config import settings
from asd_backend.db.database import get_session
from asd_backend.db.repositories import (
    AuditRepository,
    ExercisePlanRepository,
    SessionRepository,
    SyncQueueRepository,
)
from asd_backend.sync.allow_list import validate_sync_payload, SyncPolicyViolation
from asd_backend.sync.schemas import (
    ExercisePlanDownload,
    SyncAck,
    SyncPacket,
    TherapistReport,
    SessionSummary,
)

router = APIRouter(prefix="/therapist", tags=["therapist"])


# ---------------------------------------------------------------------------
# Auth helper — simple bearer token
# ---------------------------------------------------------------------------

def _require_token(authorization: str = Header(...)) -> None:
    """Validate the therapist API bearer token."""
    scheme, _, token = authorization.partition(" ")
    token_matches = bool(token) and hmac.compare_digest(token, settings.sync_api_token)
    if scheme.lower() != "bearer" or not token_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing therapist API token.",
        )


# ---------------------------------------------------------------------------
# POST /therapist/ingest — receive sync packets
# ---------------------------------------------------------------------------

@router.post(
    "/ingest",
    response_model=SyncAck,
    status_code=status.HTTP_200_OK,
    summary="Receive privacy-safe metric packet from device",
    dependencies=[Depends(_require_token)],
)
async def ingest_packet(
    packet: SyncPacket,
    x_idempotency_key: str = Header(..., alias="X-Idempotency-Key"),
    db: AsyncSession = Depends(get_session),
) -> SyncAck:
    """
    Accept a privacy-safe metric packet from a device.
    Re-validates the packet against the allow-list server-side.
    Idempotency key prevents duplicate processing.
    """
    payload = packet.model_dump()

    # Server-side privacy re-validation
    try:
        validate_sync_payload(payload)
    except SyncPolicyViolation as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Sync policy violation: {exc}",
        ) from exc

    audit = AuditRepository(db)
    if await audit.has_sync_idempotency_key(x_idempotency_key):
        return SyncAck(
            received_count=0,
            status="ok",
            message="Duplicate packet already processed",
        )

    # Persist an append-only receipt; no voice-derived data is stored.
    await audit.log(
        event_type="sync_received",
        pseudonym_id=packet.pseudonym_id,
        session_id=packet.session_id,
        detail={
            "attempt_id": packet.attempt_id,
            "overall_pass": packet.overall_pass,
            "idempotency_key": x_idempotency_key,
        },
    )
    await db.commit()

    return SyncAck(received_count=1, status="ok")


# ---------------------------------------------------------------------------
# GET /therapist/report — session report for one child
# ---------------------------------------------------------------------------

@router.get(
    "/report/{pseudonym_id}",
    response_model=TherapistReport,
    summary="Aggregate session report for a child",
    dependencies=[Depends(_require_token)],
)
async def get_report(
    pseudonym_id: str,
    db: AsyncSession = Depends(get_session),
) -> TherapistReport:
    """
    Returns aggregate session summaries for a child.
    Only pseudonymous IDs and pass/fail aggregates are included.
    No audio, raw scores, or biometrics.
    """
    sess_repo = SessionRepository(db)
    # Get all sessions for this pseudonym
    from sqlalchemy import select
    from asd_backend.db.models import Session as DBSession, Attempt
    result = await db.execute(
        select(DBSession).where(DBSession.pseudonym_id == pseudonym_id)
    )
    sessions = result.scalars().all()

    summaries = []
    for s in sessions:
        # Calculate pass rate from attempts
        att_result = await db.execute(
            select(Attempt).where(Attempt.session_id == s.session_id)
        )
        attempts = att_result.scalars().all()
        pass_count = sum(1 for a in attempts if a.decision == "pass")
        total = len(attempts)
        pass_rate = pass_count / total if total > 0 else 0.0

        summaries.append(SessionSummary(
            session_id=s.session_id,
            started_at=s.started_at.isoformat(),
            ended_at=s.ended_at.isoformat() if s.ended_at else None,
            total_attempts=total,
            pass_rate=round(pass_rate, 3),
        ))

    return TherapistReport(
        pseudonym_id=pseudonym_id,
        sessions=summaries,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


# ---------------------------------------------------------------------------
# GET /therapist/plan/{plan_id} — download exercise plan
# ---------------------------------------------------------------------------

@router.get(
    "/plan/{plan_id}",
    response_model=ExercisePlanDownload,
    summary="Download exercise plan",
    dependencies=[Depends(_require_token)],
)
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_session),
) -> ExercisePlanDownload:
    plan_repo = ExercisePlanRepository(db)
    plan = await plan_repo.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail=f"Plan {plan_id!r} not found")

    exercises = json.loads(plan.exercises_json)
    return ExercisePlanDownload(
        plan_id=plan.plan_id,
        therapist_ref=plan.therapist_ref,
        policy_version=plan.policy_version,
        plan_version=plan.plan_version,
        exercises=exercises,
    )


# ---------------------------------------------------------------------------
# POST /therapist/plan — upload new exercise plan
# ---------------------------------------------------------------------------

@router.post(
    "/plan",
    response_model=ExercisePlanDownload,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a new exercise plan",
    dependencies=[Depends(_require_token)],
)
async def upload_plan(
    plan: ExercisePlanDownload,
    db: AsyncSession = Depends(get_session),
) -> ExercisePlanDownload:
    plan_repo = ExercisePlanRepository(db)
    db_plan = await plan_repo.create(
        therapist_ref=plan.therapist_ref,
        policy_version=plan.policy_version,
        plan_version=plan.plan_version,
        exercises=[e.model_dump() for e in plan.exercises],
    )
    await db.commit()
    plan.plan_id = db_plan.plan_id
    return plan
