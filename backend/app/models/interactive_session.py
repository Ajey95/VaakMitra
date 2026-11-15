"""Strict, aggregate-only models for interactive child practice sessions."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssistanceCounts(BaseModel):
    """Counts of observable support given; contains no child media or labels."""

    model_config = ConfigDict(extra="forbid")

    independent: int = Field(default=0, ge=0, le=100)
    verbal_prompt: int = Field(default=0, ge=0, le=100)
    visual_prompt: int = Field(default=0, ge=0, le=100)
    modelled: int = Field(default=0, ge=0, le=100)
    skipped: int = Field(default=0, ge=0, le=100)

    @property
    def total(self) -> int:
        return sum(self.model_dump().values())


class InteractiveSessionCreate(BaseModel):
    """Privacy-minimal payload accepted from an authenticated child session."""

    model_config = ConfigDict(extra="forbid")

    activity_id: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9-]*$")
    activity_type: Literal["arcade", "quest", "mouth_mirror", "pippin", "talk_together"]
    started_at: datetime
    completed_at: datetime
    communication_turns: int = Field(ge=0, le=100)
    successful_turns: int = Field(ge=0, le=100)
    attempts: int = Field(ge=0, le=300)
    assistance_counts: AssistanceCounts = Field(default_factory=AssistanceCounts)
    duration_ms: int = Field(ge=0, le=3_600_000)
    effort_points: int = Field(default=0, ge=0, le=10_000)
    game_score_id: Optional[str] = Field(default=None, min_length=1, max_length=100)

    @model_validator(mode="after")
    def validate_session_consistency(self):
        if self.completed_at < self.started_at:
            raise ValueError("completed_at must not precede started_at")
        if self.successful_turns > self.communication_turns:
            raise ValueError("successful_turns cannot exceed communication_turns")
        if self.assistance_counts.total > self.communication_turns:
            raise ValueError("assistance counts cannot exceed communication_turns")
        return self
