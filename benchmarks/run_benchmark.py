"""Measure cold load, inference latency, model size, and process memory."""

from __future__ import annotations

import argparse
import json
import math
import statistics
import time
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from vaakmitra.acoustic.base import AcousticModelRuntime
from vaakmitra.acoustic.metadata import ModelManifest
from vaakmitra.acoustic.onnx_runtime import OnnxAcousticModelRuntime


@dataclass(frozen=True, slots=True)
class LatencySummary:
    minimum_ms: float
    median_ms: float
    p95_ms: float
    maximum_ms: float


@dataclass(frozen=True, slots=True)
class BenchmarkReport:
    schema_version: str
    evidence_scope: str
    model_version: str
    vocabulary_version: str
    model_sha256: str
    provider: str
    model_size_bytes: int
    cold_load_ms: float
    peak_rss_bytes: int
    warmup_runs: int
    measured_runs: int
    latency: LatencySummary
    timestamp_utc: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_latencies(values_ms: Sequence[float]) -> LatencySummary:
    """Return median and nearest-rank P95 from finite non-negative measurements."""

    ordered = sorted(float(value) for value in values_ms)
    if not ordered or any(value < 0 or not math.isfinite(value) for value in ordered):
        raise ValueError("latencies must be finite non-negative values")
    p95_index = max(0, math.ceil(0.95 * len(ordered)) - 1)
    return LatencySummary(
        minimum_ms=ordered[0],
        median_ms=statistics.median(ordered),
        p95_ms=ordered[p95_index],
        maximum_ms=ordered[-1],
    )


def run_benchmark(
    *,
    runtime_factory: Callable[[], AcousticModelRuntime],
    audio: np.ndarray,
    sample_rate: int,
    manifest: ModelManifest,
    model_path: Path,
    provider: str,
    evidence_scope: str,
    warmup_runs: int,
    measured_runs: int,
) -> BenchmarkReport:
    """Run a deterministic benchmark without claiming target-device evidence on a laptop."""

    if evidence_scope not in {"development_laptop", "target_device"}:
        raise ValueError("evidence_scope must be development_laptop or target_device")
    if warmup_runs < 0 or measured_runs <= 0:
        raise ValueError("warmup_runs must be non-negative and measured_runs must be positive")
    start = time.perf_counter_ns()
    runtime = runtime_factory()
    cold_load_ms = (time.perf_counter_ns() - start) / 1_000_000

    for _ in range(warmup_runs):
        runtime.infer(audio, sample_rate)
    measurements: list[float] = []
    try:
        import psutil  # type: ignore[import-untyped]
    except ImportError as error:
        raise RuntimeError("psutil is required for benchmark memory evidence") from error
    process = psutil.Process()
    peak_rss = process.memory_info().rss
    for _ in range(measured_runs):
        start = time.perf_counter_ns()
        runtime.infer(audio, sample_rate)
        measurements.append((time.perf_counter_ns() - start) / 1_000_000)
        peak_rss = max(peak_rss, process.memory_info().rss)

    return BenchmarkReport(
        schema_version="1.0",
        evidence_scope=evidence_scope,
        model_version=manifest.model_version,
        vocabulary_version=manifest.vocabulary_version,
        model_sha256=manifest.sha256,
        provider=provider,
        model_size_bytes=model_path.stat().st_size,
        cold_load_ms=cold_load_ms,
        peak_rss_bytes=peak_rss,
        warmup_runs=warmup_runs,
        measured_runs=measured_runs,
        latency=summarize_latencies(measurements),
        timestamp_utc=datetime.now(UTC).isoformat(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Benchmark a local ONNX phoneme CTC model.")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--audio-npy", required=True, type=Path)
    parser.add_argument("--provider", default="CPUExecutionProvider")
    parser.add_argument(
        "--evidence-scope",
        choices=("development_laptop", "target_device"),
        default="development_laptop",
    )
    parser.add_argument("--warmup-runs", type=int, default=5)
    parser.add_argument("--measured-runs", type=int, default=30)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    manifest = ModelManifest.from_json(args.manifest)
    audio = np.load(args.audio_npy, allow_pickle=False)
    report = run_benchmark(
        runtime_factory=lambda: OnnxAcousticModelRuntime(
            args.model,
            manifest,
            providers=(args.provider,),
        ),
        audio=audio,
        sample_rate=manifest.sample_rate,
        manifest=manifest,
        model_path=args.model,
        provider=args.provider,
        evidence_scope=args.evidence_scope,
        warmup_runs=args.warmup_runs,
        measured_runs=args.measured_runs,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
