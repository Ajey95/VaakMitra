from __future__ import annotations

import io
import json
import tarfile
import wave
from pathlib import Path

import pytest
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
