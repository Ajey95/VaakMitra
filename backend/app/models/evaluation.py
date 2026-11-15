"""Evaluation models."""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class EvaluationResult(BaseModel):
    """Evaluation result schema."""
    user_id: str
    lesson_id: int
    phoneme: str
    lesson_type: str
    accuracy: float = Field(ge=0, le=100)
    phoneme_match: bool
    mfcc_score: float
    gop_score: Optional[float] = None
    airflow_score: float
    stars_earned: int = Field(ge=0, le=3)
    feedback: str
    duration_ms: int


class EvaluationInDB(EvaluationResult):
    """Evaluation in database."""
    id: str = Field(alias="_id")
    created_at: datetime
    
    class Config:
        populate_by_name = True


class SpeechEvaluationRequest(BaseModel):
    """Speech evaluation request."""
    target_phoneme: str
    lesson_id: int


class FaceAnalysisResult(BaseModel):
    """Face analysis result."""
    face_detected: bool
    mouth_open_ratio: float = 0.0
    mouth_is_open: bool = False
    stress_level: float = 0.0
    emotion: str = "neutral"
