from __future__ import annotations

import numpy as np
import pytest
from modeling.validation.model_parity import compare_model_parity


def test_parity_reports_literal_logit_sequence_per_and_gop_deltas() -> None:
    reference = np.array(
        [[[0.0, 3.0, 0.0], [3.0, 0.0, 0.0], [0.0, 0.0, 3.0]]],
        dtype=np.float32,
    )
    candidate = reference.copy()
    candidate[0, 0, 1] = 2.8

    report = compare_model_parity(
        reference,
        candidate,
        blank_index=0,
        reference_per=0.10,
        candidate_per=0.11,
        reference_gop=(0.8, 0.6, 0.4),
        candidate_gop=(0.79, 0.62, 0.35),
    )

    assert report.max_absolute_logit_delta == pytest.approx(0.2)
    assert report.greedy_sequence_agreement == pytest.approx(1.0)
    assert report.per_delta == pytest.approx(0.01)
    assert report.median_absolute_gop_delta == pytest.approx(0.02)


def test_parity_rejects_shape_mismatch_and_nonfinite_values() -> None:
    with pytest.raises(ValueError, match="identical shapes"):
        compare_model_parity(
            np.zeros((1, 2, 3), dtype=np.float32),
            np.zeros((1, 3, 3), dtype=np.float32),
            blank_index=0,
            reference_per=0.0,
            candidate_per=0.0,
            reference_gop=(),
            candidate_gop=(),
        )
    invalid = np.zeros((1, 2, 3), dtype=np.float32)
    invalid[0, 0, 0] = np.nan
    with pytest.raises(ValueError, match="finite"):
        compare_model_parity(
            invalid,
            np.zeros((1, 2, 3), dtype=np.float32),
            blank_index=0,
            reference_per=0.0,
            candidate_per=0.0,
            reference_gop=(),
            candidate_gop=(),
        )
