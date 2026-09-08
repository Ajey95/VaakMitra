from __future__ import annotations

import json
from pathlib import Path

import pytest
from modeling.training.canary import (
    CanaryReport,
    StageWorkload,
    project_stage_seconds,
    write_canary_report,
)
from pydantic import ValidationError


def _report(**changes: object) -> CanaryReport:
    values: dict[str, object] = {
        "elapsed_seconds": 1_800.0,
        "records": 900,
        "audio_seconds": 5_400.0,
        "frames": 270_000,
        "batches": 900,
        "optimizer_updates": 112,
        "checkpoint_seconds": 18.0,
        "staging_bytes": 13_803_410_250,
        "staging_seconds": 600.0,
        "peak_gpu_allocated_bytes": 8_000_000_000,
        "peak_gpu_reserved_bytes": 9_000_000_000,
        "peak_host_rss_bytes": 4_000_000_000,
        "environment": {
            "gpu": "fixture GPU",
            "gpu_total_bytes": 24_000_000_000,
            "python": "3.10.12",
            "torch": "2.2.0+cu121",
            "cuda": "12.1",
            "bf16": True,
            "run_profile": "deadline_7day",
        },
    }
    values.update(changes)
    return CanaryReport.from_measurements(**values)


def test_canary_projects_stage_updates() -> None:
    report = _report()

    assert report.optimizer_updates_per_minute == pytest.approx(112 / 30)
    assert report.staging_mib_per_second == pytest.approx(
        13_803_410_250 / 600 / (1024 * 1024)
    )
    assert project_stage_seconds(
        report,
        StageWorkload(optimizer_updates=1_120),
    ) == pytest.approx(18_000)


def test_canary_report_is_privacy_safe_and_atomic(tmp_path: Path) -> None:
    output = tmp_path / "canary-report.json"

    write_canary_report(output, _report())

    payload = json.loads(output.read_text(encoding="utf-8"))
    serialized = json.dumps(payload).lower()
    assert payload["evidence_scope"] == "throughput_projection_not_model_quality"
    assert payload["production_ready"] is False
    assert "audio_rel_path" not in serialized
    assert "transcript" not in serialized
    assert "hf_token" not in serialized
    with pytest.raises(FileExistsError):
        write_canary_report(output, _report())


@pytest.mark.parametrize(
    "environment",
    [
        {"HF_TOKEN": "secret"},
        {"gpu": "C:/private/model.nemo"},
        {"transcript": "Tamil text"},
    ],
)
def test_canary_rejects_sensitive_environment_fields(
    environment: dict[str, object],
) -> None:
    with pytest.raises(ValidationError, match="privacy-safe"):
        _report(environment=environment)


def test_canary_rejects_zero_progress() -> None:
    with pytest.raises(ValidationError):
        _report(optimizer_updates=0)
