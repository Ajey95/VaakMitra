"""Immutable release canaries with independent technical and human gates."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

from app.vaakmitra_word.canary import (
    CanaryError,
    CanaryInput,
    build_canary_suite,
    run_canary_suite,
)


def test_build_requires_positive_coverage_and_preserves_governance(tmp_path: Path) -> None:
    records = _records(tmp_path)

    suite = build_canary_suite(
        records,
        active_words=("TA_WORD_0001", "TA_WORD_0002"),
        vocabulary_hash="a" * 64,
        dataset_manifest_hash="b" * 64,
        forbidden_sample_ids=set(),
        audio_root=tmp_path,
    )

    assert suite.positive_words == ("TA_WORD_0001", "TA_WORD_0002")
    assert {record.category for record in suite.records} == {
        "positive", "confusable", "audio_quality_negative"
    }
    assert suite.human_approved is False
    assert all(record.consent_basis and record.reviewer_id for record in suite.records)


def test_build_rejects_missing_positive_word(tmp_path: Path) -> None:
    records = [record for record in _records(tmp_path) if record.word_id != "TA_WORD_0002"]

    with pytest.raises(CanaryError, match="positive_word_coverage_missing"):
        build_canary_suite(
            records,
            active_words=("TA_WORD_0001", "TA_WORD_0002"),
            vocabulary_hash="a" * 64,
            dataset_manifest_hash="b" * 64,
            forbidden_sample_ids=set(),
            audio_root=tmp_path,
        )


def test_build_rejects_training_or_reference_leakage(tmp_path: Path) -> None:
    records = _records(tmp_path)

    with pytest.raises(CanaryError, match="canary_training_reference_leakage"):
        build_canary_suite(
            records,
            active_words=("TA_WORD_0001", "TA_WORD_0002"),
            vocabulary_hash="a" * 64,
            dataset_manifest_hash="b" * 64,
            forbidden_sample_ids={records[0].source_sample_id},
            audio_root=tmp_path,
        )


def test_run_separates_technical_acceptance_from_human_approval(tmp_path: Path) -> None:
    suite = build_canary_suite(
        _records(tmp_path),
        active_words=("TA_WORD_0001", "TA_WORD_0002"),
        vocabulary_hash="a" * 64,
        dataset_manifest_hash="b" * 64,
        forbidden_sample_ids=set(),
        audio_root=tmp_path,
    )

    def evaluate(record: object, _audio: bytes) -> tuple[str, str, float]:
        expected = record.expected_decision  # type: ignore[attr-defined]
        reason = record.allowed_reason_codes[0]  # type: ignore[attr-defined]
        return expected, reason, 12.0

    report = run_canary_suite(suite, audio_root=tmp_path, evaluate=evaluate)

    assert report.technical_accepted is True
    assert report.human_approved is False
    assert report.p95_latency_ms == 12.0
    assert all(item.passed for item in report.results)


def test_run_rejects_changed_audio(tmp_path: Path) -> None:
    suite = build_canary_suite(
        _records(tmp_path),
        active_words=("TA_WORD_0001", "TA_WORD_0002"),
        vocabulary_hash="a" * 64,
        dataset_manifest_hash="b" * 64,
        forbidden_sample_ids=set(),
        audio_root=tmp_path,
    )
    (tmp_path / "positive-1.wav").write_bytes(b"changed")

    with pytest.raises(CanaryError, match="canary_audio_integrity_mismatch"):
        run_canary_suite(
            suite,
            audio_root=tmp_path,
            evaluate=lambda record, audio: (record.expected_decision, record.allowed_reason_codes[0], 1.0),
        )


@pytest.mark.parametrize("script", ["build_canaries.py", "run_canaries.py"])
def test_canary_clis_run_directly_from_backend_root(script: str) -> None:
    backend_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, f"scripts/model/{script}", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr


def _records(tmp_path: Path) -> list[CanaryInput]:
    specs = (
        ("positive-1", "positive", "TA_WORD_0001", "PASS", ("CALIBRATED_TARGET_MATCH",)),
        ("positive-2", "positive", "TA_WORD_0002", "PASS", ("CALIBRATED_TARGET_MATCH",)),
        ("confusable", "confusable", "TA_WORD_0001", "RETRY", ("CALIBRATED_WORD_MISMATCH",)),
        ("bad-audio", "audio_quality_negative", "TA_WORD_0001", "UNSCORABLE", ("INVALID_AUDIO",)),
    )
    records = []
    for name, category, word_id, decision, reasons in specs:
        path = tmp_path / f"{name}.wav"
        path.write_bytes(f"RIFF-{name}".encode())
        records.append(
            CanaryInput(
                canary_id=name,
                source_sample_id=f"source-{name}",
                category=category,
                word_id=word_id,
                target_word="தமிழ்",
                audio_path=path.name,
                expected_decision=decision,
                allowed_reason_codes=reasons,
                consent_basis="public_dataset_permitted_use",
                reviewer_id="reviewer-1",
            )
        )
    return records
