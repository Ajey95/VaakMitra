"""Authenticated, allow-listed Tamil story narration audio."""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response

from ..services.story_voice import (
    STORY_VOICE_LINES,
    StoryVoiceUnavailable,
    story_voice_service,
)
from ..utils.jwt_handler import get_current_user
from ..utils.rate_limit import RateLimiter


router = APIRouter(prefix="/api/story-voice", tags=["story-voice"])
voice_rate_limit = RateLimiter(times=60, seconds=60)


@router.get("/{line_id}", dependencies=[Depends(voice_rate_limit)])
async def get_story_voice(
    line_id: str,
    _current_user: dict = Depends(get_current_user),
):
    if line_id not in STORY_VOICE_LINES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="story_line_not_found")
    try:
        audio = await story_voice_service.get_audio(line_id)
    except StoryVoiceUnavailable:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="story_voice_unavailable",
        ) from None
    return Response(
        content=audio,
        media_type="audio/mpeg",
        headers={"Cache-Control": "private, max-age=3600"},
    )
