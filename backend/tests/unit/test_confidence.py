from __future__ import annotations

import pytest
from pydantic import ValidationError

from vaakmitra.scoring.confidence import (
    ScoringConfig,
    acoustic_separation,
    classify_score,
    combine_confidence,
)


def test_config_requires_confidence_weights_to_sum_to_one() -> None:
    with pytest.raises(ValidationError, match="sum to one"):
        ScoringConfig(acoustic_weight=0.8, alignment_weight=0.4)


def test_config_requires_monotonic_score_thresholds() -> None:
    with pytest.raises(ValidationError, match="coach_score"):
        ScoringConfig(coach_score=0.9, pass_score=0.8)


def test_acoustic_separation_is_high_for_decisive_evidence() -> None:
    assert acoustic_separation(0.9) == pytest.approx(0.8)
    assert acoustic_separation(0.1) == pytest.approx(0.8)
    assert acoustic_separation(0.5) == pytest.approx(0.0)


def test_confidence_combines_acoustic_and_alignment_evidence() -> None:
    config = ScoringConfig(acoustic_weight=0.6, alignment_weight=0.4)

    confidence = combine_confidence(gop=0.9, alignment_confidence=0.75, config=config)

    assert confidence == pytest.approx(0.6 * 0.8 + 0.4 * 0.75)


@pytest.mark.parametrize(
    ("gop", "confidence", "expected"),
    [
        (0.9, 0.9, "pass"),
        (0.9, 0.6, "coach"),
        (0.6, 0.8, "coach"),
        (0.3, 0.8, "retry"),
        (0.9, 0.3, "unscorable"),
    ],
)
def test_categories_respect_score_and_confidence_gates(
    gop: float,
    confidence: float,
    expected: str,
) -> None:
    assert classify_score(gop, confidence, ScoringConfig()) == expected

