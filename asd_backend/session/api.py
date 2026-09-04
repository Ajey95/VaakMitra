"""
FastAPI router for session and attempt endpoints — Unity integration API.

All endpoints are consumed by the Unity C# HTTP client via localhost.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from asd_backend.session.orchestrator import (
    Member1ServiceInterface,
    Member2ServiceInterface,
    SessionOrchestrator,
)
from asd_backend.session.schemas import (
    AttemptResult,
    AttemptSubmitRequest,
    CancelAttemptRequest,
    HealthResponse,
    SessionEndRequest,
    SessionEndResponse,
    SessionStartRequest,
    SessionStartResponse,
)
from asd_backend import __version__
from asd_backend.adaptive.policy import TherapistPolicy

router = APIRouter(prefix="/api/v1", tags=["session"])

# ---------------------------------------------------------------------------
# Dependency — shared orchestrator singleton
# ---------------------------------------------------------------------------

_orchestrator: SessionOrchestrator | None = None


def get_orchestrator() -> SessionOrchestrator:
    if _orchestrator is None:
        raise RuntimeError("Orchestrator not initialised. Call init_orchestrator() on startup.")
    return _orchestrator


def init_orchestrator(
    policy: TherapistPolicy | None = None,
    member1: Member1ServiceInterface | None = None,
    member2: Member2ServiceInterface | None = None,
) -> SessionOrchestrator:
    global _orchestrator
    _orchestrator = SessionOrchestrator(
        policy=policy, member1=member1, member2=member2
    )
    return _orchestrator


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/health", response_model=HealthResponse, summary="Backend health check")
async def health_check(
    orch: SessionOrchestrator = Depends(get_orchestrator),
) -> HealthResponse:
    """
    Returns backend version and active configuration versions.
    Unity should call this on startup to confirm the backend is reachable.
    """
    return HealthResponse(
        status="ok",
        version=__version__,
        policy_version=orch._policy.policy_version,
        model_version=orch.model_version,
        dict_version=orch.dictionary_version,
        db_connected=True,
    )


@router.post(
    "/session/start",
    response_model=SessionStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a new therapy session",
)
async def start_session(
    request: SessionStartRequest,
    orch: SessionOrchestrator = Depends(get_orchestrator),
) -> SessionStartResponse:
    """
    Initialise a session for a child. Returns the session ID and first exercise.
    Unity must store the session_id and pass it in every subsequent request.
    """
    try:
        return await orch.start_session(request)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/session/attempt",
    response_model=AttemptResult,
    summary="Submit a child pronunciation attempt",
)
async def submit_attempt(
    request: AttemptSubmitRequest,
    orch: SessionOrchestrator = Depends(get_orchestrator),
) -> AttemptResult:
    """
    Submit a base64-encoded 16 kHz mono PCM audio buffer for one attempt.

    The backend will:
    1. Decode audio into memory
    2. Run Member 1 VAD + forced alignment
    3. Run Member 2 acoustic model + GOP scoring
    4. Apply adaptive decision engine
    5. Persist structured metrics to local DB
    6. Return Unity-facing result

    Audio is processed in memory and never persisted.
    """
    try:
        return await orch.submit_attempt(
            session_id=request.session_id,
            exercise_id=request.exercise_id,
            target_word=request.target_word,
            audio_b64=request.audio_b64,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post(
    "/session/cancel",
    status_code=status.HTTP_200_OK,
    summary="Cancel an in-flight attempt",
)
async def cancel_attempt(
    request: CancelAttemptRequest,
    orch: SessionOrchestrator = Depends(get_orchestrator),
) -> dict:
    """
    Signal cancellation of any in-flight attempt for this session.
    The backend will clean up audio and intermediate data.
    Unity should call this when the child dismisses the UI or times out.
    """
    await orch.cancel_attempt(request)
    return {"status": "ok"}


@router.post(
    "/session/end",
    response_model=SessionEndResponse,
    summary="End a therapy session",
)
async def end_session(
    request: SessionEndRequest,
    orch: SessionOrchestrator = Depends(get_orchestrator),
) -> SessionEndResponse:
    """
    Finalise the session. Aggregates session statistics and optionally
    triggers background metric sync if consent is granted and network available.
    """
    try:
        return await orch.end_session(request.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
