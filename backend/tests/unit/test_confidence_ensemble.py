from __future__ import annotations

import pytest
from modeling.calibration.confidence_ensemble import (
    ProxyConfidenceFeatures,
    combine_proxy_confidence,
)
from pydantic import ValidationError


def _features(**overrides: object) -> ProxyConfidenceFeatures:
    payload: dict[str, object] = {
        "gop_margin": 1.0,
        "alignment_confidence": 1.0,
        "normalized_entropy": 0.0,
        "posterior_margin": 1.0,
        "blank_dominance": 0.0,
        "duration_valid": True,
        "scorer_agreement": 1.0,
        "model_disagreement": 0.0,
    }
    payload.update(overrides)
    return ProxyConfidenceFeatures.model_validate(payload)


def test_perfect_proxy_features_produce_proxy_pass() -> None:
    result = combine_proxy_confidence(_features())

    assert result.score == pytest.approx(1.0)
    assert result.category == "proxy_pass"
    assert result.unscorable_reason is None


def test_model_disagreement_reduces_confidence_conservatively() -> None:
    agreed = combine_proxy_confidence(_features(model_disagreement=0.0))
    disagreed = combine_proxy_confidence(_features(model_disagreement=1.0))

    assert agreed.score is not None and disagreed.score is not None
    assert disagreed.score < agreed.score


@pytest.mark.parametrize(
    ("overrides", "reason"),
    [
        ({"alignment_confidence": 0.2}, "weak_alignment"),
        ({"duration_valid": False}, "invalid_duration"),
        ({"blank_dominance": 0.95}, "blank_dominance"),
    ],
)
def test_weak_evidence_is_unscorable(overrides: dict[str, object], reason: str) -> None:
    result = combine_proxy_confidence(_features(**overrides))

    assert result.score is None
    assert result.category == "unscorable"
    assert result.unscorable_reason == reason


@pytest.mark.parametrize("field", ["normalized_entropy", "model_disagreement", "gop_margin"])
def test_features_reject_out_of_range_values(field: str) -> None:
    with pytest.raises(ValidationError):
        _features(**{field: 1.1})
