from __future__ import annotations

from modeling.evaluation.promotion import ModelEvidence, evaluate_promotion


def _student(**overrides: object) -> ModelEvidence:
    payload: dict[str, object] = {
        "model_id": "student",
        "track": "student",
        "adult_tamil_per": 0.20,
        "significant_baseline_improvement": True,
        "controlled_confusion_auroc": 0.90,
        "proxy_false_accept_rate": 0.05,
        "expected_calibration_error": 0.05,
        "robustness_safe": True,
        "export_succeeded": True,
        "compressed_size_bytes": 50_000_000,
        "int8_per_delta": 0.01,
        "median_absolute_gop_delta": 0.03,
        "physical_android_p95_ms": 500.0,
        "physical_android_measured": True,
    }
    payload.update(overrides)
    return ModelEvidence.model_validate(payload)


def test_student_passes_at_every_exact_promotion_boundary() -> None:
    report = evaluate_promotion(_student())

    assert report.promoted is True
    assert {gate.status for gate in report.gates} == {"pass"}


def test_missing_physical_measurement_is_not_measured_and_never_promoted() -> None:
    report = evaluate_promotion(
        _student(physical_android_p95_ms=None, physical_android_measured=False)
    )
    gates = {gate.name: gate for gate in report.gates}

    assert gates["physical_android_p95_ms"].status == "not_measured"
    assert report.promoted is False


def test_any_failed_quality_gate_blocks_promotion() -> None:
    report = evaluate_promotion(_student(adult_tamil_per=0.21))
    gates = {gate.name: gate for gate in report.gates}

    assert gates["adult_tamil_per"].status == "fail"
    assert report.promoted is False


def test_full_reference_track_does_not_require_edge_only_gates() -> None:
    report = evaluate_promotion(
        ModelEvidence(
            model_id="full",
            track="full_reference",
            adult_tamil_per=0.18,
            significant_baseline_improvement=True,
            controlled_confusion_auroc=0.92,
            proxy_false_accept_rate=0.03,
            expected_calibration_error=0.04,
            robustness_safe=True,
        )
    )

    assert report.promoted is True
    assert "compressed_size_bytes" not in {gate.name for gate in report.gates}


def test_missing_gpu_metrics_are_not_measured_for_full_reference() -> None:
    report = evaluate_promotion(
        ModelEvidence(model_id="full", track="full_reference")
    )

    assert report.promoted is False
    assert all(gate.status == "not_measured" for gate in report.gates)
