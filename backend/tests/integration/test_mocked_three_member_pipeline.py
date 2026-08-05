from __future__ import annotations

import json
import sys
from io import BytesIO, TextIOWrapper
from pathlib import Path

import pytest
from modeling.team_mocks.run_mocked_pipeline import main, run_mocked_pipeline


def _all_keys(value: object) -> set[str]:
    if isinstance(value, dict):
        return set(value).union(*(_all_keys(item) for item in value.values()), set())
    if isinstance(value, list):
        return set().union(*(_all_keys(item) for item in value), set())
    return set()


def test_mocked_team_flow_is_complete_private_and_non_production(tmp_path: Path) -> None:
    report_path = tmp_path / "mocked-team.json"

    report = run_mocked_pipeline(report_path)
    payload = report.as_dict()

    assert report_path.is_file()
    assert json.loads(report_path.read_text(encoding="utf-8")) == payload
    assert payload["evidence_scope"] == "mocked_three_member_pipeline"
    assert payload["release_status"] == "technical_prototype"
    assert payload["production_eligible"] is False
    assert payload["clinical_validity"] is False
    assert payload["member1"]["implementation"] == "deterministic_mock"
    assert payload["member2"]["status"] == "ok"
    assert payload["member3"]["implementation"] == "deterministic_mock"
    assert len(payload["evidence_digest"]) == 64
    assert {
        "audio",
        "audio_path",
        "log_probabilities",
        "embeddings",
        "transcript",
        "identity",
    }.isdisjoint(_all_keys(payload))


def test_mocked_team_flow_refuses_to_overwrite_evidence(tmp_path: Path) -> None:
    report_path = tmp_path / "mocked-team.json"
    report_path.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="output exists"):
        run_mocked_pipeline(report_path)


def test_mocked_pipeline_cli_is_safe_on_windows_cp1252_console(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    console_bytes = BytesIO()
    console = TextIOWrapper(console_bytes, encoding="cp1252")
    monkeypatch.setattr(sys, "stdout", console)

    exit_code = main(["--report", str(tmp_path / "mocked-team.json")])
    console.flush()

    assert exit_code == 0
    assert "mocked_three_member_pipeline" in console_bytes.getvalue().decode("cp1252")
