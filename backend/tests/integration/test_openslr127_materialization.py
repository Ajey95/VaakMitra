from __future__ import annotations

import io
import json
import tarfile
import wave
from pathlib import Path

import pytest
from modeling.data.archive_safety import extract_validated_archive, inspect_tar_archive
from modeling.data.materialize_openslr127 import run_materialization


def _wav_bytes(seed: int) -> bytes:
    output = io.BytesIO()
    with wave.open(output, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(16_000)
        sample = seed.to_bytes(2, byteorder="little", signed=True)
        wav.writeframes(sample * 1_600)
    return output.getvalue()


def _archive(path: Path) -> Path:
    rows = (
        ("train", "ISTL_0000001_0000001", "தமிழ் ஒன்று"),
        ("train", "ISTL_0000002_0000001", "தமிழ் இரண்டு"),
        ("test", "ISTL_0000003_0000001", "தமிழ் மூன்று"),
    )
    with tarfile.open(path, "w:gz") as archive:
        for seed, (split, stem, transcript) in enumerate(rows, start=1):
            for directory, suffix, content in (
                ("audio_files", ".wav", _wav_bytes(seed)),
                ("trans_files", ".txt", transcript.encode()),
            ):
                member = tarfile.TarInfo(f"mile/{split}/{directory}/{stem}{suffix}")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
    return path


def _duplicate_archive(path: Path) -> Path:
    rows = (
        ("train", "ISTL_0000001_0000001", 1, "\u0ba4\u0bae\u0bbf\u0bb4\u0bcd"),
        ("train", "ISTL_0000001_0000002", 2, "\u0b92\u0ba9\u0bcd\u0bb1\u0bc1"),
        ("train", "ISTL_0000001_0000003", 2, "\u0b92\u0ba9\u0bcd\u0bb1\u0bc1"),
        ("train", "ISTL_0000001_0000004", 3, "\u0b87\u0bb0\u0ba3\u0bcd\u0b9f\u0bc1"),
        ("train", "ISTL_0000002_0000001", 3, "\u0b87\u0bb0\u0ba3\u0bcd\u0b9f\u0bc1"),
        ("train", "ISTL_0000003_0000001", 4, "\u0bae\u0bc2\u0ba9\u0bcd\u0bb1\u0bc1"),
        ("train", "ISTL_0000003_0000002", 4, "\u0ba8\u0bbe\u0ba9\u0bcd\u0b95\u0bc1"),
        ("test", "ISTL_0000004_0000001", 5, "\u0b90\u0ba8\u0bcd\u0ba4\u0bc1"),
        ("train", "ISTL_0000005_0000001", 6, "\u0b86\u0bb1\u0bc1"),
    )
    with tarfile.open(path, "w:gz") as archive:
        for split, stem, seed, transcript in rows:
            for directory, suffix, content in (
                ("audio_files", ".wav", _wav_bytes(seed)),
                ("trans_files", ".txt", transcript.encode()),
            ):
                member = tarfile.TarInfo(f"mile/{split}/{directory}/{stem}{suffix}")
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
    return path


def test_materialization_freezes_private_and_aggregate_outputs(tmp_path: Path) -> None:
    archive = _archive(tmp_path / "mile.tar.gz")
    aggregate = tmp_path / "public/evidence.json"
    frozen = tmp_path / "public/frozen-index.json"
    source = tmp_path / "public/source.json"
    private = tmp_path / "private"

    result = run_materialization(
        archive_path=archive,
        extraction_root=tmp_path / "extracted",
        private_output_dir=private,
        aggregate_report_path=aggregate,
        frozen_index_path=frozen,
        source_manifest_path=source,
        source_url="https://www.openslr.org/127/",
        retrieved_at="2026-08-05T13:00:00Z",
    )

    assert result["accepted_count"] == 3
    assert result["split_record_counts"] == {
        "train": 1,
        "validation": 1,
        "test": 1,
    }
    assert aggregate.is_file()
    assert frozen.is_file()
    assert source.is_file()
    assert (private / "records.jsonl").is_file()
    assert (private / "speaker-assignments.json").is_file()
    public_text = aggregate.read_text(encoding="utf-8")
    assert "ISTL_" not in public_text
    assert "தமிழ்" not in public_text
    assert str(tmp_path) not in public_text
    stored_source = json.loads(source.read_text(encoding="utf-8"))
    assert stored_source["revision_basis"] == "archive_sha256"
    assert stored_source["revision"] == result["archive_sha256"]

    with pytest.raises((FileExistsError, ValueError), match=r"exist|empty"):
        run_materialization(
            archive_path=archive,
            extraction_root=tmp_path / "extracted",
            private_output_dir=private,
            aggregate_report_path=aggregate,
            frozen_index_path=frozen,
            source_manifest_path=source,
            source_url="https://www.openslr.org/127/",
            retrieved_at="2026-08-05T13:00:00Z",
        )


def test_materialization_reuses_verified_extraction_with_exact_count_gate(
    tmp_path: Path,
) -> None:
    archive = _archive(tmp_path / "mile.tar.gz")
    extracted = tmp_path / "extracted"
    inspection = inspect_tar_archive(archive, extracted)
    extract_validated_archive(archive, extracted, inspection)

    result = run_materialization(
        archive_path=archive,
        extraction_root=extracted,
        private_output_dir=tmp_path / "private",
        aggregate_report_path=tmp_path / "public/evidence.json",
        frozen_index_path=tmp_path / "public/frozen-index.json",
        source_manifest_path=tmp_path / "public/source.json",
        source_url="https://www.openslr.org/127/",
        retrieved_at="2026-08-05T13:00:00Z",
        reuse_complete_extraction=True,
        expected_record_count=3,
    )

    assert result["accepted_count"] == 3
    assert result["rejections"] == {}


def test_materialization_rejects_reused_extraction_with_wrong_record_count(
    tmp_path: Path,
) -> None:
    archive = _archive(tmp_path / "mile.tar.gz")
    extracted = tmp_path / "extracted"
    inspection = inspect_tar_archive(archive, extracted)
    extract_validated_archive(archive, extracted, inspection)

    with pytest.raises(ValueError, match="expected exactly 4 accepted records"):
        run_materialization(
            archive_path=archive,
            extraction_root=extracted,
            private_output_dir=tmp_path / "private",
            aggregate_report_path=tmp_path / "public/evidence.json",
            frozen_index_path=tmp_path / "public/frozen-index.json",
            source_manifest_path=tmp_path / "public/source.json",
            source_url="https://www.openslr.org/127/",
            retrieved_at="2026-08-05T13:00:00Z",
            reuse_complete_extraction=True,
            expected_record_count=4,
        )

    assert not (tmp_path / "private").exists()
    assert not (tmp_path / "public").exists()


def test_materialization_excludes_duplicate_audio_from_frozen_training_index(
    tmp_path: Path,
) -> None:
    result = run_materialization(
        archive_path=_duplicate_archive(tmp_path / "mile.tar.gz"),
        extraction_root=tmp_path / "extracted",
        private_output_dir=tmp_path / "private",
        aggregate_report_path=tmp_path / "public/evidence.json",
        frozen_index_path=tmp_path / "public/frozen-index.json",
        source_manifest_path=tmp_path / "public/source.json",
        source_url="https://www.openslr.org/127/",
        retrieved_at="2026-08-05T13:00:00Z",
        expected_record_count=9,
    )

    assert result["accepted_count"] == 9
    assert result["training_eligible_count"] == 4
    assert result["exact_audio_duplicate_group_count"] == 3
    assert result["exact_audio_duplicate_record_count"] == 3
    assert result["safe_duplicate_group_count"] == 1
    assert result["cross_speaker_duplicate_group_count"] == 1
    assert result["conflicting_transcript_duplicate_group_count"] == 1
    assert result["excluded_duplicate_record_count"] == 5
    frozen = json.loads((tmp_path / "public/frozen-index.json").read_text())
    assert frozen["record_count"] == 4
    assert len((tmp_path / "private/records.jsonl").read_text().splitlines()) == 4
