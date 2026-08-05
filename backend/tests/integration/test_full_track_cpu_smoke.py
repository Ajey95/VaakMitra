from __future__ import annotations

import json
from pathlib import Path

from modeling.training.smoke_full_track import run_cpu_smoke, write_smoke_report


def test_full_track_cpu_smoke_is_deterministic_and_explicitly_not_teacher_training(
    tmp_path: Path,
) -> None:
    first = run_cpu_smoke(seed=17, steps=3)
    second = run_cpu_smoke(seed=17, steps=3)

    assert first == second
    assert first.steps == 3
    assert first.evidence_scope == "fixture_encoder_shapes_only"
    assert first.upstream_checkpoint_loaded is False
    assert first.cuda_training_completed is False
    assert first.final_loss >= 0.0

    output = tmp_path / "full-smoke.json"
    write_smoke_report(output, first)
    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["report_sha256"] == first.digest()
    assert "audio" not in stored


def test_full_track_cpu_smoke_report_refuses_overwrite(tmp_path: Path) -> None:
    output = tmp_path / "full-smoke.json"
    report = run_cpu_smoke(seed=3, steps=1)
    write_smoke_report(output, report)

    try:
        write_smoke_report(output, report)
    except FileExistsError:
        pass
    else:
        raise AssertionError("smoke report overwrote prior evidence")
