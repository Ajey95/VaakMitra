"""Balanced adult reference selection (DEC-017, DTW-005/007, DATA-010/012)."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import json
from pathlib import Path

import numpy as np

from .dtw import ReferenceBank, ReferenceEmbedding


REFERENCE_PREFIX = "reference__"
REFERENCE_META_PREFIX = "reference_meta__"


class ReferenceBankBuildError(RuntimeError):
    """A reference bank cannot be built without weakening its coverage gates."""


@dataclass(frozen=True)
class ReferenceCandidate:
    sample_id: str
    word_id: str
    speaker_pseudonym: str
    source_id: str
    quality_score: float
    approved: bool
    embedding: np.ndarray


@dataclass(frozen=True)
class ReferenceSelection:
    active: bool
    selected: tuple[ReferenceCandidate, ...]
    reasons: tuple[str, ...]


def select_balanced_references(
    candidates: list[ReferenceCandidate],
    *,
    min_references: int = 32,
    max_references: int = 64,
    min_speakers: int = 8,
    max_per_speaker: int = 4,
) -> ReferenceSelection:
    """Select a deterministic, speaker-balanced bank or fail the word closed."""
    if not 1 <= min_references <= max_references:
        raise ValueError("reference bounds are invalid")
    if min_speakers < 1 or max_per_speaker < 1:
        raise ValueError("speaker bounds are invalid")

    grouped: dict[str, list[ReferenceCandidate]] = defaultdict(list)
    seen_samples: set[str] = set()
    for candidate in sorted(
        candidates,
        key=lambda item: (
            item.speaker_pseudonym,
            -item.quality_score,
            item.source_id,
            item.sample_id,
        ),
    ):
        embedding = np.asarray(candidate.embedding)
        if (
            not candidate.approved
            or not candidate.sample_id
            or candidate.sample_id in seen_samples
            or not candidate.speaker_pseudonym
            or embedding.ndim != 2
            or embedding.size == 0
            or not np.isfinite(embedding).all()
        ):
            continue
        seen_samples.add(candidate.sample_id)
        grouped[candidate.speaker_pseudonym].append(candidate)

    reasons: list[str] = []
    if len(grouped) < min_speakers:
        reasons.append("insufficient_speakers")
    if reasons:
        return ReferenceSelection(False, (), tuple(reasons))

    selected: list[ReferenceCandidate] = []
    speakers = sorted(grouped)
    for rank in range(max_per_speaker):
        for speaker in speakers:
            if len(selected) >= max_references:
                break
            speaker_items = grouped[speaker]
            if rank < len(speaker_items):
                selected.append(speaker_items[rank])
        if len(selected) >= max_references:
            break

    if len(selected) < min_references:
        return ReferenceSelection(False, (), ("insufficient_references",))
    return ReferenceSelection(True, tuple(selected), ())


def save_reference_bank_artifact(
    path: Path | str,
    *,
    selections: dict[str, ReferenceSelection],
    version: str,
    model_hash: str,
    vocabulary_hash: str,
    dataset_manifest_hash: str,
) -> None:
    """Serialize only active selections with per-reference speaker provenance."""
    destination = Path(path)
    if destination.exists():
        raise FileExistsError(destination)
    active = {word_id: value for word_id, value in selections.items() if value.active}
    if not active:
        raise ReferenceBankBuildError("no_active_words")
    arrays: dict[str, np.ndarray] = {
        "version": np.asarray(version),
        "model_hash": np.asarray(model_hash),
        "vocabulary_hash": np.asarray(vocabulary_hash),
        "dataset_manifest_hash": np.asarray(dataset_manifest_hash),
    }
    for word_id in sorted(active):
        for index, candidate in enumerate(active[word_id].selected):
            suffix = f"{word_id}__{index:04d}"
            arrays[f"{REFERENCE_PREFIX}{suffix}"] = np.asarray(candidate.embedding, dtype=np.float32)
            arrays[f"{REFERENCE_META_PREFIX}{suffix}"] = np.asarray(
                json.dumps(
                    {
                        "reference_id": candidate.sample_id,
                        "speaker_pseudonym": candidate.speaker_pseudonym,
                        "source_id": candidate.source_id,
                        "quality_score": candidate.quality_score,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                )
            )
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(f"{destination.name}.part")
    if partial.exists():
        raise FileExistsError(partial)
    try:
        with partial.open("xb") as sink:
            np.savez_compressed(sink, **arrays)
        partial.replace(destination)
    except Exception:
        if partial.exists():
            partial.unlink()
        raise


def load_reference_bank_artifact(
    path: Path | str,
    *,
    expected_model_hash: str | None = None,
    expected_vocabulary_hash: str | None = None,
) -> ReferenceBank:
    try:
        with np.load(Path(path), allow_pickle=False) as archive:
            version = str(archive["version"].item())
            model_hash = str(archive["model_hash"].item())
            vocabulary_hash = str(archive["vocabulary_hash"].item())
            if expected_model_hash is not None and model_hash != expected_model_hash:
                raise ReferenceBankBuildError("model_hash_mismatch")
            if expected_vocabulary_hash is not None and vocabulary_hash != expected_vocabulary_hash:
                raise ReferenceBankBuildError("vocabulary_hash_mismatch")
            references: dict[str, list[ReferenceEmbedding]] = defaultdict(list)
            for key in sorted(archive.files):
                if not key.startswith(REFERENCE_PREFIX):
                    continue
                suffix = key[len(REFERENCE_PREFIX) :]
                word_id, separator, index = suffix.rpartition("__")
                if not separator or not word_id or not index.isdigit():
                    raise ReferenceBankBuildError("reference_key_invalid")
                meta_key = f"{REFERENCE_META_PREFIX}{suffix}"
                if meta_key not in archive.files:
                    raise ReferenceBankBuildError("reference_metadata_missing")
                metadata = json.loads(str(archive[meta_key].item()))
                embedding = np.asarray(archive[key], dtype=np.float32)
                if embedding.ndim != 2 or embedding.size == 0 or not np.isfinite(embedding).all():
                    raise ReferenceBankBuildError("reference_embedding_invalid")
                references[word_id].append(
                    ReferenceEmbedding(
                        reference_id=str(metadata["reference_id"]),
                        speaker_pseudonym=str(metadata["speaker_pseudonym"]),
                        embedding=embedding.copy(),
                    )
                )
    except ReferenceBankBuildError:
        raise
    except Exception as exc:
        raise ReferenceBankBuildError("reference_bank_payload_invalid") from exc
    if not references:
        raise ReferenceBankBuildError("reference_bank_empty")
    return ReferenceBank(
        version=version,
        model_hash=model_hash,
        vocabulary_hash=vocabulary_hash,
        references=dict(references),
    )
