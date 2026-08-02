from __future__ import annotations

import pytest
from benchmarks.run_benchmark import summarize_latencies


def test_latency_summary_uses_nearest_rank_p95() -> None:
    summary = summarize_latencies([10.0, 20.0, 30.0, 40.0, 50.0])

    assert summary.median_ms == 30.0
    assert summary.p95_ms == 50.0
    assert summary.minimum_ms == 10.0
    assert summary.maximum_ms == 50.0


@pytest.mark.parametrize("values", [[], [-1.0], [float("nan")], [float("inf")]])
def test_latency_summary_rejects_invalid_measurements(values: list[float]) -> None:
    with pytest.raises(ValueError, match="latencies"):
        summarize_latencies(values)

