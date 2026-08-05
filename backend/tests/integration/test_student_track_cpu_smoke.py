from __future__ import annotations

import json
from pathlib import Path

from modeling.training.smoke_student_track import run_student_smoke, write_student_smoke_report


def test_student_smoke_trains_both_candidates_deterministically(tmp_path: Path) -> None:
    first = run_student_smoke(seed=23, steps=1)
    second = run_student_smoke(seed=23, steps=1)

    assert first == second
    assert tuple(candidate.architecture for candidate in first.candidates) == (
        "conformer",
        "conv_bigru",
    )
    assert all(candidate.parameter_count > 0 for candidate in first.candidates)
    assert all(candidate.final_loss >= 0.0 for candidate in first.candidates)
    assert first.evidence_scope == "distillation_smoke_only"
    assert first.teacher_checkpoint_loaded is False
    assert first.cuda_training_completed is False

    output = tmp_path / "student-smoke.json"
    write_student_smoke_report(output, first)
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["report_sha256"] == first.digest()
    assert "features" not in stored
