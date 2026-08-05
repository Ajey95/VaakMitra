"""Deterministic Member 1 alignment mock for contract integration tests only."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from vaakmitra.contracts.alignment import AlignedPhoneme, AlignmentResult


@dataclass(frozen=True, slots=True)
class MockAlignmentEnvelope:
    """Alignment plus evidence labels that prevent production interpretation."""

    dependency: str
    implementation: str
    evidence_scope: str
    production_eligible: bool
    clinical_validity: bool
    alignment: AlignmentResult

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["alignment"] = self.alignment.model_dump(mode="json")
        return payload


def _envelope(alignment: AlignmentResult) -> MockAlignmentEnvelope:
    return MockAlignmentEnvelope(
        dependency="member1",
        implementation="deterministic_mock",
        evidence_scope="mock_dependency_integration",
        production_eligible=False,
        clinical_validity=False,
        alignment=alignment,
    )


def build_mock_alignment(
    expected_phonemes: tuple[str, ...],
    frame_count: int,
    frame_shift_ms: float,
    *,
    confidence: float,
) -> MockAlignmentEnvelope:
    """Divide frames deterministically without claiming real forced alignment."""

    if not expected_phonemes or any(not phoneme.strip() for phoneme in expected_phonemes):
        raise ValueError("expected_phonemes must contain non-empty units")
    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    if frame_shift_ms <= 0:
        raise ValueError("frame_shift_ms must be positive")
    if not 0 <= confidence <= 1:
        raise ValueError("confidence must be between zero and one")
    if frame_count < len(expected_phonemes):
        return _envelope(
            AlignmentResult(
                status="invalid",
                confidence=0.0,
                reason="mock_insufficient_frames",
            )
        )

    base_width, extra_frames = divmod(frame_count, len(expected_phonemes))
    start_frame = 0
    aligned: list[AlignedPhoneme] = []
    for index, phoneme in enumerate(expected_phonemes):
        width = base_width + (1 if index < extra_frames else 0)
        end_frame = start_frame + width
        aligned.append(
            AlignedPhoneme(
                phoneme=phoneme,
                start_frame=start_frame,
                end_frame=end_frame,
                start_ms=start_frame * frame_shift_ms,
                end_ms=end_frame * frame_shift_ms,
                confidence=confidence,
            )
        )
        start_frame = end_frame

    return _envelope(
        AlignmentResult(
            status="valid",
            confidence=confidence,
            phonemes=tuple(aligned),
        )
    )
