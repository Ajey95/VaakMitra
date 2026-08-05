from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest
from modeling.data.openslr127 import (
    MaterializedRecord,
    assign_speakers,
    deduplicate_audio_records,
    inspect_extracted_corpus,
    speaker_from_utterance_id,
)


def _write_wav(
    path: Path,
    *,
    channels: int = 1,
    sample_rate: int = 16_000,
    sample_width: int = 2,
    frames: int = 1_600,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(sample_width)
        output.setframerate(sample_rate)
        output.writeframes(b"\x00" * frames * channels * sample_width)


def _make_pair(
    root: Path,
    *,
    split: str,
    stem: str,
    transcript: str = "தமிழ் மொழி",
    channels: int = 1,
) -> None:
    _write_wav(
        root / "mile_tamil" / split / "audio_files" / f"{stem}.wav",
        channels=channels,
    )
    transcript_path = root / "mile_tamil" / split / "trans_files" / f"{stem}.txt"
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    transcript_path.write_text(transcript, encoding="utf-8")


def test_inspection_pairs_valid_audio_and_normalizes_transcript(tmp_path: Path) -> None:
    _make_pair(
        tmp_path,
        split="train",
        stem="ISTL_0000202_0000009",
        transcript="  தமிழ் மொழி  ",
    )

    result = inspect_extracted_corpus(tmp_path, archive_sha256="a" * 64)

    assert len(result.records) == 1
    record = result.records[0]
    assert record.utterance_id == "ISTL_0000202_0000009"
    assert record.speaker_id == "ISTL_0000202"
    assert record.official_split == "train"
    assert record.sample_rate_hz == 16_000
    assert record.duration_ms == 100
    assert record.normalized_transcript == "தமிழ் மொழி"
    assert result.report.accepted_count == 1
    assert result.report.total_duration_ms == 100
    assert result.report.rejections == {}
    public_payload = result.report.model_dump_json()
    assert str(tmp_path) not in public_payload
    assert "ISTL_0000202" not in public_payload

    parallel = inspect_extracted_corpus(
        tmp_path,
        archive_sha256="a" * 64,
        hash_workers=2,
    )
    assert parallel == result
    assert "தமிழ்" not in public_payload


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    (
        ({"channels": 2}, "invalid_wav_channels"),
        ({"sample_rate": 8_000}, "invalid_wav_sample_rate"),
        ({"sample_width": 1}, "invalid_wav_sample_width"),
        ({"frames": 0}, "invalid_wav_duration"),
    ),
)
def test_inspection_rejects_invalid_wav_contract(
    tmp_path: Path, kwargs: dict[str, int], reason: str
) -> None:
    stem = "ISTL_0000202_0000009"
    audio = tmp_path / "mile_tamil/train/audio_files" / f"{stem}.wav"
    _write_wav(audio, **kwargs)
    transcript = tmp_path / "mile_tamil/train/trans_files" / f"{stem}.txt"
    transcript.parent.mkdir(parents=True, exist_ok=True)
    transcript.write_text("தமிழ்", encoding="utf-8")

    result = inspect_extracted_corpus(tmp_path, archive_sha256="b" * 64)

    assert result.records == ()
    assert result.report.rejections == {reason: 1}
    assert str(audio) not in result.report.model_dump_json()


def test_inspection_rejects_missing_pair_non_tamil_and_unrecognized_identifier(
    tmp_path: Path,
) -> None:
    _write_wav(tmp_path / "mile_tamil/train/audio_files/ISTL_0000001_0000001.wav")
    _make_pair(
        tmp_path,
        split="train",
        stem="ISTL_0000002_0000001",
        transcript="English only",
    )
    _make_pair(tmp_path, split="test", stem="unknown", transcript="தமிழ்")

    result = inspect_extracted_corpus(tmp_path, archive_sha256="c" * 64)

    assert result.records == ()
    assert result.report.rejections == {
        "missing_transcript": 1,
        "non_tamil_transcript": 1,
        "unrecognized_utterance_id": 1,
    }


def test_speaker_extraction_is_strict() -> None:
    assert speaker_from_utterance_id("ISTL_0000202_0000009") == "ISTL_0000202"
    with pytest.raises(ValueError, match="speaker identity"):
        speaker_from_utterance_id("unknown")


def test_assignments_retain_disjoint_official_test_and_select_validation() -> None:
    official = {
        **{f"ISTL_{speaker:07d}": "train" for speaker in range(1, 11)},
        "ISTL_0000011": "test",
    }

    first = assign_speakers(official)
    second = assign_speakers(dict(reversed(tuple(official.items()))))

    assert first.assignments == second.assignments
    assert first.policy_version == "official-test-plus-train-validation-sha256-v1"
    assert first.official_overlap_count == 0
    assert first.assignments["ISTL_0000011"] == "test"
    assert list(first.assignments.values()).count("validation") == 1
    assert list(first.assignments.values()).count("train") == 9


def test_assignments_resplit_all_speakers_when_official_overlap_exists() -> None:
    official_rows = [
        (f"ISTL_{speaker:07d}", "train") for speaker in range(1, 11)
    ] + [("ISTL_0000001", "test")]

    result = assign_speakers(official_rows)

    assert result.policy_version == "speaker-sha256-80-10-10-v1"
    assert result.official_overlap_count == 1
    assert set(result.assignments.values()) == {"train", "validation", "test"}
    assert list(result.assignments.values()).count("validation") == 1
    assert list(result.assignments.values()).count("test") == 1
    assert "ISTL_0000001" not in json.dumps(result.model_dump(mode="json"))


def _record(
    utterance_id: str,
    speaker_id: str,
    audio_sha256: str,
    transcript_sha256: str,
) -> MaterializedRecord:
    return MaterializedRecord(
        utterance_id=utterance_id,
        speaker_id=speaker_id,
        official_split="train",
        audio_path=Path(f"{utterance_id}.wav"),
        transcript_path=Path(f"{utterance_id}.txt"),
        normalized_transcript="\u0ba4\u0bae\u0bbf\u0bb4\u0bcd",
        audio_sha256=audio_sha256,
        transcript_sha256=transcript_sha256,
        sample_rate_hz=16_000,
        duration_ms=100,
    )


def test_audio_deduplication_collapses_safe_groups_and_excludes_risky_groups() -> None:
    records = (
        _record("A", "speaker-1", "a" * 64, "1" * 64),
        _record("B", "speaker-1", "b" * 64, "2" * 64),
        _record("C", "speaker-1", "b" * 64, "2" * 64),
        _record("D", "speaker-1", "c" * 64, "3" * 64),
        _record("E", "speaker-2", "c" * 64, "3" * 64),
        _record("F", "speaker-3", "d" * 64, "4" * 64),
        _record("G", "speaker-3", "d" * 64, "5" * 64),
    )

    result = deduplicate_audio_records(records)

    assert [record.utterance_id for record in result.eligible_records] == ["A", "B"]
    assert result.duplicate_group_count == 3
    assert result.duplicate_record_count == 3
    assert result.safe_collapsed_group_count == 1
    assert result.cross_speaker_group_count == 1
    assert result.conflicting_transcript_group_count == 1
    assert result.excluded_record_count == 5
