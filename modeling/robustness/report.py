"""Aggregate PER/confidence effects for a frozen transformation stress matrix."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Category = Literal["proxy_pass", "proxy_coach", "retry", "unscorable"]


class RobustnessObservation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    transform_id: str = Field(min_length=1)
    severity: Literal["moderate", "severe"]
    baseline_per: float = Field(ge=0.0)
    stressed_per: float = Field(ge=0.0)
    baseline_confidence: float = Field(ge=0.0, le=1.0)
    stressed_confidence: float = Field(ge=0.0, le=1.0)
    stressed_category: Category


class RobustnessResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transform_id: str
    severity: Literal["moderate", "severe"]
    absolute_per_degradation: float
    relative_per_degradation: float
    confidence_delta: float
    stressed_category: Category


class RobustnessReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    results: tuple[RobustnessResult, ...]
    order_inversion_count: int = Field(ge=0)
    severe_confident_decision_violations: int = Field(ge=0)
    promotion_safe: bool
    evidence_scope: Literal["transformation_robustness_only"] = (
        "transformation_robustness_only"
    )
    child_domain_accuracy_measured: Literal[False] = False


def summarize_robustness(
    observations: tuple[RobustnessObservation, ...],
) -> RobustnessReport:
    if not observations:
        raise ValueError("at least one robustness observation is required")
    identifiers = [observation.transform_id for observation in observations]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("robustness transform identifiers must be unique")
    results = tuple(
        RobustnessResult(
            transform_id=item.transform_id,
            severity=item.severity,
            absolute_per_degradation=item.stressed_per - item.baseline_per,
            relative_per_degradation=(
                (item.stressed_per - item.baseline_per) / item.baseline_per
                if item.baseline_per > 0
                else 0.0
            ),
            confidence_delta=item.stressed_confidence - item.baseline_confidence,
            stressed_category=item.stressed_category,
        )
        for item in observations
    )
    inversions = 0
    for first_index, first in enumerate(observations):
        for second in observations[first_index + 1 :]:
            baseline_order = first.baseline_confidence - second.baseline_confidence
            stressed_order = first.stressed_confidence - second.stressed_confidence
            inversions += int(baseline_order * stressed_order < 0)
    violations = sum(
        item.severity == "severe" and item.stressed_category != "unscorable"
        for item in observations
    )
    return RobustnessReport(
        results=results,
        order_inversion_count=inversions,
        severe_confident_decision_violations=violations,
        promotion_safe=violations == 0,
    )
