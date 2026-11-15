"""Immutable, resumable encoder-embedding shards for governed speech data."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator


class EmbeddingShardError(RuntimeError):
    """A shard is malformed or incompatible with the requested build."""


class EmbeddingRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    sample_id: str = Field(min_length=1)
    canonical_word_id: str | None = Field(default=None, pattern=r"^TA_WORD_\d{4}$")
    speaker_pseudonym: str = Field(min_length=1)
    split: Literal["train", "calibration", "evaluation", "reference", "canary"]
    embedding_key: str = Field(pattern=r"^embedding__\d{6}$")
    frames: int = Field(gt=0)
    dimensions: int = Field(gt=0)


class EmbeddingShardManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    schema_version: Literal["vaakmitra-embedding-shard-1"]
    shard_id: str = Field(min_length=1)
    model_hash: str
    vocabulary_hash: str
    source_manifest_hash: str
    records: tuple[EmbeddingRecord, ...] = Field(min_length=1)

    @field_validator("model_hash", "vocabulary_hash", "source_manifest_hash")
    @classmethod
    def valid_hash(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("artifact hashes must be SHA-256")
        return normalized

    @model_validator(mode="after")
    def unique_samples(self) -> "EmbeddingShardManifest":
        sample_ids = [record.sample_id for record in self.records]
        if len(set(sample_ids)) != len(sample_ids):
            raise ValueError("sample IDs must be unique within a shard")
        dimensions = {record.dimensions for record in self.records}
        if len(dimensions) != 1:
            raise ValueError("all embeddings in a shard must share dimensions")
        return self


@dataclass(frozen=True)
class EmbeddingItem:
    sample_id: str
    canonical_word_id: str | None
    speaker_pseudonym: str
    split: str
    embedding: np.ndarray


@dataclass(frozen=True)
class LoadedEmbeddingShard:
    manifest: EmbeddingShardManifest
    items: tuple[EmbeddingItem, ...]
    manifest_sha256: str


def _canonical_manifest(manifest: EmbeddingShardManifest) -> str:
    return json.dumps(
        manifest.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _validate_embedding(value: np.ndarray) -> np.ndarray:
    embedding = np.asarray(value, dtype=np.float32)
    if embedding.ndim != 2 or embedding.shape[0] == 0 or embedding.shape[1] == 0:
        raise EmbeddingShardError("embedding_invalid:expected_frames_by_dimensions")
    if not np.isfinite(embedding).all():
        raise EmbeddingShardError("embedding_invalid:non_finite")
    return embedding


def write_embedding_shard(
    path: Path | str,
    *,
    shard_id: str,
    items: list[EmbeddingItem] | tuple[EmbeddingItem, ...],
    model_hash: str,
    vocabulary_hash: str,
    source_manifest_hash: str,
) -> str:
    destination = Path(path)
    if destination.exists():
        raise FileExistsError(destination)
    if not items:
        raise EmbeddingShardError("shard_empty")

    arrays: dict[str, np.ndarray] = {}
    records: list[EmbeddingRecord] = []
    for index, item in enumerate(items):
        embedding = _validate_embedding(item.embedding)
        key = f"embedding__{index:06d}"
        arrays[key] = embedding
        try:
            records.append(
                EmbeddingRecord(
                    sample_id=item.sample_id,
                    canonical_word_id=item.canonical_word_id,
                    speaker_pseudonym=item.speaker_pseudonym,
                    split=item.split,
                    embedding_key=key,
                    frames=embedding.shape[0],
                    dimensions=embedding.shape[1],
                )
            )
        except ValidationError as exc:
            raise EmbeddingShardError("embedding_metadata_invalid") from exc

    try:
        manifest = EmbeddingShardManifest(
            schema_version="vaakmitra-embedding-shard-1",
            shard_id=shard_id,
            model_hash=model_hash,
            vocabulary_hash=vocabulary_hash,
            source_manifest_hash=source_manifest_hash,
            records=tuple(records),
        )
    except ValidationError as exc:
        raise EmbeddingShardError("embedding_manifest_invalid") from exc
    manifest_json = _canonical_manifest(manifest)
    manifest_sha256 = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f"{destination.name}.part")
    if partial.exists():
        raise FileExistsError(partial)
    try:
        with partial.open("xb") as sink:
            np.savez_compressed(
                sink,
                manifest=np.asarray(manifest_json),
                manifest_sha256=np.asarray(manifest_sha256),
                **arrays,
            )
        partial.replace(destination)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise
    return manifest_sha256


def load_embedding_shard(
    path: Path | str,
    *,
    model_hash: str,
    vocabulary_hash: str,
    source_manifest_hash: str,
) -> LoadedEmbeddingShard:
    try:
        with np.load(Path(path), allow_pickle=False) as archive:
            manifest_json = str(archive["manifest"].item())
            stored_manifest_hash = str(archive["manifest_sha256"].item())
            actual_manifest_hash = hashlib.sha256(manifest_json.encode("utf-8")).hexdigest()
            if stored_manifest_hash != actual_manifest_hash:
                raise EmbeddingShardError("manifest_integrity_mismatch")
            manifest = EmbeddingShardManifest.model_validate_json(manifest_json)
            expectations = {
                "model_hash": model_hash,
                "vocabulary_hash": vocabulary_hash,
                "source_manifest_hash": source_manifest_hash,
            }
            for name, expected in expectations.items():
                if getattr(manifest, name) != expected:
                    raise EmbeddingShardError(f"{name}_mismatch")
            items = []
            for record in manifest.records:
                embedding = _validate_embedding(archive[record.embedding_key])
                if embedding.shape != (record.frames, record.dimensions):
                    raise EmbeddingShardError("embedding_shape_mismatch")
                items.append(
                    EmbeddingItem(
                        sample_id=record.sample_id,
                        canonical_word_id=record.canonical_word_id,
                        speaker_pseudonym=record.speaker_pseudonym,
                        split=record.split,
                        embedding=embedding.copy(),
                    )
                )
    except EmbeddingShardError:
        raise
    except Exception as exc:
        raise EmbeddingShardError("shard_payload_invalid") from exc
    return LoadedEmbeddingShard(manifest, tuple(items), actual_manifest_hash)


def completed_sample_ids(
    directory: Path | str,
    *,
    model_hash: str,
    vocabulary_hash: str,
    source_manifest_hash: str,
) -> set[str]:
    completed: set[str] = set()
    for path in sorted(Path(directory).glob("shard-*.npz")):
        shard = load_embedding_shard(
            path,
            model_hash=model_hash,
            vocabulary_hash=vocabulary_hash,
            source_manifest_hash=source_manifest_hash,
        )
        overlap = completed.intersection(item.sample_id for item in shard.items)
        if overlap:
            raise EmbeddingShardError("sample_id_repeated_across_shards")
        completed.update(item.sample_id for item in shard.items)
    return completed
