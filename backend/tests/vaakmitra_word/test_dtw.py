from __future__ import annotations

import numpy as np
import pytest

from app.vaakmitra_word.dtw import (
    InvalidEmbeddingSequence,
    ReferenceBank,
    ReferenceEmbedding,
    cosine_dtw_distance,
)


def valid() -> np.ndarray:
    return np.array([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32)


def test_identical_sequences_have_zero_distance() -> None:
    assert cosine_dtw_distance(valid(), valid()) == pytest.approx(0.0, abs=1e-7)


def test_time_stretched_matching_sequence_remains_close() -> None:
    stretched = np.array([[1.0, 0.0], [1.0, 0.0], [0.0, 1.0]], dtype=np.float32)
    assert cosine_dtw_distance(stretched, valid()) == pytest.approx(0.0, abs=1e-7)


@pytest.mark.parametrize(
    "bad",
    [np.empty((0, 2), dtype=np.float32), np.array([[np.nan, 0.0]], dtype=np.float32)],
)
def test_invalid_sequences_are_rejected(bad: np.ndarray) -> None:
    with pytest.raises(InvalidEmbeddingSequence):
        cosine_dtw_distance(bad, valid())


def test_dimension_mismatch_is_rejected() -> None:
    with pytest.raises(InvalidEmbeddingSequence, match="dimensions"):
        cosine_dtw_distance(valid(), np.ones((2, 3), dtype=np.float32))


def test_reference_model_hash_mismatch_is_unavailable() -> None:
    bank = ReferenceBank(
        version="references-1",
        model_hash="abc",
        references={"TA_00021": [valid()]},
    )

    assert bank.best_distance("TA_00021", valid(), model_hash="different") is None


def test_three_best_distinct_speakers_are_aggregated() -> None:
    far = np.array([[-1.0, 0.0], [0.0, -1.0]], dtype=np.float32)
    middle = np.array([[0.0, 1.0], [1.0, 0.0]], dtype=np.float32)
    bank = ReferenceBank(
        version="references-1",
        model_hash="abc",
        references={
            "TA_00021": [
                ReferenceEmbedding("ref-a1", "speaker-a", valid()),
                ReferenceEmbedding("ref-a2", "speaker-a", far),
                ReferenceEmbedding("ref-b1", "speaker-b", middle),
                ReferenceEmbedding("ref-c1", "speaker-c", far),
                ReferenceEmbedding("ref-d1", "speaker-d", far),
            ]
        },
    )

    match = bank.match("TA_00021", valid(), model_hash="abc")

    assert match is not None
    assert match.distinct_speakers == 4
    assert match.aggregated_speakers == ("speaker-a", "speaker-b", "speaker-c")
    assert match.distance == pytest.approx(8.0 / 9.0)


def test_fewer_than_three_distinct_reference_speakers_is_unavailable() -> None:
    """A prolific speaker must not manufacture independent reference agreement."""
    bank = ReferenceBank(
        version="references-1",
        model_hash="abc",
        references={
            "TA_00021": [
                ReferenceEmbedding("ref-a1", "speaker-a", valid()),
                ReferenceEmbedding("ref-a2", "speaker-a", valid()),
                ReferenceEmbedding("ref-b1", "speaker-b", valid()),
            ]
        },
    )

    assert bank.match("TA_00021", valid(), model_hash="abc") is None
