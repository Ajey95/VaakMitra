from __future__ import annotations

import math

import numpy as np
import pytest

from vaakmitra.contracts.acoustic import AcousticOutput
from vaakmitra.contracts.alignment import AlignedPhoneme, AlignmentResult
from vaakmitra.ctc.vocabulary import PhonemeVocabulary
from vaakmitra.scoring.confidence import ScoringConfig
from vaakmitra.scoring.gop import (
    UnscorableEvidenceError,
    phoneme_gop,
    score_aligned_phonemes,
)


def test_gop_uses_strongest_non_blank_competitor() -> None:
    segment = np.log(
        np.array(
            [
                [0.05, 0.70, 0.20, 0.05],
                [0.05, 0.60, 0.30, 0.05],
            ],
            dtype=np.float64,
        )
    )

    score = phoneme_gop(segment, expected_index=1, blank_index=0)

    expected_margin = np.mean(np.log([0.70, 0.60])) - np.mean(np.log([0.20, 0.30]))
    expected_score = 1.0 / (1.0 + math.exp(-expected_margin))
    assert score == pytest.approx(expected_score)


def test_gop_excludes_high_blank_probability_from_competitors() -> None:
    segment = np.log(np.array([[0.80, 0.15, 0.05]], dtype=np.float64))

    score = phoneme_gop(segment, expected_index=1, blank_index=0)

    assert score == pytest.approx(0.75)


def test_gop_rejects_empty_segment() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        phoneme_gop(np.empty((0, 3)), expected_index=1, blank_index=0)


def test_low_alignment_confidence_is_unscorable() -> None:
    vocabulary = PhonemeVocabulary("fixture-vocab-1", ("<blank>", "a", "m"))
    probabilities = np.log(
        np.array([[0.05, 0.85, 0.10], [0.05, 0.80, 0.15]], dtype=np.float32)
    )
    output = AcousticOutput(
        log_probabilities=probabilities,
        frame_shift_ms=20.0,
        model_version="fixture-model-1",
        vocabulary_version=vocabulary.version,
        blank_index=vocabulary.blank_index,
        vocabulary_size=len(vocabulary.tokens),
    )
    alignment = AlignmentResult(
        status="valid",
        confidence=0.2,
        phonemes=(
            AlignedPhoneme(
                phoneme="a",
                start_frame=0,
                end_frame=2,
                start_ms=0.0,
                end_ms=40.0,
                confidence=0.9,
            ),
        ),
    )

    with pytest.raises(UnscorableEvidenceError, match="alignment_low_confidence"):
        score_aligned_phonemes(output, alignment, vocabulary, ScoringConfig())


def test_aligned_phoneme_bounds_must_fit_probability_frames() -> None:
    vocabulary = PhonemeVocabulary("fixture-vocab-1", ("<blank>", "a", "m"))
    probabilities = np.log(np.array([[0.05, 0.85, 0.10]], dtype=np.float32))
    output = AcousticOutput(
        log_probabilities=probabilities,
        frame_shift_ms=20.0,
        model_version="fixture-model-1",
        vocabulary_version=vocabulary.version,
        blank_index=vocabulary.blank_index,
        vocabulary_size=len(vocabulary.tokens),
    )
    alignment = AlignmentResult(
        status="valid",
        confidence=0.9,
        phonemes=(
            AlignedPhoneme(
                phoneme="a",
                start_frame=0,
                end_frame=2,
                start_ms=0.0,
                end_ms=40.0,
                confidence=0.9,
            ),
        ),
    )

    with pytest.raises(UnscorableEvidenceError, match="segment_out_of_bounds"):
        score_aligned_phonemes(output, alignment, vocabulary, ScoringConfig())

