from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

import pytest
from modeling.data.prepare_tamil_tts_proxy import prepare_tamil_tts_proxy


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=("rel_path", "text", "phonemes", "speaker"),
            delimiter="|",
        )
        writer.writeheader()
        writer.writerows(rows)


def _source_fixture(tmp_path: Path) -> Path:
    source = tmp_path / "source"
    source.mkdir()
    _write_csv(
        source / "train.csv",
        [
            {"rel_path": "wavs/a/1.wav", "text": "one", "phonemes": "a", "speaker": "a"},
            {"rel_path": "wavs/b/1.wav", "text": "two", "phonemes": "m", "speaker": "b"},
            {"rel_path": "wavs/c/1.wav", "text": "three", "phonemes": "a m", "speaker": "c"},
        ],
    )
    _write_csv(
        source / "val.csv",
        [
            {"rel_path": "wavs/a/2.wav", "text": "four", "phonemes": "a:", "speaker": "a"},
            {"rel_path": "wavs/b/2.wav", "text": "five", "phonemes": "m a", "speaker": "b"},
            {"rel_path": "wavs/c/2.wav", "text": "six", "phonemes": "a m", "speaker": "c"},
        ],
    )
    _write_csv(
        source / "test.csv",
        [
            {"rel_path": "wavs/d/1.wav", "text": "seven", "phonemes": "a", "speaker": "d"}
        ],
    )
    return source


def _prepare(source: Path, output: Path):
    return prepare_tamil_tts_proxy(
        source_dir=source,
        output_dir=output,
        dataset_id="asishbala/tamil-tts-dataset",
        revision="1d6a78e02c6c21d8da30eb57dd4dc02b4ed765f5",
        source_url="https://huggingface.co/datasets/asishbala/tamil-tts-dataset",
        license_spdx="CC0-1.0",
        validation_speaker_fraction=0.34,
        split_seed="vaakmitra-member2-v1",
    )


def _index_speakers(path: Path) -> set[str]:
    return {
        json.loads(line)["speaker"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    }


def test_preparation_derives_speaker_disjoint_splits_and_strips_text(tmp_path) -> None:
    result = _prepare(_source_fixture(tmp_path), tmp_path / "prepared")

    train_speakers = _index_speakers(result.train_index)
    validation_speakers = _index_speakers(result.validation_index)
    test_speakers = _index_speakers(result.test_index)
    assert train_speakers
    assert validation_speakers
    assert test_speakers == {"d"}
    assert train_speakers.isdisjoint(validation_speakers)
    assert train_speakers.isdisjoint(test_speakers)
    assert validation_speakers.isdisjoint(test_speakers)
    assert "text" not in result.train_index.read_text(encoding="utf-8")
    assert result.manifest.total_records == 7


def test_preparation_manifest_hashes_exact_generated_indices(tmp_path) -> None:
    result = _prepare(_source_fixture(tmp_path), tmp_path / "prepared")

    paths = {
        "train": result.train_index,
        "validation": result.validation_index,
        "test": result.test_index,
    }
    for split in result.manifest.splits:
        digest = hashlib.sha256(paths[split.name].read_bytes()).hexdigest()
        assert split.index_sha256 == digest


def test_preparation_audit_records_source_overlap_and_proxy_limitations(tmp_path) -> None:
    result = _prepare(_source_fixture(tmp_path), tmp_path / "prepared")
    audit = json.loads(result.audit_report.read_text(encoding="utf-8"))

    assert audit["source_train_validation_speaker_overlap"] == 3
    assert audit["source_test_development_speaker_overlap"] == 0
    assert audit["derived_speaker_disjoint"] is True
    assert audit["evidence_scope"] == "engineering_proxy"
    assert audit["limitations"] == [
        "adult speech is not target-user child speech",
        "dataset phonemes are not therapist pronunciation ratings",
    ]


def test_preparation_is_byte_deterministic_for_same_source_and_seed(tmp_path) -> None:
    source = _source_fixture(tmp_path)
    first = _prepare(source, tmp_path / "first")
    second = _prepare(source, tmp_path / "second")

    assert first.manifest.digest() == second.manifest.digest()
    assert first.train_index.read_bytes() == second.train_index.read_bytes()
    assert first.validation_index.read_bytes() == second.validation_index.read_bytes()
    assert first.test_index.read_bytes() == second.test_index.read_bytes()


def test_preparation_rejects_missing_phoneme_labels(tmp_path) -> None:
    source = _source_fixture(tmp_path)
    _write_csv(
        source / "train.csv",
        [{"rel_path": "wavs/a/1.wav", "text": "one", "phonemes": "", "speaker": "a"}],
    )

    with pytest.raises(ValueError, match="non-empty phonemes"):
        _prepare(source, tmp_path / "prepared")


def test_preparation_rejects_test_speaker_leakage(tmp_path) -> None:
    source = _source_fixture(tmp_path)
    _write_csv(
        source / "test.csv",
        [{"rel_path": "wavs/a/test.wav", "text": "seven", "phonemes": "a", "speaker": "a"}],
    )

    with pytest.raises(ValueError, match="test speakers overlap"):
        _prepare(source, tmp_path / "prepared")


def test_preparation_rejects_duplicate_audio_paths(tmp_path) -> None:
    source = _source_fixture(tmp_path)
    _write_csv(
        source / "val.csv",
        [
            {
                "rel_path": "wavs/a/1.wav",
                "text": "duplicate",
                "phonemes": "a",
                "speaker": "a",
            }
        ],
    )

    with pytest.raises(ValueError, match="rel_path values must be unique"):
        _prepare(source, tmp_path / "prepared")

