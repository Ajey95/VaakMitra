"""Governed corpus manifests for DTW-001/002/007 and DATA-001/007/008/010/011."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.vaakmitra_word.corpus import (
    CorpusManifestError,
    CorpusRecord,
    SourceRegistry,
    validate_jsonl_manifest,
)


def test_record_requires_traceable_source_speaker_split_and_checksum() -> None:
    """Removing provenance fields must make a training record invalid."""
    payload = _record()
    for field in (
        "source_revision",
        "original_id",
        "speaker_pseudonym",
        "audio_sha256",
        "split",
        "licence_id",
    ):
        broken = dict(payload)
        del broken[field]
        with pytest.raises(ValidationError):
            CorpusRecord.model_validate(broken)


def test_unknown_or_incompatible_licence_blocks_ingestion() -> None:
    """A source without reusable terms must never enter a build manifest."""
    registry = SourceRegistry.model_validate(
        {
            "schema_version": "vaakmitra-source-registry-1",
            "sources": [
                _source("good", "CC-BY-4.0", "verified"),
                _source("unknown", "LicenseRef-Unknown", "unknown"),
                _source("restricted", "CC-BY-NC-ND-4.0", "incompatible"),
            ],
        }
    )

    assert registry.require_ingestible("good").licence_id == "CC-BY-4.0"
    with pytest.raises(CorpusManifestError, match="licence_not_verified"):
        registry.require_ingestible("unknown")
    with pytest.raises(CorpusManifestError, match="licence_incompatible"):
        registry.require_ingestible("restricted")


def test_derived_record_requires_parent_and_transformation_provenance() -> None:
    """A segmented or augmented clip must always identify how it was derived."""
    with pytest.raises(ValidationError, match="derived records require parent_id and transformation"):
        CorpusRecord.model_validate({**_record(), "provenance_kind": "segmented"})


def test_manifest_rejects_speaker_leakage_across_splits(tmp_path: Path) -> None:
    """A speaker appearing in train and evaluation would invalidate reported metrics."""
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(
            (
                json.dumps(_record(sample_id="one", split="train")),
                json.dumps(_record(sample_id="two", split="evaluation")),
            )
        ),
        encoding="utf-8",
    )

    with pytest.raises(CorpusManifestError, match="speaker_split_leakage"):
        validate_jsonl_manifest(manifest)


def test_manifest_verifies_audio_hash_when_root_is_supplied(tmp_path: Path) -> None:
    """A changed audio file must invalidate its manifest before training."""
    audio = tmp_path / "clip.wav"
    audio.write_bytes(b"expected")
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        json.dumps(
            {
                **_record(),
                "audio_path": "clip.wav",
                "audio_sha256": hashlib.sha256(b"different").hexdigest(),
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(CorpusManifestError, match="audio_integrity_mismatch"):
        validate_jsonl_manifest(manifest, audio_root=tmp_path)


def test_valid_manifest_returns_deterministic_summary(tmp_path: Path) -> None:
    """The validator must expose real counts used by downstream release gates."""
    first = {**_record(sample_id="one"), "speaker_pseudonym": "speaker-a"}
    second = {
        **_record(sample_id="two", canonical_word_id=None),
        "speaker_pseudonym": "speaker-b",
        "label_kind": "other",
    }
    manifest = tmp_path / "manifest.jsonl"
    manifest.write_text(
        "\n".join(json.dumps(item) for item in (first, second)), encoding="utf-8"
    )

    summary = validate_jsonl_manifest(manifest)

    assert summary.records == 2
    assert summary.speakers == 2
    assert summary.target_records == 1
    assert summary.other_records == 1


def _record(
    *,
    sample_id: str = "sample-one",
    split: str = "train",
    canonical_word_id: str | None = "TA_WORD_0001",
) -> dict[str, object]:
    return {
        "schema_version": "vaakmitra-corpus-record-1",
        "sample_id": sample_id,
        "source_id": "mlcommons-mswc",
        "source_revision": "0bc9df68e92fd6bb54176bf7eb29e2b9e97cb218",
        "original_id": sample_id,
        "speaker_pseudonym": "speaker-a",
        "canonical_word_id": canonical_word_id,
        "label_kind": "target" if canonical_word_id else "other",
        "transcript": "அம்மா" if canonical_word_id else "வேறு",
        "audio_path": "audio/sample.opus",
        "audio_sha256": "a" * 64,
        "duration_seconds": 1.0,
        "split": split,
        "licence_id": "CC-BY-4.0",
        "provenance_kind": "original",
        "parent_id": None,
        "transformation": None,
    }


def _source(source_id: str, licence_id: str, status: str) -> dict[str, object]:
    return {
        "source_id": source_id,
        "source_revision": "revision-one",
        "homepage": "https://example.invalid/dataset",
        "licence_id": licence_id,
        "licence_url": "https://example.invalid/license",
        "licence_status": status,
        "terms_checked_at": "2026-09-06",
        "enabled": True,
    }
