"""Deterministic length-bucketed batch ordering with resumable cursors."""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Sequence
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class LengthRecord:
    record_index: int
    sample_count: int


@dataclass(frozen=True, slots=True)
class BatchOrder:
    seed: int
    epoch: int
    batch_size: int
    bucket_size: int
    batches: tuple[tuple[int, ...], ...]
    order_sha256: str


def build_batch_order(
    records: Sequence[LengthRecord],
    *,
    seed: int,
    epoch: int,
    batch_size: int,
    bucket_size: int,
) -> BatchOrder:
    """Sort by length, shuffle locally, then shuffle complete batches."""

    if epoch < 0:
        raise ValueError("epoch must be non-negative")
    if batch_size <= 0:
        raise ValueError("batch size must be positive")
    if bucket_size < batch_size:
        raise ValueError("bucket size must be at least batch size")

    indexes = [record.record_index for record in records]
    if len(indexes) != len(set(indexes)):
        raise ValueError("record indexes must be unique")
    if any(index < 0 for index in indexes):
        raise ValueError("record indexes must be non-negative")
    if any(record.sample_count <= 0 for record in records):
        raise ValueError("sample counts must be positive")

    ordered = sorted(records, key=lambda item: (item.sample_count, item.record_index))
    buckets = [
        ordered[start : start + bucket_size]
        for start in range(0, len(ordered), bucket_size)
    ]
    rng = random.Random(f"{seed}:{epoch}")
    batches: list[tuple[int, ...]] = []
    for bucket in buckets:
        rng.shuffle(bucket)
        batches.extend(
            tuple(item.record_index for item in bucket[start : start + batch_size])
            for start in range(0, len(bucket), batch_size)
        )
    rng.shuffle(batches)
    frozen_batches = tuple(batches)
    canonical = json.dumps(frozen_batches, separators=(",", ":")).encode("utf-8")
    return BatchOrder(
        seed=seed,
        epoch=epoch,
        batch_size=batch_size,
        bucket_size=bucket_size,
        batches=frozen_batches,
        order_sha256=hashlib.sha256(canonical).hexdigest(),
    )


def remaining_batches(
    order: BatchOrder,
    next_batch_index: int,
) -> tuple[tuple[int, ...], ...]:
    """Return batches starting at the next unapplied batch cursor."""

    if next_batch_index < 0 or next_batch_index > len(order.batches):
        raise ValueError("next batch index is outside the batch order")
    return order.batches[next_batch_index:]
