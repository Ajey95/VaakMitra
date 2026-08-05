"""Conservative proxy-confidence ensemble for non-clinical engineering evidence."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProxyCategory = Literal["proxy_pass", "proxy_coach", "retry", "unscorable"]


class ProxyConfidenceFeatures(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    gop_margin: float = Field(ge=-1.0, le=1.0)
    alignment_confidence: float = Field(ge=0.0, le=1.0)
    normalized_entropy: float = Field(ge=0.0, le=1.0)
    posterior_margin: float = Field(ge=0.0, le=1.0)
    blank_dominance: float = Field(ge=0.0, le=1.0)
    duration_valid: bool
    scorer_agreement: float = Field(ge=0.0, le=1.0)
    model_disagreement: float = Field(ge=0.0, le=1.0)


class ProxyConfidenceResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    score: float | None = Field(default=None, ge=0.0, le=1.0)
    category: ProxyCategory
    unscorable_reason: Literal[
        "weak_alignment", "invalid_duration", "blank_dominance"
    ] | None = None


def combine_proxy_confidence(features: ProxyConfidenceFeatures) -> ProxyConfidenceResult:
    """Combine independent evidence and prefer neutral output under weak conditions."""

    if not features.duration_valid:
        return ProxyConfidenceResult(category="unscorable", unscorable_reason="invalid_duration")
    if features.alignment_confidence < 0.35:
        return ProxyConfidenceResult(category="unscorable", unscorable_reason="weak_alignment")
    if features.blank_dominance > 0.90:
        return ProxyConfidenceResult(category="unscorable", unscorable_reason="blank_dominance")
    normalized_gop = (features.gop_margin + 1.0) / 2.0
    score = (
        0.25 * normalized_gop
        + 0.20 * features.alignment_confidence
        + 0.15 * (1.0 - features.normalized_entropy)
        + 0.15 * features.posterior_margin
        + 0.05 * (1.0 - features.blank_dominance)
        + 0.10 * features.scorer_agreement
        + 0.10 * (1.0 - features.model_disagreement)
    )
    bounded = min(1.0, max(0.0, score))
    category: ProxyCategory
    if bounded >= 0.75:
        category = "proxy_pass"
    elif bounded >= 0.50:
        category = "proxy_coach"
    else:
        category = "retry"
    return ProxyConfidenceResult(score=bounded, category=category)
