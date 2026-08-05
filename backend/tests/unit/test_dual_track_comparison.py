from __future__ import annotations

from modeling.evaluation.promotion import ModelEvidence, evaluate_promotion
from modeling.release.dual_track_comparison import (
    ComparisonCandidate,
    compare_dual_tracks,
)


def _student(model_id: str, per: float, *, export: bool = True) -> ComparisonCandidate:
    promotion = evaluate_promotion(
        ModelEvidence(
            model_id=model_id,
            track="student",
            adult_tamil_per=per,
            significant_baseline_improvement=True,
            controlled_confusion_auroc=0.95,
            proxy_false_accept_rate=0.01,
            expected_calibration_error=0.02,
            robustness_safe=True,
            export_succeeded=export,
            compressed_size_bytes=10_000_000,
            int8_per_delta=0.005,
            median_absolute_gop_delta=0.01,
            physical_android_p95_ms=200.0,
            physical_android_measured=True,
        )
    )
    return ComparisonCandidate(
        model_id=model_id,
        role="student",
        adult_tamil_per=per,
        model_size_bytes=10_000_000,
        exportable=export,
        promotion=promotion,
    )


def test_comparison_selects_best_fully_promoted_edge_student() -> None:
    report = compare_dual_tracks((_student("b", 0.18), _student("a", 0.15)))

    assert report.selected_edge_model_id == "a"
    assert report.edge_selection_status == "promoted_student_selected"


def test_better_quality_cannot_win_when_export_gate_fails() -> None:
    report = compare_dual_tracks(
        (_student("not-exportable", 0.10, export=False), _student("eligible", 0.18))
    )

    assert report.selected_edge_model_id == "eligible"


def test_missing_mandatory_evidence_produces_no_edge_selection() -> None:
    incomplete = ComparisonCandidate(
        model_id="cpu-smoke",
        role="student",
        adult_tamil_per=None,
        model_size_bytes=10_000,
        exportable=True,
        promotion=evaluate_promotion(ModelEvidence(model_id="cpu-smoke", track="student")),
    )

    report = compare_dual_tracks((incomplete,))

    assert report.selected_edge_model_id is None
    assert report.edge_selection_status == "no_student_passed_all_gates"
    assert "missing promoted full-reference GPU evidence" in report.outstanding_work


def test_full_reference_is_recorded_as_ceiling_not_edge_selection() -> None:
    full = ComparisonCandidate(
        model_id="full",
        role="full_reference",
        adult_tamil_per=0.12,
        model_size_bytes=500_000_000,
        exportable=False,
        promotion=evaluate_promotion(
            ModelEvidence(
                model_id="full",
                track="full_reference",
                adult_tamil_per=0.12,
                significant_baseline_improvement=True,
                controlled_confusion_auroc=0.95,
                proxy_false_accept_rate=0.01,
                expected_calibration_error=0.02,
                robustness_safe=True,
            )
        ),
    )

    report = compare_dual_tracks((full, _student("edge", 0.18)))

    assert report.reference_model_id == "full"
    assert report.selected_edge_model_id == "edge"
