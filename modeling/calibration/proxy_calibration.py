"""Deterministic engineering calibration without therapist-validity claims."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class ProxyCalibrationExample:
    """A proxy label, or an explicitly unscorable example when both values are absent."""

    example_id: str
    score: float | None
    acceptable: bool | None

    def __post_init__(self) -> None:
        if not self.example_id.strip():
            raise ValueError("example_id must be non-empty")
        if (self.score is None) != (self.acceptable is None):
            raise ValueError("score and acceptable must both be present or both be absent")
        if self.score is not None and (
            not math.isfinite(self.score) or not 0.0 <= self.score <= 1.0
        ):
            raise ValueError("score must be finite and between zero and one")
        if self.acceptable is not None and not isinstance(self.acceptable, bool):
            raise ValueError("acceptable must be a boolean")


@dataclass(frozen=True, slots=True)
class ProxyCalibrationReport:
    schema_version: str
    calibration_status: str
    example_count: int
    scorable_count: int
    unscorable_count: int
    unscorable_rate: float
    pass_threshold: float
    coach_threshold: float
    max_false_accept_rate: float
    false_accepts: int
    true_accepts: int
    false_accept_rate: float
    true_accept_rate: float
    expected_calibration_error: float
    calibration_bins: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _expected_calibration_error(
    examples: Sequence[ProxyCalibrationExample], bins: int
) -> float:
    populated: list[list[ProxyCalibrationExample]] = [[] for _ in range(bins)]
    for example in examples:
        assert example.score is not None
        index = min(int(example.score * bins), bins - 1)
        populated[index].append(example)

    total = len(examples)
    error = 0.0
    for bucket in populated:
        if not bucket:
            continue
        mean_score = sum(example.score or 0.0 for example in bucket) / len(bucket)
        mean_label = sum(bool(example.acceptable) for example in bucket) / len(bucket)
        error += (len(bucket) / total) * abs(mean_score - mean_label)
    return error


def calibrate_proxy_thresholds(
    examples: Sequence[ProxyCalibrationExample],
    *,
    candidate_thresholds: Sequence[float],
    max_false_accept_rate: float,
    calibration_bins: int = 10,
) -> ProxyCalibrationReport:
    """Choose a conservative pass threshold from non-clinical proxy labels."""

    if not examples:
        raise ValueError("at least one calibration example is required")
    example_ids = [example.example_id for example in examples]
    if len(example_ids) != len(set(example_ids)):
        raise ValueError("example_id values must be unique")
    if (
        not math.isfinite(max_false_accept_rate)
        or not 0.0 <= max_false_accept_rate <= 1.0
    ):
        raise ValueError("max_false_accept_rate must be between zero and one")
    if calibration_bins <= 0:
        raise ValueError("calibration_bins must be positive")

    thresholds = sorted({float(threshold) for threshold in candidate_thresholds})
    if not thresholds or any(
        not math.isfinite(threshold) or not 0.0 <= threshold <= 1.0
        for threshold in thresholds
    ):
        raise ValueError("candidate_thresholds must be finite values between zero and one")

    scorable = [example for example in examples if example.score is not None]
    acceptable = [example for example in scorable if example.acceptable is True]
    unacceptable = [example for example in scorable if example.acceptable is False]
    if not acceptable or not unacceptable:
        raise ValueError("calibration requires acceptable and unacceptable scorable examples")

    feasible: list[tuple[int, float, int, float]] = []
    for threshold in thresholds:
        true_accepts = sum(
            example.score is not None and example.score >= threshold for example in acceptable
        )
        false_accepts = sum(
            example.score is not None and example.score >= threshold for example in unacceptable
        )
        false_accept_rate = false_accepts / len(unacceptable)
        if false_accept_rate <= max_false_accept_rate:
            feasible.append((true_accepts, threshold, false_accepts, false_accept_rate))
    if not feasible:
        raise ValueError("no candidate threshold satisfies max_false_accept_rate")

    true_accepts, pass_threshold, false_accepts, false_accept_rate = max(
        feasible,
        key=lambda result: (result[0], -result[1]),
    )
    lower_thresholds = [threshold for threshold in thresholds if threshold < pass_threshold]
    coach_threshold = max(lower_thresholds, default=pass_threshold / 2.0)
    scorable_count = len(scorable)
    unscorable_count = len(examples) - scorable_count

    return ProxyCalibrationReport(
        schema_version="1.0",
        calibration_status="proxy_not_therapist_calibrated",
        example_count=len(examples),
        scorable_count=scorable_count,
        unscorable_count=unscorable_count,
        unscorable_rate=unscorable_count / len(examples),
        pass_threshold=pass_threshold,
        coach_threshold=coach_threshold,
        max_false_accept_rate=max_false_accept_rate,
        false_accepts=false_accepts,
        true_accepts=true_accepts,
        false_accept_rate=false_accept_rate,
        true_accept_rate=true_accepts / len(acceptable),
        expected_calibration_error=_expected_calibration_error(scorable, calibration_bins),
        calibration_bins=calibration_bins,
    )
