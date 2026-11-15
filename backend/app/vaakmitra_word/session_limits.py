"""SES-001/002: versioned, bounded therapist-plan limits."""
from pydantic import BaseModel, ConfigDict, Field


class SessionLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    max_retries: int = Field(default=2, ge=0, le=3)
    max_session_seconds: int = Field(default=600, ge=60, le=900)
    max_total_attempts: int = Field(default=40, ge=1, le=60)
    break_seconds: int = Field(default=30, ge=15, le=300)
