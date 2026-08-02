from __future__ import annotations

import numpy as np
import pytest

from vaakmitra.ctc.probabilities import frame_times_ms, validate_log_probabilities
from vaakmitra.ctc.vocabulary import PhonemeVocabulary


@pytest.fixture
def vocabulary() -> PhonemeVocabulary:
    return PhonemeVocabulary(
        version="ta-fixture-1.0.0",
        tokens=("<blank>", "a", "m"),
        blank_token="<blank>",
    )


def test_log_probabilities_must_normalize_per_frame(vocabulary: PhonemeVocabulary) -> None:
    invalid = np.log(np.array([[0.8, 0.8, 0.1]], dtype=np.float32))

    with pytest.raises(ValueError, match="normalize"):
        validate_log_probabilities(invalid, vocabulary)


def test_log_probability_width_must_match_vocabulary(vocabulary: PhonemeVocabulary) -> None:
    invalid = np.log(np.array([[0.5, 0.5]], dtype=np.float32))

    with pytest.raises(ValueError, match="vocabulary"):
        validate_log_probabilities(invalid, vocabulary)


def test_valid_log_probabilities_are_not_modified(vocabulary: PhonemeVocabulary) -> None:
    values = np.log(np.array([[0.1, 0.7, 0.2], [0.2, 0.2, 0.6]], dtype=np.float32))
    before = values.copy()

    validate_log_probabilities(values, vocabulary)

    np.testing.assert_array_equal(values, before)


def test_frame_times_use_deterministic_frame_shift() -> None:
    times = frame_times_ms(frame_count=3, frame_shift_ms=20.0)

    np.testing.assert_array_equal(times, np.array([0.0, 20.0, 40.0]))


@pytest.mark.parametrize(
    ("frame_count", "frame_shift_ms"),
    [(0, 20.0), (2, 0.0), (2, float("nan"))],
)
def test_frame_times_reject_invalid_inputs(frame_count: int, frame_shift_ms: float) -> None:
    with pytest.raises(ValueError):
        frame_times_ms(frame_count=frame_count, frame_shift_ms=frame_shift_ms)
