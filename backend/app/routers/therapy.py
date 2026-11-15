"""Therapy lessons router."""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Dict
from ..utils.jwt_handler import get_current_user
from ..vaakmitra_word.curriculum import build_lesson_catalog
from ..vaakmitra_word.router import VOCABULARY_REGISTRY


router = APIRouter(prefix="/api/therapy", tags=["therapy"])


AVATAR_COACH_DEFAULTS = {
    "enabled": True,
    "engine": "livetalk-unity",
    "renderer": "web-fallback",
    "name": "Mitra",
    "voice": "en-IN",
    "package_path": "LiveTalk-Unity",
}


def _with_avatar_coach(lesson: Dict) -> Dict:
    """Attach the child-friendly LiveTalk coach contract to a lesson."""
    english = lesson.get("english", "this sound")
    return {
        **lesson,
        "avatar_coach": {
            **AVATAR_COACH_DEFAULTS,
            "intro": f"Let's learn {english} together!",
            "tip": lesson.get("tip", "Take your time and try again."),
            "success": "Great job! You did it!",
            "retry": "Nice try. Let's practice once more.",
        },
    }


LESSONS = build_lesson_catalog(VOCABULARY_REGISTRY)


@router.get("/lessons", response_model=List[Dict])
async def get_lessons(current_user: dict = Depends(get_current_user)):
    """Get all available lessons."""
    return [_with_avatar_coach(lesson) for lesson in LESSONS]


@router.get("/lessons/{lesson_id}", response_model=Dict)
async def get_lesson(lesson_id: int, current_user: dict = Depends(get_current_user)):
    """Get specific lesson by ID."""
    for lesson in LESSONS:
        if lesson["id"] == lesson_id:
            return _with_avatar_coach(lesson)
    
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Lesson with ID {lesson_id} not found"
    )
