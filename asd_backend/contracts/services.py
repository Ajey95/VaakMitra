"""Structural interfaces implemented by Members 1 and 2."""

from typing import Protocol, runtime_checkable

from .schemas import AlignmentResult, ScoringResult


@runtime_checkable
class AlignmentService(Protocol):
    async def process(
        self, audio_bytes: bytes, target_word: str, exercise_id: str
    ) -> AlignmentResult: ...


@runtime_checkable
class ScoringService(Protocol):
    async def score(
        self,
        audio_bytes: bytes,
        phoneme_alignment: list[dict],
        expected_phonemes: list[str],
        attempt_id: str,
    ) -> ScoringResult: ...
