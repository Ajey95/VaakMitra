"""Numerical validation for frame-level phoneme CTC log probabilities."""

from __future__ import annotations

import math

import numpy as np

from vaakmitra.ctc.vocabulary import PhonemeVocabulary

_NORMALIZATION_TOLERANCE = 1e-4


def validate_log_probabilities(
    log_probabilities: np.ndarray,
    vocabulary: PhonemeVocabulary,
) -> None:
    """Validate tensor shape, values, and per-frame normalization without mutation."""

    if not isinstance(log_probabilities, np.ndarray):
        raise ValueError("log_probabilities must be a NumPy array")
    if log_probabilities.ndim != 2:
        raise ValueError("log_probabilities must have shape [frames, vocabulary]")
    if log_probabilities.shape[0] == 0:
        raise ValueError("log_probabilities must include at least one frame")
    if log_probabilities.shape[1] != len(vocabulary.tokens):
        raise ValueError("log probability width must match vocabulary")
    if not np.issubdtype(log_probabilities.dtype, np.floating):
        raise ValueError("log_probabilities must use a floating-point dtype")
    if not np.isfinite(log_probabilities).all():
        raise ValueError("log_probabilities must contain only finite values")

    frame_maximum = np.max(log_probabilities, axis=1, keepdims=True)
    log_normalizer = frame_maximum[:, 0] + np.log(
        np.exp(log_probabilities - frame_maximum).sum(axis=1)
    )
    if not np.allclose(log_normalizer, 0.0, atol=_NORMALIZATION_TOLERANCE, rtol=0.0):
        raise ValueError("log probabilities must normalize to one for every frame")


def frame_times_ms(frame_count: int, frame_shift_ms: float) -> np.ndarray:
    """Return deterministic start timestamps for each CTC frame."""

    if frame_count <= 0:
        raise ValueError("frame_count must be positive")
    if not math.isfinite(frame_shift_ms) or frame_shift_ms <= 0:
        raise ValueError("frame_shift_ms must be finite and positive")
    return np.arange(frame_count, dtype=np.float64) * frame_shift_ms

