"""Compare probability and GOP changes introduced by model optimization."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from vaakmitra.contracts.alignment import AlignedPhoneme
from vaakmitra.ctc.probabilities import validate_log_probabilities
from vaakmitra.ctc.vocabulary import PhonemeVocabulary
from vaakmitra.scoring.gop import phoneme_gop


@dataclass(frozen=True, slots=True)
class OutputComparisonReport:
    max_probability_delta: float
    mean_probability_delta: float
    max_gop_delta: float
    aligned_segment_count: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compare_probability_outputs(
    fp32_log_probabilities: npt.NDArray[np.floating[Any]],
    optimized_log_probabilities: npt.NDArray[np.floating[Any]],
    aligned_phonemes: tuple[AlignedPhoneme, ...],
    vocabulary: PhonemeVocabulary,
) -> OutputComparisonReport:
    """Measure absolute posterior and aligned-GOP degradation."""

    if fp32_log_probabilities.shape != optimized_log_probabilities.shape:
        raise ValueError("FP32 and optimized outputs must have identical shapes")
    validate_log_probabilities(fp32_log_probabilities, vocabulary)
    validate_log_probabilities(optimized_log_probabilities, vocabulary)
    probability_delta = np.abs(
        np.exp(fp32_log_probabilities) - np.exp(optimized_log_probabilities)
    )

    gop_deltas: list[float] = []
    frame_count = fp32_log_probabilities.shape[0]
    for aligned in aligned_phonemes:
        if aligned.end_frame > frame_count:
            raise ValueError("aligned segment exceeds probability frames")
        expected_index = vocabulary.index_of(aligned.phoneme)
        fp32_score = phoneme_gop(
            fp32_log_probabilities[aligned.start_frame : aligned.end_frame],
            expected_index,
            vocabulary.blank_index,
        )
        optimized_score = phoneme_gop(
            optimized_log_probabilities[aligned.start_frame : aligned.end_frame],
            expected_index,
            vocabulary.blank_index,
        )
        gop_deltas.append(abs(fp32_score - optimized_score))

    return OutputComparisonReport(
        max_probability_delta=float(probability_delta.max()),
        mean_probability_delta=float(probability_delta.mean()),
        max_gop_delta=max(gop_deltas, default=0.0),
        aligned_segment_count=len(aligned_phonemes),
    )
