"""Privacy-safe, leakage-proof frozen corpus indexes for local Tamil training."""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    field_validator,
    model_validator,
)

SplitName = Literal["train", "validation", "test"]
_SPLIT_ORDER: tuple[SplitName, ...] = ("train", "validation", "test")
_APPROVED_LICENSES = frozenset(
    {"Apache-2.0", "CC-BY-2.0", "CC-BY-4.0", "CC-BY-SA-4.0", "CC0-1.0", "MIT"}
)


class CorpusRecord(BaseModel):
    """Sensitive local index input; aggregate outputs never contain these identifiers."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    utterance_id: str = Field(min_length=1)
    speaker_id: str = Field(min_length=1)
    audio_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    transcript_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sample_rate_hz: Literal[16000]
    duration_ms: int = Field(gt=0)

    @field_validator("utterance_id", "speaker_id")
    @classmethod
    def normalize_identifier(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("record identifiers must be non-empty")
        return normalized


class CorpusSource(BaseModel):
    """Audited corpus snapshot; revision is the locally verified archive digest."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    dataset_id: str = Field(min_length=1)
    revision: str = Field(pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
    revision_basis: Literal["archive_sha256", "source_snapshot_sha256"]
    source_url: HttpUrl
    license_spdx: str = Field(min_length=1)
    population: Literal["adult_tamil_proxy", "general_child_proxy", "target_user_child"]
    local_processing_only: Literal[True]

    @field_validator("license_spdx")
    @classmethod
    def validate_license(cls, license_spdx: str) -> str:
        if license_spdx not in _APPROVED_LICENSES:
            raise ValueError("corpus license is not approved")
        return license_spdx

    @model_validator(mode="after")
    def reject_unlabelled_target_child_source(self) -> CorpusSource:
        if self.population == "target_user_child":
            raise ValueError("target_user_child requires the therapist-labelled manifest path")
        return self


class FrozenCorpusSplit(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: SplitName
    record_count: int = Field(gt=0)
    speaker_count: int = Field(gt=0)
    index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class FrozenCorpusIndex(BaseModel):
    """Aggregate, hash-linked index safe to store as engineering evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    source: CorpusSource
    splits: tuple[FrozenCorpusSplit, FrozenCorpusSplit, FrozenCorpusSplit]
    record_count: int = Field(gt=0)
    speaker_count: int = Field(gt=0)
    evidence_scope: Literal["engineering_proxy"] = "engineering_proxy"
    contains_identifiers: Literal[False] = False
    contains_transcripts: Literal[False] = False
    contains_paths: Literal[False] = False

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        result = self.model_dump(mode="json")
        result["corpus_index_sha256"] = self.digest()
        return result


def _split_digest(records: Sequence[CorpusRecord]) -> str:
    rows = sorted(
        (
            record.utterance_id,
            record.speaker_id,
            record.audio_sha256,
            record.transcript_sha256,
            record.sample_rate_hz,
            record.duration_ms,
        )
        for record in records
    )
    canonical = json.dumps(rows, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def freeze_corpus_index(
    records: Sequence[CorpusRecord],
    speaker_assignments: Mapping[str, str],
    source: CorpusSource,
) -> FrozenCorpusIndex:
    """Freeze aggregate split evidence after rejecting identity and audio leakage."""

    if not records:
        raise ValueError("at least one corpus record is required")
    if source.revision_basis != "archive_sha256":
        raise ValueError("freeze requires a locally verified archive_sha256 revision")
    utterance_counts = Counter(record.utterance_id for record in records)
    if any(count > 1 for count in utterance_counts.values()):
        raise ValueError("utterance identifiers must be unique")
    audio_counts = Counter(record.audio_sha256 for record in records)
    if any(count > 1 for count in audio_counts.values()):
        raise ValueError("audio digest values must be unique across the corpus")

    speakers = {record.speaker_id for record in records}
    missing = sorted(speakers - set(speaker_assignments))
    if missing:
        raise ValueError("missing split assignment for one or more speakers")
    extra = sorted(set(speaker_assignments) - speakers)
    if extra:
        raise ValueError("split assignments contain unknown speakers")
    invalid = sorted(set(speaker_assignments.values()) - set(_SPLIT_ORDER))
    if invalid:
        raise ValueError("split assignment must be train, validation, or test")
    if set(speaker_assignments.values()) != set(_SPLIT_ORDER):
        raise ValueError("corpus index requires train, validation, and test splits")

    frozen_splits: list[FrozenCorpusSplit] = []
    for split_name in _SPLIT_ORDER:
        split_records = tuple(
            record
            for record in records
            if speaker_assignments[record.speaker_id] == split_name
        )
        split_speakers = {record.speaker_id for record in split_records}
        frozen_splits.append(
            FrozenCorpusSplit(
                name=split_name,
                record_count=len(split_records),
                speaker_count=len(split_speakers),
                index_sha256=_split_digest(split_records),
            )
        )
    split_tuple = tuple(frozen_splits)
    assert len(split_tuple) == 3
    return FrozenCorpusIndex(
        source=source,
        splits=(split_tuple[0], split_tuple[1], split_tuple[2]),
        record_count=len(records),
        speaker_count=len(speakers),
    )


def write_frozen_corpus_index(path: Path, index: FrozenCorpusIndex) -> None:
    """Write aggregate index evidence without overwriting an earlier frozen result."""

    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(index.as_dict(), output, ensure_ascii=False, indent=2)
        output.write("\n")
