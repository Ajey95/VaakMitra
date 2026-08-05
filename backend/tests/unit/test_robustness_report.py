from __future__ import annotations

import pytest
from modeling.robustness.report import RobustnessObservation, summarize_robustness


def test_report_computes_per_degradation_confidence_and_order_inversions() -> None:
    report = summarize_robustness(
        (
            RobustnessObservation(
                transform_id="moderate-noise-a",
                severity="moderate",
                baseline_per=0.1,
                stressed_per=0.2,
                baseline_confidence=0.9,
                stressed_confidence=0.4,
                stressed_category="proxy_coach",
            ),
            RobustnessObservation(
                transform_id="moderate-noise-b",
                severity="moderate",
                baseline_per=0.2,
                stressed_per=0.25,
                baseline_confidence=0.6,
                stressed_confidence=0.8,
                stressed_category="proxy_pass",
            ),
        )
    )

    assert report.results[0].absolute_per_degradation == pytest.approx(0.1)
    assert report.results[0].relative_per_degradation == pytest.approx(1.0)
    assert report.results[0].confidence_delta == pytest.approx(-0.5)
    assert report.order_inversion_count == 1
    assert report.severe_confident_decision_violations == 0
    assert report.evidence_scope == "transformation_robustness_only"


def test_severe_condition_counts_non_unscorable_as_violation() -> None:
    report = summarize_robustness(
        (
            RobustnessObservation(
                transform_id="severe-clip",
                severity="severe",
                baseline_per=0.1,
                stressed_per=0.9,
                baseline_confidence=0.9,
                stressed_confidence=0.95,
                stressed_category="proxy_pass",
            ),
        )
    )

    assert report.severe_confident_decision_violations == 1
    assert report.promotion_safe is False
