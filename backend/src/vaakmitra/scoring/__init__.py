"""GOP, confidence, and syllable-level pronunciation scoring."""

from vaakmitra.scoring.confidence import ScoringConfig, classify_score, combine_confidence
from vaakmitra.scoring.gop import (
    UnscorableEvidenceError,
    phoneme_gop,
    score_aligned_phonemes,
)
from vaakmitra.scoring.syllables import aggregate_syllables

__all__ = [
    "ScoringConfig",
    "UnscorableEvidenceError",
    "aggregate_syllables",
    "classify_score",
    "combine_confidence",
    "phoneme_gop",
    "score_aligned_phonemes",
]

