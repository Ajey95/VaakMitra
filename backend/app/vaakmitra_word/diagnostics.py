"""DEC-018/SES-006: process-local adult diagnostics, with no child database writes."""
import ipaddress
import secrets
from time import monotonic
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, ConfigDict

from ..config import settings
from ..utils.rate_limit import RateLimiter
from .assessment import AssessmentContext
from .contracts import AssessmentResult, Decision, ReasonCode
from .calibration import EvidenceCalibrator
from .adult_preview import AdultPreview, adult_development_result, provisional_adult_estimate
from .dev_chunk_coach import build_chunk_coach
from .diagnostic_runtime import diagnostic_runtime
from .inference_runner import inference_runner
from .policy import TherapistConstraints
from .router import bounded_audio
from .router import VOCABULARY_REGISTRY
from .upload_limit import MemoryOnlyWordRoute

router = APIRouter(prefix="/api/dev/word-lab", tags=["local-operator-diagnostics"], route_class=MemoryOnlyWordRoute)
COOKIE = "vaakmitra_local_lab"
_capabilities = {}


def adult_preview_for_result(service, result: AssessmentResult) -> dict:
    """DEC-022: expose only a separate adult estimate after live binding gates."""
    unavailable = {"status": "unavailable", "estimate": None, "reason_code": "preview_gate_unavailable"}
    calibrator = getattr(service, "calibrator", None)
    if (not isinstance(calibrator, EvidenceCalibrator)
            or result.decision is not Decision.UNSCORABLE
            or result.reason_code is not ReasonCode.CALIBRATION_UNAVAILABLE
            or result.quality.vad_mode != "onnx_cpu"
            or not getattr(service, "live_pipeline_ready", False)
            or not getattr(service, "production_vad_ready", False)):
        return unavailable
    preview = provisional_adult_estimate(calibrator, result.evidence, result.quality)
    return {"status": preview.status, "estimate": preview.estimate,
            "reason_code": preview.reason_code,
            "calibration_version": calibrator.artifact.version}


def require_local_lab(request: Request):
    if settings.APP_ENV != "development" or not settings.VAAKMITRA_DIAGNOSTICS_ENABLED:
        raise HTTPException(404, detail="not_found")
    try:
        local = request.client is not None and ipaddress.ip_address(request.client.host).is_loopback
    except ValueError:
        local = False
    if not local:
        raise HTTPException(403, detail="loopback_required")
    if request.method != "GET":
        origin = request.headers.get("origin", "")
        if origin not in settings.cors_origins or request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, detail="local_origin_required")


def require_operator(request: Request, _local=Depends(require_local_lab)):
    token = request.cookies.get(COOKIE, "")
    if _capabilities.get(token, 0) <= monotonic():
        raise HTTPException(401, detail="local_operator_session_required")
    return token


class OpenLab(BaseModel):
    model_config = ConfigDict(extra="forbid")
    adult_test_only: Literal[True]


@router.post("/open", dependencies=[Depends(require_local_lab), Depends(RateLimiter(10, 60))])
async def open_lab(payload: OpenLab, response: Response):
    """Explicit local operator action grants only the diagnostic namespace."""
    for key, expires in tuple(_capabilities.items()):
        if expires <= monotonic():
            _capabilities.pop(key, None)
    if len(_capabilities) >= 32:
        raise HTTPException(429, detail="too_many_local_operator_sessions")
    token = secrets.token_urlsafe(32)
    _capabilities[token] = monotonic() + 1800
    response.set_cookie(COOKIE, token, httponly=True, samesite="strict", max_age=1800, path="/api/dev/word-lab")
    return {"status": "open", "scope": "local_adult_diagnostics", "expires_in_seconds": 1800}


@router.post("/close")
async def close_lab(response: Response, token=Depends(require_operator)):
    _capabilities.pop(token, None)
    response.delete_cookie(COOKIE, path="/api/dev/word-lab")
    return {"status": "closed"}


@router.get("/status")
async def diagnostic_status(_operator=Depends(require_operator)):
    return diagnostic_runtime.status()


@router.post("/session-checks", dependencies=[Depends(RateLimiter(5, 60))])
async def diagnostic_session_checks(_operator=Depends(require_operator)):
    from ..database import db_manager, ensure_database
    from .diagnostic_scenarios import run_scenarios
    await ensure_database()
    return await run_scenarios(db_manager.client, VOCABULARY_REGISTRY)


@router.post("/assess", dependencies=[Depends(RateLimiter(20, 60))])
async def diagnostic_assessment(audio: UploadFile = File(...), word_id: str = Form(..., max_length=64),
                                 _operator=Depends(require_operator)):
    if diagnostic_runtime.service is None:
        raise HTTPException(503, detail="diagnostic_model_not_ready")
    target = diagnostic_runtime.words.get(word_id)
    if target is None:
        raise HTTPException(422, detail="word_not_in_engineering_artifacts")
    data = await bounded_audio(audio)
    context = AssessmentContext(session_id=f"DIAG-{uuid4().hex}", attempt_id=f"ATT-{uuid4().hex}",
        word_id=word_id, target_word=target, attempt_count=0,
        therapist_constraints=TherapistConstraints(allowed_actions=("break", "safe_end"), next_exercise_id=""))
    try:
        result = await inference_runner.run(diagnostic_runtime.service.assess, data, context, timeout=60)
    except HTTPException:
        raise
    except Exception:
        result = AssessmentResult.unscorable(ReasonCode.MODEL_INFERENCE_FAILED,
            session_id=context.session_id, attempt_id=context.attempt_id, word_id=word_id, target_word=target)
    # This is an evidence inspection path. It cannot emit approved scoring decisions.
    if result.decision is not Decision.UNSCORABLE:
        result = AssessmentResult.unscorable(ReasonCode.CALIBRATION_UNAVAILABLE,
            session_id=context.session_id, attempt_id=context.attempt_id, word_id=word_id, target_word=target,
            quality=result.quality, evidence=result.evidence)
    preview = adult_preview_for_result(diagnostic_runtime.service, result)
    development_result = adult_development_result(AdultPreview(
        preview["status"], preview["estimate"], preview["reason_code"]))
    return {"evidence_scope": "real_adult_engineering", "scoring_ready": False,
            "result": result.model_dump(mode="json"),
            "adult_preview": preview,
            "development_result": development_result,
            "chunk_coach": build_chunk_coach(
                target, result.observed_candidates[0].word if result.observed_candidates else None,
                capture_valid=result.quality.valid and result.quality.speech_detected),
            "persisted": False}
