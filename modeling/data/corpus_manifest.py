"""Immutable, licence-aware manifests for local proxy speech corpora."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_APPROVED_LICENCES = frozenset(
    {
        "Apache-2.0",
        "CC-BY-2.0",
        "CC-BY-4.0",
        "CC-BY-SA-4.0",
        "CC0-1.0",
        "MIT",
    }
)
_IMMUTABLE_REVISION = re.compile(r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")


class CorpusSplit(BaseModel):
    """Speaker-level split metadata without paths, text, or voice-derived data."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: Literal["train", "validation", "test"]
    speakers: tuple[str, ...] = Field(min_length=1)
    record_count: int = Field(gt=0)
    index_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("speakers")
    @classmethod
    def validate_speakers(cls, speakers: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(speaker.strip() for speaker in speakers)
        if any(not speaker for speaker in normalized):
            raise ValueError("speaker identifiers must be non-empty")
        if len(normalized) != len(set(normalized)):
            raise ValueError("speaker identifiers must be unique within a split")
        return normalized


class CorpusManifest(BaseModel):
    """Provenance gate for a frozen local corpus used by Member 2."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    dataset_id: str = Field(min_length=1)
    revision: str
    source_url: str
    license_spdx: str
    population: Literal["adult_tamil_proxy", "general_child_proxy", "target_user_child"]
    label_origin: Literal[
        "dataset_supplied_phonemes",
        "rule_based_proxy",
        "therapist_adjudicated",
    ]
    evidence_scope: Literal["engineering_proxy", "target_user_validation"]
    local_processing_only: bool
    splits: tuple[CorpusSplit, ...]

    @field_validator("revision")
    @classmethod
    def validate_revision(cls, revision: str) -> str:
        if not _IMMUTABLE_REVISION.fullmatch(revision):
            raise ValueError("revision must be an immutable revision hash")
        return revision

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, source_url: str) -> str:
        if not source_url.startswith("https://"):
            raise ValueError("source_url must use https")
        return source_url

    @field_validator("license_spdx")
    @classmethod
    def validate_licence(cls, licence: str) -> str:
        if licence not in _APPROVED_LICENCES:
            raise ValueError("dataset must declare an approved SPDX licence")
        return licence

    @model_validator(mode="after")
    def validate_evidence_contract(self) -> Self:
        if not self.local_processing_only:
            raise ValueError("local_processing_only must be true")
        if {split.name for split in self.splits} != {"train", "validation", "test"}:
            raise ValueError("manifest must contain train, validation, and test splits")

        seen_speakers: set[str] = set()
        for split in self.splits:
            overlap = seen_speakers.intersection(split.speakers)
            if overlap:
                raise ValueError("corpus splits must be speaker-disjoint")
            seen_speakers.update(split.speakers)

        if self.evidence_scope == "target_user_validation" and (
            self.population != "target_user_child"
            or self.label_origin != "therapist_adjudicated"
        ):
            raise ValueError(
                "target-user evidence requires target_user_child population and "
                "therapist_adjudicated labels"
            )
        if self.population == "target_user_child" and self.label_origin != "therapist_adjudicated":
            raise ValueError("target_user_child data requires therapist_adjudicated labels")
        return self

    @property
    def total_records(self) -> int:
        return sum(split.record_count for split in self.splits)

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    @classmethod
    def from_json(cls, path: str | Path) -> CorpusManifest:
        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))
