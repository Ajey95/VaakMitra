"""Framework/export/quantization parity metrics for phoneme CTC models."""

from __future__ import annotations

import math
from typing import Any

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field


class ModelParityReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    max_absolute_logit_delta: float = Field(ge=0.0)
    mean_absolute_logit_delta: float = Field(ge=0.0)
    greedy_sequence_agreement: float = Field(ge=0.0, le=1.0)
    per_delta: float
    median_absolute_gop_delta: float = Field(ge=0.0)
    sequence_count: int = Field(gt=0)


def _greedy_sequences(
    logits: npt.NDArray[np.floating[Any]],
    blank_index: int,
) -> tuple[tuple[int, ...], ...]:
    sequences: list[tuple[int, ...]] = []
    for row in np.argmax(logits, axis=-1):
        output: list[int] = []
        previous: int | None = None
        for raw_token in row:
            token = int(raw_token)
            if token != blank_index and token != previous:
                output.append(token)
            previous = token
        sequences.append(tuple(output))
    return tuple(sequences)


def compare_model_parity(
    reference_logits: npt.NDArray[np.floating[Any]],
    candidate_logits: npt.NDArray[np.floating[Any]],
    *,
    blank_index: int,
    reference_per: float,
    candidate_per: float,
    reference_gop: tuple[float, ...],
    candidate_gop: tuple[float, ...],
) -> ModelParityReport:
    """Compare numeric outputs and downstream sequence/GOP behavior."""

    if reference_logits.shape != candidate_logits.shape:
        raise ValueError("reference and candidate logits must have identical shapes")
    if reference_logits.ndim != 3 or reference_logits.shape[0] == 0:
        raise ValueError("logits must be non-empty [batch, frames, vocabulary]")
    if not np.isfinite(reference_logits).all() or not np.isfinite(candidate_logits).all():
        raise ValueError("logits must contain only finite values")
    if not 0 <= blank_index < reference_logits.shape[2]:
        raise ValueError("blank_index must exist in the vocabulary")
    if any(not math.isfinite(value) or value < 0 for value in (reference_per, candidate_per)):
        raise ValueError("phone error rates must be finite and non-negative")
    if len(reference_gop) != len(candidate_gop):
        raise ValueError("GOP sequences must have identical lengths")
    if any(not math.isfinite(value) for value in (*reference_gop, *candidate_gop)):
        raise ValueError("GOP values must be finite")

    absolute = np.abs(reference_logits.astype(np.float64) - candidate_logits.astype(np.float64))
    reference_sequences = _greedy_sequences(reference_logits, blank_index)
    candidate_sequences = _greedy_sequences(candidate_logits, blank_index)
    agreement = sum(
        first == second
        for first, second in zip(reference_sequences, candidate_sequences, strict=True)
    ) / len(reference_sequences)
    gop_delta = (
        float(np.median(np.abs(np.subtract(reference_gop, candidate_gop))))
        if reference_gop
        else 0.0
    )
    return ModelParityReport(
        max_absolute_logit_delta=float(absolute.max()),
        mean_absolute_logit_delta=float(absolute.mean()),
        greedy_sequence_agreement=agreement,
        per_delta=candidate_per - reference_per,
        median_absolute_gop_delta=gop_delta,
        sequence_count=len(reference_sequences),
    )
