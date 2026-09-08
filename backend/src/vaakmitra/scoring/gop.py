"""Expected-versus-competing phoneme evidence over aligned frames."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import numpy.typing as npt

from vaakmitra.contracts.acoustic import AcousticOutput
from vaakmitra.contracts.alignment import AlignmentResult
from vaakmitra.contracts.scoring import PhonemeScore
from vaakmitra.ctc.vocabulary import PhonemeVocabulary
from vaakmitra.scoring.confidence import ScoringConfig, classify_score, combine_confidence


class UnscorableEvidenceError(ValueError):
    """Raised when the score contract cannot produce responsible evidence."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def phoneme_gop(
    segment: npt.NDArray[np.floating[Any]],
    expected_index: int,
    blank_index: int,
) -> float:
    """Return sigmoid of expected mean log posterior versus strongest competitor."""

    if not isinstance(segment, np.ndarray) or segment.ndim != 2 or segment.shape[0] == 0:
        raise ValueError("segment must be a non-empty [frames, vocabulary] array")
    width = segment.shape[1]
    if not 0 <= expected_index < width or not 0 <= blank_index < width:
        raise ValueError("phoneme indices must fit the segment vocabulary")
    if expected_index == blank_index:
        raise ValueError("expected phoneme cannot be the blank token")
    if not np.isfinite(segment).all():
        raise ValueError("segment must contain finite log probabilities")

    competitor_indices = [
        index for index in range(width) if index not in {expected_index, blank_index}
    ]
    if not competitor_indices:
        raise ValueError("GOP requires at least one non-blank competing phoneme")
    expected_mean = float(segment[:, expected_index].mean())
    strongest_competitor = float(segment[:, competitor_indices].mean(axis=0).max())
    margin = expected_mean - strongest_competitor
    if margin >= 0:
        return 1.0 / (1.0 + math.exp(-margin))
    exponential = math.exp(margin)
    return exponential / (1.0 + exponential)


def score_aligned_phonemes(
    output: AcousticOutput,
    alignment: AlignmentResult,
    vocabulary: PhonemeVocabulary,
    config: ScoringConfig,
) -> tuple[PhonemeScore, ...]:
    """Score Member 1's valid aligned segments against Member 2 probabilities."""

    if alignment.status != "valid":
        raise UnscorableEvidenceError("alignment_invalid")
    if alignment.confidence < config.min_alignment_confidence:
        raise UnscorableEvidenceError("alignment_low_confidence")
    if output.vocabulary_version != vocabulary.version:
        raise UnscorableEvidenceError("vocabulary_version_mismatch")
    if output.vocabulary_size != len(vocabulary.tokens):
        raise UnscorableEvidenceError("vocabulary_size_mismatch")
    if output.blank_index != vocabulary.blank_index:
        raise UnscorableEvidenceError("blank_index_mismatch")

    frame_count = output.log_probabilities.shape[0]
    scores: list[PhonemeScore] = []
    for aligned in alignment.phonemes:
        try:
            expected_index = vocabulary.index_of(aligned.phoneme)
        except KeyError as error:
            raise UnscorableEvidenceError("phoneme_not_in_vocabulary") from error
        if aligned.start_frame < 0 or aligned.end_frame > frame_count:
            raise UnscorableEvidenceError("segment_out_of_bounds")
        segment = output.log_probabilities[aligned.start_frame : aligned.end_frame]
        if segment.shape[0] == 0:
            raise UnscorableEvidenceError("empty_aligned_segment")

        gop = phoneme_gop(segment, expected_index, output.blank_index)
        confidence = combine_confidence(
            gop=gop,
            alignment_confidence=aligned.confidence,
            config=config,
        )
        status = classify_score(gop, confidence, config)
        scores.append(
            PhonemeScore(
                phoneme=aligned.phoneme,
                gop=gop,
                confidence=confidence,
                status=status,
                start_ms=aligned.start_ms,
                end_ms=aligned.end_ms,
                reason="phoneme_low_confidence" if status == "unscorable" else None,
            )
        )
    return tuple(scores)
