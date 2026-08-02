from __future__ import annotations

import pytest

from vaakmitra.contracts.alignment import AlignedPhoneme, SyllableDefinition
from vaakmitra.contracts.scoring import PhonemeScore
from vaakmitra.scoring.confidence import ScoringConfig
from vaakmitra.scoring.syllables import aggregate_syllables


def _aligned(phoneme: str, start: int, end: int, confidence: float = 0.9) -> AlignedPhoneme:
    return AlignedPhoneme(
        phoneme=phoneme,
        start_frame=start,
        end_frame=end,
        start_ms=float(start * 20),
        end_ms=float(end * 20),
        confidence=confidence,
    )


def _score(phoneme: str, gop: float, confidence: float, status: str) -> PhonemeScore:
    return PhonemeScore(
        phoneme=phoneme,
        gop=gop,
        confidence=confidence,
        status=status,
        start_ms=0.0,
        end_ms=20.0,
    )


def test_syllable_score_is_duration_weighted() -> None:
    phoneme_scores = (
        _score("a", gop=0.9, confidence=0.8, status="pass"),
        _score("m", gop=0.3, confidence=0.6, status="retry"),
    )
    aligned = (_aligned("a", 0, 1), _aligned("m", 1, 4))
    syllables = (SyllableDefinition(text="அம்", phoneme_indices=(0, 1)),)

    result = aggregate_syllables(phoneme_scores, aligned, syllables, ScoringConfig())

    assert result[0].score == pytest.approx((0.9 * 1 + 0.3 * 3) / 4)
    assert result[0].confidence == pytest.approx((0.8 * 1 + 0.6 * 3) / 4)
    assert result[0].status == "retry"


def test_unscorable_phoneme_propagates_to_syllable() -> None:
    phoneme_scores = (
        _score("a", gop=0.9, confidence=0.9, status="pass"),
        _score("m", gop=0.5, confidence=0.2, status="unscorable"),
    )
    aligned = (_aligned("a", 0, 1), _aligned("m", 1, 2))
    syllables = (SyllableDefinition(text="அம்", phoneme_indices=(0, 1)),)

    result = aggregate_syllables(phoneme_scores, aligned, syllables, ScoringConfig())

    assert result[0].status == "unscorable"


def test_syllable_indices_must_fit_phoneme_scores() -> None:
    with pytest.raises(ValueError, match="out of range"):
        aggregate_syllables(
            (_score("a", 0.9, 0.9, "pass"),),
            (_aligned("a", 0, 1),),
            (SyllableDefinition(text="அ", phoneme_indices=(1,)),),
            ScoringConfig(),
        )
