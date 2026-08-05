from __future__ import annotations

from modeling.evaluation.promotion import ModelEvidence, evaluate_promotion
from modeling.release.dual_track_comparison import ComparisonCandidate, compare_dual_tracks
from modeling.training.smoke_full_track import run_cpu_smoke
from modeling.training.smoke_student_track import run_student_smoke


def test_cpu_evidence_reports_both_tracks_without_claiming_gpu_or_device_completion() -> None:
    full_smoke = run_cpu_smoke(seed=17, steps=1)
    student_smoke = run_student_smoke(seed=23, steps=1)
    candidates = [
        ComparisonCandidate(
            model_id="indicconformer-full-cpu-smoke",
            role="full_reference",
            adult_tamil_per=None,
            model_size_bytes=None,
            exportable=False,
            promotion=evaluate_promotion(
                ModelEvidence(
                    model_id="indicconformer-full-cpu-smoke", track="full_reference"
                )
            ),
        )
    ]
    candidates.extend(
        ComparisonCandidate(
            model_id=f"{candidate.architecture}-cpu-smoke",
            role="student",
            adult_tamil_per=None,
            model_size_bytes=candidate.fp32_size_bytes,
            exportable=True,
            promotion=evaluate_promotion(
                ModelEvidence(
                    model_id=f"{candidate.architecture}-cpu-smoke",
                    track="student",
                    export_succeeded=True,
                    compressed_size_bytes=candidate.fp32_size_bytes,
                )
            ),
        )
        for candidate in student_smoke.candidates
    )

    report = compare_dual_tracks(tuple(candidates))

    assert full_smoke.cuda_training_completed is False
    assert student_smoke.cuda_training_completed is False
    assert report.reference_model_id is None
    assert report.selected_edge_model_id is None
    assert "missing promoted full-reference GPU evidence" in report.outstanding_work
    assert "missing physical Android benchmark" in report.outstanding_work
