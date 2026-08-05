"""Deterministic, explicitly provisional Tamil acoustic inventory consensus."""

from __future__ import annotations

import hashlib
import json
import unicodedata
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_BLANK: Literal["<blank>"] = "<blank>"


def _normalized_token(token: str) -> str:
    normalized = unicodedata.normalize("NFC", token.strip())
    if not normalized:
        raise ValueError("phoneme tokens must be non-empty")
    return normalized


class InventorySource(BaseModel):
    """One immutable source inventory; the revision binds the source snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str = Field(min_length=1)
    revision: str = Field(pattern=r"^[0-9a-f]{40}(?:[0-9a-f]{24})?$")
    source_scope: Literal[
        "published_inventory", "transliterator", "exercise_lexicon", "corpus_observation"
    ]
    segments: tuple[str, ...] = Field(min_length=1)

    @field_validator("source_id")
    @classmethod
    def normalize_source_id(cls, source_id: str) -> str:
        normalized = source_id.strip()
        if not normalized:
            raise ValueError("source_id must be non-empty")
        return normalized

    @field_validator("segments")
    @classmethod
    def normalize_segments(cls, segments: tuple[str, ...]) -> tuple[str, ...]:
        normalized = tuple(_normalized_token(token) for token in segments)
        if _BLANK in normalized:
            raise ValueError("source segments cannot contain the blank token")
        if len(normalized) != len(set(normalized)):
            raise ValueError("source segments must be unique")
        return tuple(sorted(normalized))


class AllophoneRule(BaseModel):
    """Explicit acoustic-only mapping with human-readable provenance."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source: str = Field(min_length=1)
    canonical: str = Field(min_length=1)
    provenance: str = Field(min_length=1)

    @field_validator("source", "canonical", "provenance")
    @classmethod
    def normalize_text(cls, value: str) -> str:
        return _normalized_token(value)


class TokenProvenance(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    source_ids: tuple[str, ...]
    observed_in_training_text: bool


class InventoryConflict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    token: str
    present_in: tuple[str, ...]
    missing_from: tuple[str, ...]
    resolution: Literal["extended_pending_review"] = "extended_pending_review"


class CandidateInventory(BaseModel):
    """Candidate model vocabulary that cannot be mistaken for expert approval."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    inventory_version: str = Field(min_length=1)
    blank_token: Literal["<blank>"] = _BLANK
    tokens: tuple[str, ...] = Field(min_length=2)
    core_tokens: tuple[str, ...]
    extended_tokens: tuple[str, ...]
    sources: tuple[InventorySource, ...] = Field(min_length=1)
    token_provenance: tuple[TokenProvenance, ...] = Field(min_length=1)
    allophones: tuple[AllophoneRule, ...]
    conflicts: tuple[InventoryConflict, ...]
    expert_approved: Literal[False] = False
    production_ready: Literal[False] = False
    evidence_scope: Literal["provisional_research_inventory"] = (
        "provisional_research_inventory"
    )

    @model_validator(mode="after")
    def validate_partition(self) -> Self:
        if self.tokens[0] != self.blank_token:
            raise ValueError("blank token must be index zero")
        nonblank = set(self.tokens[1:])
        if set(self.core_tokens).intersection(self.extended_tokens):
            raise ValueError("core and extended tokens must be disjoint")
        if set(self.core_tokens).union(self.extended_tokens) != nonblank:
            raise ValueError("core and extended tokens must partition the vocabulary")
        return self

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        result = self.model_dump(mode="json")
        result["inventory_digest"] = self.digest()
        return result


class InventoryCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    total_units: int = Field(ge=0)
    known_units: int = Field(ge=0)
    unknown_units: tuple[str, ...]
    coverage: float = Field(ge=0.0, le=1.0)


def load_inventory_sources(path: str | Path) -> tuple[InventorySource, ...]:
    """Load a pinned inventory-source catalog and reject duplicate identifiers."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("sources"), list):
        raise TypeError("inventory source catalog must contain a sources array")
    sources = tuple(InventorySource.model_validate(item) for item in payload["sources"])
    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("inventory source identifiers must be unique")
    return sources


def build_candidate_inventory(
    *,
    sources: Sequence[InventorySource],
    observed_units: Sequence[str],
    allophones: Sequence[AllophoneRule],
    version: str,
) -> CandidateInventory:
    """Merge published sources and observations without hiding disagreements."""

    if not sources:
        raise ValueError("at least one inventory source is required")
    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError("inventory source identifiers must be unique")
    normalized_observed = tuple(_normalized_token(token) for token in observed_units)
    if not normalized_observed:
        raise ValueError("observed units must be non-empty")
    if _BLANK in normalized_observed:
        raise ValueError("observed units cannot contain the blank token")
    normalized_version = version.strip()
    if not normalized_version:
        raise ValueError("inventory version must be non-empty")

    ordered_sources = tuple(sorted(sources, key=lambda item: item.source_id))
    source_sets = {source.source_id: set(source.segments) for source in ordered_sources}
    observed_set = set(normalized_observed)
    vocabulary = set().union(*source_sets.values(), observed_set)
    core = set.intersection(*source_sets.values())
    extended = vocabulary - core

    ordered_allophones = tuple(
        sorted(allophones, key=lambda item: (item.source, item.canonical, item.provenance))
    )
    allophone_sources: set[str] = set()
    for rule in ordered_allophones:
        if rule.source == _BLANK or rule.canonical == _BLANK:
            raise ValueError("allophone rules cannot contain the blank token")
        if rule.source in allophone_sources:
            raise ValueError("allophone sources must be unique")
        if rule.canonical not in vocabulary:
            raise ValueError("canonical allophone target must exist in the inventory")
        allophone_sources.add(rule.source)

    provenance = tuple(
        TokenProvenance(
            token=token,
            source_ids=tuple(
                source.source_id for source in ordered_sources if token in source_sets[source.source_id]
            ),
            observed_in_training_text=token in observed_set,
        )
        for token in sorted(vocabulary)
    )
    conflicts = tuple(
        InventoryConflict(
            token=token,
            present_in=tuple(
                source.source_id for source in ordered_sources if token in source_sets[source.source_id]
            ),
            missing_from=tuple(
                source.source_id for source in ordered_sources if token not in source_sets[source.source_id]
            ),
        )
        for token in sorted(extended)
        if any(token in segments for segments in source_sets.values())
    )

    return CandidateInventory(
        inventory_version=normalized_version,
        tokens=(_BLANK, *sorted(vocabulary)),
        core_tokens=tuple(sorted(core)),
        extended_tokens=tuple(sorted(extended)),
        sources=ordered_sources,
        token_provenance=provenance,
        allophones=ordered_allophones,
        conflicts=conflicts,
    )


def map_acoustic_units(
    inventory: CandidateInventory, units: Sequence[str]
) -> tuple[str, ...]:
    """Apply only declared allophone mappings and fail on unresolved phones."""

    known = set(inventory.tokens[1:])
    mappings = {rule.source: rule.canonical for rule in inventory.allophones}
    mapped: list[str] = []
    for raw_unit in units:
        unit = _normalized_token(raw_unit)
        canonical = mappings.get(unit, unit)
        if canonical not in known:
            raise ValueError(f"unresolved phoneme: {unit}")
        mapped.append(canonical)
    return tuple(mapped)


def evaluate_inventory_coverage(
    inventory: CandidateInventory, sequences: Sequence[Sequence[str]]
) -> InventoryCoverage:
    """Report unknown units while counting explicit allophones as covered."""

    known = set(inventory.tokens[1:])
    mappings = {rule.source: rule.canonical for rule in inventory.allophones}
    total = 0
    covered = 0
    unknown: set[str] = set()
    for sequence in sequences:
        for raw_unit in sequence:
            total += 1
            unit = _normalized_token(raw_unit)
            if mappings.get(unit, unit) in known:
                covered += 1
            else:
                unknown.add(unit)
    return InventoryCoverage(
        total_units=total,
        known_units=covered,
        unknown_units=tuple(sorted(unknown)),
        coverage=covered / total if total else 0.0,
    )
