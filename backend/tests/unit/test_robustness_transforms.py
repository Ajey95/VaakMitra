from __future__ import annotations

import numpy as np
import pytest
from modeling.robustness.transforms import StressSpec, apply_stress, load_stress_matrix

MATRIX_PATH = "modeling/configs/robustness_matrix.json"


def _waveform() -> np.ndarray:
    time = np.arange(3_200, dtype=np.float32) / 16_000.0
    return (0.2 * np.sin(2.0 * np.pi * 440.0 * time)).astype(np.float32)


@pytest.mark.parametrize(
    ("kind", "value"),
    [
        ("rate", 1.1),
        ("pitch_formant", 1.08),
        ("vtln", 1.05),
        ("pause", 0.02),
        ("repetition", 0.02),
        ("noise", 15.0),
        ("gain", 0.5),
        ("clipping", 0.1),
        ("bandwidth", 3_500.0),
        ("resampling", 8_000.0),
    ],
)
def test_stress_transforms_are_finite_float32_and_sequence_preserving_metadata(
    kind: str, value: float
) -> None:
    result = apply_stress(
        _waveform(),
        StressSpec(
            transform_id=f"moderate-{kind}", kind=kind, severity="moderate", value=value
        ),
        seed=7,
    )

    assert result.waveform.dtype == np.float32
    assert result.waveform.ndim == 1
    assert result.waveform.size > 0
    assert np.isfinite(result.waveform).all()
    assert float(np.max(np.abs(result.waveform))) <= 1.0
    assert result.preserves_expected_sequence is True
    assert result.evidence_scope == "transformation_robustness_only"


def test_seeded_noise_is_deterministic_and_changes_with_seed() -> None:
    spec = StressSpec(
        transform_id="noise", kind="noise", severity="moderate", value=10.0
    )

    first = apply_stress(_waveform(), spec, seed=3).waveform
    repeated = apply_stress(_waveform(), spec, seed=3).waveform
    changed = apply_stress(_waveform(), spec, seed=4).waveform

    np.testing.assert_array_equal(first, repeated)
    assert not np.array_equal(first, changed)


def test_severe_stress_requires_unscorable_metamorphic_outcome() -> None:
    result = apply_stress(
        _waveform(),
        StressSpec(
            transform_id="severe-clip", kind="clipping", severity="severe", value=0.02
        ),
        seed=1,
    )

    assert result.expected_outcome == "unscorable_preferred"


def test_transform_rejects_nonfinite_or_out_of_range_waveform() -> None:
    with pytest.raises(ValueError, match="finite"):
        apply_stress(
            np.array([0.0, np.nan], dtype=np.float32),
            StressSpec(transform_id="gain", kind="gain", severity="moderate", value=0.5),
            seed=1,
        )


def test_frozen_matrix_is_transformation_only_and_has_unique_ids() -> None:
    matrix = load_stress_matrix(MATRIX_PATH)

    assert matrix.sample_rate_hz == 16_000
    assert matrix.evidence_scope == "transformation_robustness_only"
    assert matrix.child_domain_accuracy_measured is False
    assert len(matrix.transforms) == 11
    assert len({item.transform_id for item in matrix.transforms}) == 11
    with pytest.raises(ValueError, match=r"\[-1, 1\]"):
        apply_stress(
            np.array([2.0], dtype=np.float32),
            StressSpec(transform_id="gain", kind="gain", severity="moderate", value=0.5),
            seed=1,
        )
