"""Validation and aggregation for physical Android benchmark exports."""

from __future__ import annotations

import math
import re
from collections.abc import Sequence
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class DeviceBenchmarkInput(BaseModel):
    """Raw benchmark export; latency samples are removed from aggregate evidence."""

    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    schema_version: Literal["1.0"]
    service: Literal["aws_device_farm", "firebase_test_lab", "local_lab"]
    service_run_id: str = Field(min_length=1)
    device_fingerprint: str = Field(min_length=1)
    device_model: str = Field(min_length=1)
    android_api: int = Field(ge=23)
    form_factor: Literal["phone", "tablet"]
    is_physical: bool
    execution_provider: Literal["CPUExecutionProvider", "NnapiExecutionProvider"]
    repetitions: int = Field(ge=30)
    cold_load_ms: float = Field(gt=0.0)
    latency_samples_ms: tuple[float, ...] = Field(min_length=30)
    peak_memory_mb: float = Field(gt=0.0)
    thermal_status: str = Field(min_length=1)
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    offline_assertion: bool
    network_access_detected: bool
    fixture_scope: Literal["synthetic_non_sensitive", "approved_non_sensitive"]

    @model_validator(mode="after")
    def validate_samples(self) -> Self:
        if len(self.latency_samples_ms) != self.repetitions:
            raise ValueError("repetitions must equal the number of latency samples")
        if any(value <= 0 for value in self.latency_samples_ms):
            raise ValueError("latency samples must be positive")
        return self


class DeviceBenchmarkReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    schema_version: Literal["1.0"] = "1.0"
    service: Literal["aws_device_farm", "firebase_test_lab", "local_lab"]
    device_fingerprint: str
    device_model: str
    android_api: int
    form_factor: Literal["phone", "tablet"]
    execution_provider: Literal["CPUExecutionProvider", "NnapiExecutionProvider"]
    repetitions: int
    cold_load_ms: float
    median_latency_ms: float
    p95_latency_ms: float
    peak_memory_mb: float
    thermal_status: str
    model_sha256: str
    physical_device_measured: bool
    offline_verified: bool
    promotable: bool
    evidence_scope: Literal[
        "representative_physical_android", "emulator_functional_only"
    ]


def percentile(values: Sequence[float], quantile: float) -> float:
    """Return a linearly interpolated percentile over finite values."""

    if not values:
        raise ValueError("percentile requires values")
    if not math.isfinite(quantile) or not 0.0 <= quantile <= 1.0:
        raise ValueError("quantile must be between zero and one")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("percentile values must be finite")
    ordered = sorted(values)
    position = (len(ordered) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    fraction = position - lower
    return float(ordered[lower] + fraction * (ordered[upper] - ordered[lower]))


def validate_device_benchmark(
    benchmark: DeviceBenchmarkInput, *, expected_model_sha256: str
) -> DeviceBenchmarkReport:
    """Bind the report to one model and refuse emulator/network evidence as promotion."""

    if not _SHA256.fullmatch(expected_model_sha256):
        raise ValueError("expected model digest must be lowercase SHA-256")
    if benchmark.model_sha256 != expected_model_sha256:
        raise ValueError("model digest does not match the benchmarked artifact")
    median = percentile(benchmark.latency_samples_ms, 0.50)
    p95 = percentile(benchmark.latency_samples_ms, 0.95)
    offline = benchmark.offline_assertion and not benchmark.network_access_detected
    promotable = benchmark.is_physical and offline and p95 <= 500.0
    return DeviceBenchmarkReport(
        service=benchmark.service,
        device_fingerprint=benchmark.device_fingerprint,
        device_model=benchmark.device_model,
        android_api=benchmark.android_api,
        form_factor=benchmark.form_factor,
        execution_provider=benchmark.execution_provider,
        repetitions=benchmark.repetitions,
        cold_load_ms=benchmark.cold_load_ms,
        median_latency_ms=median,
        p95_latency_ms=p95,
        peak_memory_mb=benchmark.peak_memory_mb,
        thermal_status=benchmark.thermal_status,
        model_sha256=benchmark.model_sha256,
        physical_device_measured=benchmark.is_physical,
        offline_verified=offline,
        promotable=promotable,
        evidence_scope=(
            "representative_physical_android"
            if benchmark.is_physical
            else "emulator_functional_only"
        ),
    )
