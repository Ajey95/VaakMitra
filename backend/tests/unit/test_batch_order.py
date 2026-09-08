from __future__ import annotations

import json
from itertools import chain
from pathlib import Path

import pytest
from modeling.training.batch_order import (
    LengthRecord,
    build_batch_order,
    remaining_batches,
)


def test_resume_cursor_neither_replays_nor_skips_a_batch() -> None:
    records = tuple(
        LengthRecord(index, samples)
        for index, samples in enumerate([9, 2, 8, 1, 7, 3])
    )
    order = build_batch_order(
        records,
        seed=17,
        epoch=2,
        batch_size=2,
        bucket_size=4,
    )

    assert order.batches[:2] + remaining_batches(order, 2) == order.batches
    assert set(chain.from_iterable(order.batches)) == set(range(6))


def test_same_inputs_produce_same_order_and_digest() -> None:
    records = tuple(LengthRecord(index, index + 1) for index in range(12))

    first = build_batch_order(records, seed=17, epoch=1, batch_size=2, bucket_size=4)
    second = build_batch_order(records, seed=17, epoch=1, batch_size=2, bucket_size=4)

    assert first == second
    assert len(first.order_sha256) == 64


def test_length_bucketing_bounds_padding_inside_each_batch() -> None:
    records = tuple(
        LengthRecord(index, samples) for index, samples in enumerate(range(1, 17))
    )
    order = build_batch_order(
        records,
        seed=3,
        epoch=0,
        batch_size=2,
        bucket_size=4,
    )
    sample_counts = {record.record_index: record.sample_count for record in records}

    assert all(
        max(sample_counts[index] for index in batch)
        - min(sample_counts[index] for index in batch)
        <= 3
        for batch in order.batches
    )


def test_empty_records_produce_an_empty_order() -> None:
    order = build_batch_order((), seed=1, epoch=0, batch_size=1, bucket_size=1)

    assert order.batches == ()
    assert remaining_batches(order, 0) == ()


@pytest.mark.parametrize(
    ("records", "message"),
    [
        ((LengthRecord(0, 10), LengthRecord(0, 20)), "record indexes must be unique"),
        ((LengthRecord(-1, 10),), "record indexes must be non-negative"),
        ((LengthRecord(0, 0),), "sample counts must be positive"),
    ],
)
def test_invalid_length_records_are_rejected(
    records: tuple[LengthRecord, ...],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_batch_order(records, seed=1, epoch=0, batch_size=1, bucket_size=1)


@pytest.mark.parametrize("cursor", [-1, 4])
def test_out_of_range_resume_cursor_is_rejected(cursor: int) -> None:
    records = tuple(LengthRecord(index, index + 1) for index in range(6))
    order = build_batch_order(records, seed=1, epoch=0, batch_size=2, bucket_size=4)

    with pytest.raises(ValueError, match="next batch index"):
        remaining_batches(order, cursor)


def test_notebook_target_cache_records_duration_for_bucketing() -> None:
    notebook = json.loads(
        Path("notebooks/VaakMitra_GPU_Training_Colab.ipynb").read_text(encoding="utf-8")
    )
    target_cell = next(cell for cell in notebook["cells"] if cell["id"] == "phoneme-targets")
    code = "".join(target_cell["source"])

    assert '"duration_ms": record["duration_ms"]' in code
    assert "duration_ms: int" in code
    assert "sample_count" in code
