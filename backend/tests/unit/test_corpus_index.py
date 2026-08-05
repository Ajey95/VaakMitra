from __future__ import annotations

import json
from pathlib import Path

import pytest
from modeling.data.build_corpus_index import load_assignments, load_corpus_records
from modeling.data.corpus_index import (
    CorpusRecord,
    CorpusSource,
    freeze_corpus_index,
    write_frozen_corpus_index,
)
from pydantic import ValidationError


def _source() -> CorpusSource:
    return CorpusSource(
        dataset_id="openslr-127-iisc-mile-tamil",
        revision="f" * 64,
        revision_basis="archive_sha256",
        source_url="https://www.openslr.org/127/",
        license_spdx="CC-BY-2.0",
        population="adult_tamil_proxy",
        local_processing_only=True,
    )


def test_freeze_rejects_source_snapshot_without_verified_archive_digest() -> None:
    source = _source().model_copy(update={"revision_basis": "source_snapshot_sha256"})

    with pytest.raises(ValueError, match="archive_sha256"):
        freeze_corpus_index(
            _records(),
            {
                "speaker-a": "train",
                "speaker-b": "validation",
                "speaker-c": "test",
            },
            source,
        )


def _record(utterance: str, speaker: str, audio_digest: str) -> CorpusRecord:
    return CorpusRecord(
        utterance_id=utterance,
        speaker_id=speaker,
        audio_sha256=audio_digest,
        transcript_sha256=(utterance[0] * 64),
        sample_rate_hz=16_000,
        duration_ms=1_000,
    )


def _records() -> tuple[CorpusRecord, ...]:
    return (
        _record("a1", "speaker-a", "1" * 64),
        _record("b1", "speaker-b", "2" * 64),
        _record("c1", "speaker-c", "3" * 64),
    )


def test_freeze_builds_stable_privacy_safe_split_digests() -> None:
    assignments = {
        "speaker-a": "train",
        "speaker-b": "validation",
        "speaker-c": "test",
    }

    first = freeze_corpus_index(_records(), assignments, _source())
    second = freeze_corpus_index(tuple(reversed(_records())), assignments, _source())

    assert first.digest() == second.digest()
    assert tuple(split.record_count for split in first.splits) == (1, 1, 1)
    payload = json.dumps(first.as_dict())
    assert "a1" not in payload
    assert "speaker-a" not in payload
    assert "transcript_sha256" not in payload
    assert first.evidence_scope == "engineering_proxy"


def test_freeze_rejects_same_audio_digest_across_speakers() -> None:
    records = (
        _record("a1", "speaker-a", "1" * 64),
        _record("b1", "speaker-b", "1" * 64),
    )

    with pytest.raises(ValueError, match="audio digest"):
        freeze_corpus_index(
            records,
            {"speaker-a": "train", "speaker-b": "test"},
            _source(),
        )


def test_freeze_rejects_duplicate_utterance_identifier() -> None:
    records = (
        _record("a1", "speaker-a", "1" * 64),
        _record("a1", "speaker-b", "2" * 64),
    )

    with pytest.raises(ValueError, match="utterance"):
        freeze_corpus_index(
            records,
            {"speaker-a": "train", "speaker-b": "test"},
            _source(),
        )


def test_freeze_requires_every_split_and_one_assignment_per_speaker() -> None:
    with pytest.raises(ValueError, match="train, validation, and test"):
        freeze_corpus_index(
            _records(),
            {"speaker-a": "train", "speaker-b": "train", "speaker-c": "test"},
            _source(),
        )

    with pytest.raises(ValueError, match="missing split assignment"):
        freeze_corpus_index(
            _records(),
            {"speaker-a": "train", "speaker-b": "validation"},
            _source(),
        )


def test_corpus_record_rejects_paths_transcript_text_and_wrong_sample_rate() -> None:
    payload = _record("a1", "speaker-a", "1" * 64).model_dump()
    payload["audio_path"] = "private.wav"
    with pytest.raises(ValidationError, match="audio_path"):
        CorpusRecord.model_validate(payload)

    payload = _record("a1", "speaker-a", "1" * 64).model_dump()
    payload["transcript"] = "private words"
    with pytest.raises(ValidationError, match="transcript"):
        CorpusRecord.model_validate(payload)

    payload = _record("a1", "speaker-a", "1" * 64).model_dump()
    payload["sample_rate_hz"] = 44_100
    with pytest.raises(ValidationError, match="sample_rate_hz"):
        CorpusRecord.model_validate(payload)


def test_writer_refuses_overwrite_and_emits_only_aggregate_index(tmp_path: Path) -> None:
    index = freeze_corpus_index(
        _records(),
        {
            "speaker-a": "train",
            "speaker-b": "validation",
            "speaker-c": "test",
        },
        _source(),
    )
    output = tmp_path / "index.json"

    write_frozen_corpus_index(output, index)

    stored = json.loads(output.read_text(encoding="utf-8"))
    assert stored["record_count"] == 3
    assert stored["source"]["license_spdx"] == "CC-BY-2.0"
    with pytest.raises(FileExistsError):
        write_frozen_corpus_index(output, index)


def test_jsonl_and_assignment_loaders_validate_complete_private_inputs(tmp_path: Path) -> None:
    records_path = tmp_path / "records.jsonl"
    records_path.write_text(
        "\n".join(record.model_dump_json() for record in _records()) + "\n",
        encoding="utf-8",
    )
    assignments_path = tmp_path / "assignments.json"
    assignments_path.write_text(
        json.dumps(
            {
                "speaker-a": "train",
                "speaker-b": "validation",
                "speaker-c": "test",
            }
        ),
        encoding="utf-8",
    )

    assert load_corpus_records(records_path) == _records()
    assert load_assignments(assignments_path)["speaker-b"] == "validation"

    records_path.write_text("\n", encoding="utf-8")
    with pytest.raises(ValueError, match="non-empty"):
        load_corpus_records(records_path)
