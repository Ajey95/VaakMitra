"""Corpus provenance and split validation (DTW-001/002/007, DATA-001/007/008/010/011)."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class CorpusManifestError(ValueError):
    """Raised when a corpus cannot enter a governed build stage."""


class SourceEntry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    homepage: str = Field(pattern=r"^https://")
    licence_id: str = Field(min_length=1)
    licence_url: str = Field(pattern=r"^https://")
    licence_status: Literal["verified", "unknown", "incompatible"]
    terms_checked_at: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    enabled: bool
    intended_uses: tuple[Literal["target", "other", "confusable", "canary"], ...] = ()


class SourceRegistry(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["vaakmitra-source-registry-1"]
    sources: tuple[SourceEntry, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_sources(self) -> "SourceRegistry":
        source_ids = [source.source_id for source in self.sources]
        if len(set(source_ids)) != len(source_ids):
            raise ValueError("source_id must be unique")
        return self

    @classmethod
    def from_json(cls, path: Path | str) -> "SourceRegistry":
        with Path(path).open("r", encoding="utf-8") as source:
            return cls.model_validate(json.load(source))

    def require_ingestible(self, source_id: str) -> SourceEntry:
        source = next((item for item in self.sources if item.source_id == source_id), None)
        if source is None:
            raise CorpusManifestError(f"source_unknown:{source_id}")
        if source.licence_status == "incompatible":
            raise CorpusManifestError(f"licence_incompatible:{source_id}")
        if source.licence_status != "verified":
            raise CorpusManifestError(f"licence_not_verified:{source_id}")
        if not source.enabled:
            raise CorpusManifestError(f"source_disabled:{source_id}")
        return source


class CorpusRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["vaakmitra-corpus-record-1"]
    sample_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    original_id: str = Field(min_length=1)
    speaker_pseudonym: str = Field(min_length=1)
    canonical_word_id: str | None = Field(default=None, pattern=r"^TA_WORD_\d{4}$")
    label_kind: Literal["target", "other", "confusable", "noise"]
    transcript: str | None = None
    audio_path: str = Field(min_length=1)
    audio_sha256: str
    duration_seconds: float = Field(gt=0.0)
    split: Literal["train", "calibration", "evaluation", "reference", "canary"]
    licence_id: str = Field(min_length=1)
    provenance_kind: Literal["original", "segmented", "augmented"] = "original"
    parent_id: str | None = None
    transformation: str | None = None

    @field_validator("audio_sha256")
    @classmethod
    def valid_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("audio_sha256 must be lowercase hexadecimal SHA-256")
        return normalized

    @field_validator("audio_path")
    @classmethod
    def relative_audio_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("audio_path must be a safe relative path")
        return value

    @model_validator(mode="after")
    def validate_label_and_derivation(self) -> "CorpusRecord":
        if self.label_kind == "target" and self.canonical_word_id is None:
            raise ValueError("target records require canonical_word_id")
        if self.provenance_kind != "original" and (not self.parent_id or not self.transformation):
            raise ValueError("derived records require parent_id and transformation")
        if self.provenance_kind == "original" and (self.parent_id or self.transformation):
            raise ValueError("original records cannot have derivation fields")
        return self


class CorpusSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    records: int
    speakers: int
    target_records: int
    other_records: int
    split_counts: dict[str, int]


def validate_jsonl_manifest(
    manifest_path: Path | str,
    *,
    audio_root: Path | str | None = None,
) -> CorpusSummary:
    """Validate records, integrity, uniqueness, and speaker-disjoint splits."""
    manifest = Path(manifest_path)
    records: list[CorpusRecord] = []
    try:
        with manifest.open("r", encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    records.append(CorpusRecord.model_validate(json.loads(line)))
                except Exception as exc:
                    raise CorpusManifestError(f"record_invalid:{line_number}") from exc
    except OSError as exc:
        raise CorpusManifestError("manifest_unavailable") from exc

    if not records:
        raise CorpusManifestError("manifest_empty")
    sample_ids = [record.sample_id for record in records]
    if len(set(sample_ids)) != len(sample_ids):
        raise CorpusManifestError("sample_id_duplicate")
    source_original_ids = [(record.source_id, record.original_id) for record in records]
    if len(set(source_original_ids)) != len(source_original_ids):
        raise CorpusManifestError("source_original_duplicate")

    speaker_splits: dict[str, set[str]] = defaultdict(set)
    for record in records:
        speaker_splits[record.speaker_pseudonym].add(record.split)
    if any(len(splits) > 1 for splits in speaker_splits.values()):
        raise CorpusManifestError("speaker_split_leakage")

    if audio_root is not None:
        root = Path(audio_root).resolve()
        for record in records:
            path = (root / record.audio_path).resolve()
            try:
                path.relative_to(root)
            except ValueError as exc:
                raise CorpusManifestError("audio_path_outside_root") from exc
            if not path.is_file():
                raise CorpusManifestError(f"audio_unavailable:{record.sample_id}")
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if digest != record.audio_sha256:
                raise CorpusManifestError(f"audio_integrity_mismatch:{record.sample_id}")

    split_counts: dict[str, int] = defaultdict(int)
    for record in records:
        split_counts[record.split] += 1
    return CorpusSummary(
        records=len(records),
        speakers=len(speaker_splits),
        target_records=sum(record.label_kind == "target" for record in records),
        other_records=sum(record.label_kind != "target" for record in records),
        split_counts=dict(sorted(split_counts.items())),
    )
