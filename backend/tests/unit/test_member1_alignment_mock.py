from __future__ import annotations

import pytest
from modeling.team_mocks.member1_alignment import build_mock_alignment


def test_mock_alignment_partitions_every_frame_without_overlap() -> None:
    envelope = build_mock_alignment(("a", "m", "a\u02d0"), 8, 20.0, confidence=0.9)

    assert envelope.alignment.status == "valid"
    assert [(item.start_frame, item.end_frame) for item in envelope.alignment.phonemes] == [
        (0, 3),
        (3, 6),
        (6, 8),
    ]
    assert [(item.start_ms, item.end_ms) for item in envelope.alignment.phonemes] == [
        (0.0, 60.0),
        (60.0, 120.0),
        (120.0, 160.0),
    ]
    assert envelope.evidence_scope == "mock_dependency_integration"
    assert envelope.production_eligible is False
    assert envelope.clinical_validity is False


def test_mock_alignment_returns_neutral_invalid_when_frames_are_insufficient() -> None:
    envelope = build_mock_alignment(("a", "m", "a\u02d0"), 2, 20.0, confidence=0.9)

    assert envelope.alignment.status == "invalid"
    assert envelope.alignment.confidence == 0.0
    assert envelope.alignment.phonemes == ()
    assert envelope.alignment.reason == "mock_insufficient_frames"


@pytest.mark.parametrize(
    ("phonemes", "frame_count", "frame_shift_ms", "confidence", "message"),
    [
        ((), 4, 20.0, 0.9, "expected_phonemes"),
        (("a",), 0, 20.0, 0.9, "frame_count"),
        (("a",), 4, 0.0, 0.9, "frame_shift_ms"),
        (("a",), 4, 20.0, 1.1, "confidence"),
    ],
)
def test_mock_alignment_rejects_invalid_configuration(
    phonemes: tuple[str, ...],
    frame_count: int,
    frame_shift_ms: float,
    confidence: float,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_mock_alignment(
            phonemes,
            frame_count,
            frame_shift_ms,
            confidence=confidence,
        )
