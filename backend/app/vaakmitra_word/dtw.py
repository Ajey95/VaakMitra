"""Representation-level cosine DTW (DEC-006, DTW-001 through DTW-006)."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil

import numpy as np


class InvalidEmbeddingSequence(ValueError):
    """Raised when an embedding sequence cannot be compared safely."""


def _validated(sequence: np.ndarray, name: str) -> np.ndarray:
    value = np.asarray(sequence, dtype=np.float64)
    if value.ndim != 2 or value.shape[0] == 0 or value.shape[1] == 0:
        raise InvalidEmbeddingSequence(f"{name} must be a non-empty [frames, dimensions] array")
    if not np.isfinite(value).all():
        raise InvalidEmbeddingSequence(f"{name} contains non-finite values")
    return value


def cosine_dtw_distance(
    query: np.ndarray,
    reference: np.ndarray,
    band_ratio: float = 0.20,
) -> float:
    """Return path-length-normalized cosine DTW distance for two frame sequences."""
    left = _validated(query, "query")
    right = _validated(reference, "reference")
    if left.shape[1] != right.shape[1]:
        raise InvalidEmbeddingSequence("query and reference embedding dimensions differ")
    if not 0.0 < band_ratio <= 1.0:
        raise ValueError("band_ratio must be in (0, 1]")

    left_norm = np.linalg.norm(left, axis=1, keepdims=True)
    right_norm = np.linalg.norm(right, axis=1, keepdims=True)
    left_unit = np.divide(left, left_norm, out=np.zeros_like(left), where=left_norm > 1e-12)
    right_unit = np.divide(right, right_norm, out=np.zeros_like(right), where=right_norm > 1e-12)

    n, m = left.shape[0], right.shape[0]
    band = max(abs(n - m), ceil(max(n, m) * band_ratio))
    costs = np.full((n + 1, m + 1), np.inf, dtype=np.float64)
    lengths = np.zeros((n + 1, m + 1), dtype=np.int32)
    costs[0, 0] = 0.0

    for i in range(1, n + 1):
        for j in range(max(1, i - band), min(m, i + band) + 1):
            frame_cost = float(np.clip(1.0 - np.dot(left_unit[i - 1], right_unit[j - 1]), 0.0, 2.0))
            predecessors = (
                (costs[i - 1, j], lengths[i - 1, j]),
                (costs[i, j - 1], lengths[i, j - 1]),
                (costs[i - 1, j - 1], lengths[i - 1, j - 1]),
            )
            previous_cost, previous_length = min(predecessors, key=lambda item: item[0])
            if np.isfinite(previous_cost):
                costs[i, j] = previous_cost + frame_cost
                lengths[i, j] = previous_length + 1

    if not np.isfinite(costs[n, m]) or lengths[n, m] == 0:
        raise InvalidEmbeddingSequence("no valid DTW path exists for the configured band")
    return float(costs[n, m] / lengths[n, m])


@dataclass(frozen=True)
class ReferenceEmbedding:
    reference_id: str
    speaker_pseudonym: str
    embedding: np.ndarray


@dataclass(frozen=True)
class ReferenceMatch:
    distance: float
    distinct_speakers: int
    aggregated_speakers: tuple[str, ...]


@dataclass(frozen=True)
class ReferenceBank:
    version: str
    model_hash: str
    references: dict[str, list[np.ndarray | ReferenceEmbedding]]
    vocabulary_hash: str = ""

    def match(
        self,
        word_id: str,
        embeddings: np.ndarray,
        *,
        model_hash: str,
        aggregate_speakers: int = 3,
    ) -> ReferenceMatch | None:
        """Aggregate nearest distances from distinct speakers (DEC-017, DTW-005)."""
        if model_hash != self.model_hash or aggregate_speakers < 1:
            return None
        candidates = self.references.get(word_id)
        if not candidates:
            return None
        best_by_speaker: dict[str, float] = {}
        for index, reference in enumerate(candidates):
            if isinstance(reference, ReferenceEmbedding):
                speaker = reference.speaker_pseudonym
                sequence = reference.embedding
            else:
                # Legacy synthetic fixtures have no identity metadata. Treat each as
                # independent only for backwards-compatible engineering tests.
                speaker = f"legacy-reference-{index}"
                sequence = reference
            try:
                distance = cosine_dtw_distance(embeddings, sequence)
            except InvalidEmbeddingSequence:
                continue
            best_by_speaker[speaker] = min(distance, best_by_speaker.get(speaker, float("inf")))
        if len(best_by_speaker) < aggregate_speakers:
            return None
        ranked = sorted(best_by_speaker.items(), key=lambda item: (item[1], item[0]))
        selected = ranked[:aggregate_speakers]
        return ReferenceMatch(
            distance=float(np.mean([distance for _, distance in selected])),
            distinct_speakers=len(best_by_speaker),
            aggregated_speakers=tuple(speaker for speaker, _ in selected),
        )

    def best_distance(
        self,
        word_id: str,
        embeddings: np.ndarray,
        *,
        model_hash: str,
    ) -> float | None:
        match = self.match(word_id, embeddings, model_hash=model_hash)
        return match.distance if match is not None else None
