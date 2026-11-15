from __future__ import annotations

import numpy as np
import pytest

from app.vaakmitra_word.audio import DecodedAudio
from app.vaakmitra_word.normalization import NormalizationConfig, create_normalized_view


def decoded() -> DecodedAudio:
    samples = np.linspace(-0.2, 0.4, 16000, dtype=np.float32)
    return DecodedAudio(samples=samples, sample_rate=16000, duration_s=1.0)


def test_normalization_does_not_mutate_original() -> None:
    source = decoded()
    before = source.samples.copy()

    view = create_normalized_view(source, NormalizationConfig())

    assert np.array_equal(source.samples, before)
    assert view.available is True
    assert np.isfinite(view.samples).all()
    assert np.max(np.abs(view.samples)) <= 0.95


@pytest.mark.parametrize(
    "values",
    [
        {"rate_factor": 0.84},
        {"rate_factor": 1.19},
        {"vtln_warp": 0.87},
        {"vtln_warp": 1.13},
    ],
)
def test_config_rejects_transform_outside_ssot_bounds(values: dict) -> None:
    with pytest.raises(ValueError):
        NormalizationConfig(**values)


def test_unapproved_rate_or_vtln_request_is_unavailable() -> None:
    view = create_normalized_view(
        decoded(),
        NormalizationConfig(rate_factor=0.9, rate_approved=False),
    )

    assert view.available is False
    assert view.reason == "rate_transform_not_approved"

