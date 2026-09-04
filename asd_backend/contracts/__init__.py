"""Stable, versioned boundaries between backend team modules.

Members 1 and 2 should depend on this package only, never on Member 3's
orchestrator internals.  Contract additions require a new contract version;
existing fields must remain backwards compatible within version 1.x.
"""

from .schemas import (
    AlignmentResult,
    CaptureStatus,
    PhonemeAlignment,
    PhonemeScore,
    ScoringResult,
    ScoreStatus,
    SyllableScore,
)
from .services import AlignmentService, ScoringService

__all__ = [
    "AlignmentResult",
    "AlignmentService",
    "CaptureStatus",
    "PhonemeAlignment",
    "PhonemeScore",
    "ScoringResult",
    "ScoringService",
    "ScoreStatus",
    "SyllableScore",
]
