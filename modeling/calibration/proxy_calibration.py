"""Deterministic engineering calibration without therapist-validity claims."""

from __future__ import annotations

import math
import random
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict


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
class GroupedCalibrationExample:
    example_id: str
    phone: str
    phonological_class: str
    score: float
    acceptable: bool

    def __post_init__(self) -> None:
        ProxyCalibrationExample(self.example_id, self.score, self.acceptable)
        if not self.phone.strip() or not self.phonological_class.strip():
            raise ValueError("phone and phonological_class must be non-empty")


class GroupedThresholdReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    phone_thresholds: dict[str, float]
    class_thresholds: dict[str, float]
    fallback_by_phone: dict[str, str]
    calibration_status: str = "proxy_not_therapist_calibrated"


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
    false_rejects: int
    false_accept_rate: float
    true_accept_rate: float
    false_reject_rate: float
    auroc: float
    auroc_ci_low: float
    auroc_ci_high: float
    brier_score: float
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


def _auroc(examples: Sequence[ProxyCalibrationExample]) -> float:
    acceptable = [example for example in examples if example.acceptable is True]
    unacceptable = [example for example in examples if example.acceptable is False]
    if not acceptable or not unacceptable:
        raise ValueError("AUROC requires acceptable and unacceptable examples")
    wins = 0.0
    for positive in acceptable:
        assert positive.score is not None
        for negative in unacceptable:
            assert negative.score is not None
            wins += float(positive.score > negative.score)
            wins += 0.5 * float(positive.score == negative.score)
    return wins / (len(acceptable) * len(unacceptable))


def _brier_score(examples: Sequence[ProxyCalibrationExample]) -> float:
    return sum(
        ((example.score or 0.0) - float(bool(example.acceptable))) ** 2
        for example in examples
    ) / len(examples)


def _bootstrap_auroc_interval(
    examples: Sequence[ProxyCalibrationExample], *, samples: int, seed: int
) -> tuple[float, float]:
    if samples <= 0:
        raise ValueError("bootstrap_samples must be positive")
    randomizer = random.Random(seed)
    estimates: list[float] = []
    for _ in range(samples):
        resampled = tuple(randomizer.choice(examples) for _ in examples)
        if {example.acceptable for example in resampled} >= {True, False}:
            estimates.append(_auroc(resampled))
    if not estimates:
        estimate = _auroc(examples)
        return estimate, estimate
    estimates.sort()
    last = len(estimates) - 1
    low_index = math.floor(0.025 * last)
    high_index = math.ceil(0.975 * last)
    return estimates[low_index], estimates[high_index]


def calibrate_proxy_thresholds(
    examples: Sequence[ProxyCalibrationExample],
    *,
    candidate_thresholds: Sequence[float],
    max_false_accept_rate: float,
    calibration_bins: int = 10,
    bootstrap_samples: int = 200,
    bootstrap_seed: int = 1729,
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
    false_rejects = sum(
        example.score is not None and example.score < pass_threshold for example in acceptable
    )
    false_reject_rate = false_rejects / len(acceptable)
    auroc = _auroc(scorable)
    auroc_ci_low, auroc_ci_high = _bootstrap_auroc_interval(
        scorable, samples=bootstrap_samples, seed=bootstrap_seed
    )

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
        false_rejects=false_rejects,
        false_accept_rate=false_accept_rate,
        true_accept_rate=true_accepts / len(acceptable),
        false_reject_rate=false_reject_rate,
        auroc=auroc,
        auroc_ci_low=auroc_ci_low,
        auroc_ci_high=auroc_ci_high,
        brier_score=_brier_score(scorable),
        expected_calibration_error=_expected_calibration_error(scorable, calibration_bins),
        calibration_bins=calibration_bins,
    )


def fit_grouped_thresholds(
    observations: Sequence[GroupedCalibrationExample],
    *,
    candidate_thresholds: Sequence[float],
    max_false_accept_rate: float,
    minimum_phone_examples: int,
) -> GroupedThresholdReport:
    """Fit phone thresholds when supported and fall back to phonological classes."""

    if minimum_phone_examples <= 0:
        raise ValueError("minimum_phone_examples must be positive")
    if not observations:
        raise ValueError("grouped calibration requires observations")
    identifiers = [observation.example_id for observation in observations]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError("grouped calibration example identifiers must be unique")

    by_phone: dict[str, list[GroupedCalibrationExample]] = {}
    by_class: dict[str, list[GroupedCalibrationExample]] = {}
    phone_class: dict[str, str] = {}
    for observation in observations:
        previous_class = phone_class.setdefault(
            observation.phone, observation.phonological_class
        )
        if previous_class != observation.phonological_class:
            raise ValueError("one phone cannot belong to multiple phonological classes")
        by_phone.setdefault(observation.phone, []).append(observation)
        by_class.setdefault(observation.phonological_class, []).append(observation)

    def threshold_for(group: Sequence[GroupedCalibrationExample]) -> float:
        examples = tuple(
            ProxyCalibrationExample(item.example_id, item.score, item.acceptable)
            for item in group
        )
        return calibrate_proxy_thresholds(
            examples,
            candidate_thresholds=candidate_thresholds,
            max_false_accept_rate=max_false_accept_rate,
            bootstrap_samples=50,
        ).pass_threshold

    class_thresholds = {
        class_name: threshold_for(group)
        for class_name, group in sorted(by_class.items())
        if {item.acceptable for item in group} == {True, False}
    }
    phone_thresholds: dict[str, float] = {}
    fallback: dict[str, str] = {}
    for phone, group in sorted(by_phone.items()):
        if len(group) >= minimum_phone_examples and {
            item.acceptable for item in group
        } == {True, False}:
            phone_thresholds[phone] = threshold_for(group)
            continue
        class_name = phone_class[phone]
        if class_name not in class_thresholds:
            raise ValueError("phone lacks supported phone or phonological-class calibration")
        fallback[phone] = class_name
    return GroupedThresholdReport(
        phone_thresholds=phone_thresholds,
        class_thresholds=class_thresholds,
        fallback_by_phone=fallback,
    )
