from __future__ import annotations

import json

import pytest
from modeling.calibration.calibrate_jsonl import main
from modeling.calibration.proxy_calibration import (
    GroupedCalibrationExample,
    ProxyCalibrationExample,
    calibrate_proxy_thresholds,
    fit_grouped_thresholds,
)


def _examples(
    *values: tuple[float | None, bool | None],
) -> tuple[ProxyCalibrationExample, ...]:
    return tuple(
        ProxyCalibrationExample(example_id=f"example-{index}", score=score, acceptable=acceptable)
        for index, (score, acceptable) in enumerate(values)
    )


def test_calibration_selects_lowest_threshold_with_best_acceptance_under_limit() -> None:
    report = calibrate_proxy_thresholds(
        _examples((0.9, True), (0.8, True), (0.7, False), (0.1, False)),
        candidate_thresholds=(0.5, 0.75, 0.85),
        max_false_accept_rate=0.0,
    )

    assert report.pass_threshold == pytest.approx(0.75)
    assert report.coach_threshold == pytest.approx(0.5)
    assert report.false_accepts == 0
    assert report.true_accepts == 2
    assert report.false_accept_rate == pytest.approx(0.0)
    assert report.true_accept_rate == pytest.approx(1.0)
    assert report.calibration_status == "proxy_not_therapist_calibrated"


def test_calibration_raises_when_no_candidate_meets_false_accept_limit() -> None:
    with pytest.raises(ValueError, match="no candidate threshold"):
        calibrate_proxy_thresholds(
            _examples((0.9, True), (0.7, False)),
            candidate_thresholds=(0.5,),
            max_false_accept_rate=0.0,
        )


def test_calibration_uses_lower_threshold_for_deterministic_equal_quality_tie() -> None:
    report = calibrate_proxy_thresholds(
        _examples((0.95, True), (0.1, False)),
        candidate_thresholds=(0.5, 0.75),
        max_false_accept_rate=0.0,
    )

    assert report.pass_threshold == pytest.approx(0.5)
    assert report.coach_threshold == pytest.approx(0.25)


@pytest.mark.parametrize(
    ("score", "acceptable"),
    [
        (None, True),
        (0.5, None),
        (-0.1, False),
        (1.1, True),
        (float("nan"), True),
    ],
)
def test_calibration_example_rejects_invalid_or_partial_evidence(
    score: float | None,
    acceptable: bool | None,
) -> None:
    with pytest.raises(ValueError):
        ProxyCalibrationExample("invalid", score, acceptable)


def test_calibration_reports_unscorable_rate_and_expected_calibration_error() -> None:
    report = calibrate_proxy_thresholds(
        _examples((0.9, True), (0.1, False), (None, None)),
        candidate_thresholds=(0.5,),
        max_false_accept_rate=0.0,
        calibration_bins=10,
    )

    assert report.example_count == 3
    assert report.scorable_count == 2
    assert report.unscorable_count == 1
    assert report.unscorable_rate == pytest.approx(1 / 3)
    assert report.expected_calibration_error == pytest.approx(0.1)
    assert report.brier_score == pytest.approx(0.01)
    assert report.auroc == pytest.approx(1.0)
    assert report.false_reject_rate == pytest.approx(0.0)
    assert report.auroc_ci_low <= report.auroc <= report.auroc_ci_high


def test_calibration_reports_hand_derived_auc_brier_and_false_reject_rate() -> None:
    report = calibrate_proxy_thresholds(
        _examples((0.9, True), (0.4, True), (0.6, False), (0.1, False)),
        candidate_thresholds=(0.5, 0.7),
        max_false_accept_rate=0.0,
        bootstrap_samples=50,
        bootstrap_seed=9,
    )

    assert report.pass_threshold == pytest.approx(0.7)
    assert report.auroc == pytest.approx(0.75)
    assert report.brier_score == pytest.approx(0.185)
    assert report.false_rejects == 1
    assert report.false_reject_rate == pytest.approx(0.5)


def test_calibration_requires_positive_and_negative_scorable_examples() -> None:
    with pytest.raises(ValueError, match="acceptable and unacceptable"):
        calibrate_proxy_thresholds(
            _examples((0.9, True), (0.8, True), (None, None)),
            candidate_thresholds=(0.5,),
            max_false_accept_rate=0.0,
        )


def test_grouped_thresholds_use_phone_support_then_phonological_class_fallback() -> None:
    observations = (
        GroupedCalibrationExample("m1", "m", "nasal", 0.9, True),
        GroupedCalibrationExample("m2", "m", "nasal", 0.8, True),
        GroupedCalibrationExample("m3", "m", "nasal", 0.2, False),
        GroupedCalibrationExample("m4", "m", "nasal", 0.1, False),
        GroupedCalibrationExample("n1", "n", "nasal", 0.85, True),
        GroupedCalibrationExample("n2", "n", "nasal", 0.15, False),
    )

    report = fit_grouped_thresholds(
        observations,
        candidate_thresholds=(0.5, 0.75),
        max_false_accept_rate=0.0,
        minimum_phone_examples=4,
    )

    assert report.phone_thresholds == {"m": pytest.approx(0.5)}
    assert report.class_thresholds == {"nasal": pytest.approx(0.5)}
    assert report.fallback_by_phone == {"n": "nasal"}


def test_calibration_jsonl_cli_writes_aggregate_proxy_report(tmp_path) -> None:
    input_path = tmp_path / "calibration.jsonl"
    output_path = tmp_path / "report.json"
    rows = [
        {"example_id": "clean", "score": 0.9, "acceptable": True},
        {"example_id": "corrupt", "score": 0.1, "acceptable": False},
    ]
    input_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    assert (
        main(
            [
                "--input",
                str(input_path),
                "--output",
                str(output_path),
                "--candidate-thresholds",
                "0.5,0.75",
                "--max-false-accept-rate",
                "0.0",
            ]
        )
        == 0
    )
    output = json.loads(output_path.read_text(encoding="utf-8"))

    assert output["calibration_status"] == "proxy_not_therapist_calibrated"
    assert "example_id" not in output


def test_calibration_cli_rejects_therapist_calibrated_claim(tmp_path) -> None:
    input_path = tmp_path / "calibration.jsonl"
    input_path.write_text(
        json.dumps({"example_id": "clean", "score": 0.9, "acceptable": True}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="therapist-labelled target-user evidence"):
        main(
            [
                "--input",
                str(input_path),
                "--output",
                str(tmp_path / "report.json"),
                "--calibration-status",
                "therapist_calibrated",
            ]
        )
