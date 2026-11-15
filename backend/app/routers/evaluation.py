"""SES-001: retire unbound legacy scoring in favor of plan-backed assessments."""
from fastapi import APIRouter, Depends, HTTPException

from ..utils.jwt_handler import get_current_user
from ..utils.rate_limit import RateLimiter


router = APIRouter(prefix="/api/evaluate", tags=["evaluation"])
speech_rate_limit = RateLimiter(times=30, seconds=60)


@router.post("/speech", dependencies=[Depends(speech_rate_limit)])
async def evaluate_speech(
    current_user: dict = Depends(get_current_user),
):
    """SES-001: unbound legacy scoring cannot bypass canonical session limits."""
    raise HTTPException(409, detail="word_session_required_use_canonical_endpoint")
