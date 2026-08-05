"""Explicit pass/fail/not-measured promotion gates for full and edge tracks."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

GateStatus = Literal["pass", "fail", "not_measured"]


class ModelEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    model_id: str = Field(min_length=1)
    track: Literal["full_reference", "student"]
    adult_tamil_per: float | None = Field(default=None, ge=0.0)
    significant_baseline_improvement: bool | None = None
    controlled_confusion_auroc: float | None = Field(default=None, ge=0.0, le=1.0)
    proxy_false_accept_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    expected_calibration_error: float | None = Field(default=None, ge=0.0, le=1.0)
    robustness_safe: bool | None = None
    export_succeeded: bool | None = None
    compressed_size_bytes: int | None = Field(default=None, gt=0)
    int8_per_delta: float | None = Field(default=None, ge=0.0)
    median_absolute_gop_delta: float | None = Field(default=None, ge=0.0)
    physical_android_p95_ms: float | None = Field(default=None, gt=0.0)
    physical_android_measured: bool = False

    @model_validator(mode="after")
    def validate_device_measurement(self) -> Self:
        if self.physical_android_measured and self.physical_android_p95_ms is None:
            raise ValueError("physical measurement requires physical_android_p95_ms")
        return self


class GateResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str
    status: GateStatus
    observed: float | bool | int | None
    requirement: str


class PromotionReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str
    track: Literal["full_reference", "student"]
    gates: tuple[GateResult, ...]
    promoted: bool
    evidence_scope: Literal["engineering_proxy"] = "engineering_proxy"


def _maximum(name: str, value: float | None, maximum: float) -> GateResult:
    return GateResult(
        name=name,
        status="not_measured" if value is None else "pass" if value <= maximum else "fail",
        observed=value,
        requirement=f"<= {maximum}",
    )


def _minimum(name: str, value: float | None, minimum: float) -> GateResult:
    return GateResult(
        name=name,
        status="not_measured" if value is None else "pass" if value >= minimum else "fail",
        observed=value,
        requirement=f">= {minimum}",
    )


def _required_true(name: str, value: bool | None) -> GateResult:
    return GateResult(
        name=name,
        status="not_measured" if value is None else "pass" if value else "fail",
        observed=value,
        requirement="true",
    )


def evaluate_promotion(evidence: ModelEvidence) -> PromotionReport:
    """Apply fixed gates without converting missing evidence into success."""

    gates: list[GateResult] = [
        _maximum("adult_tamil_per", evidence.adult_tamil_per, 0.20),
        _required_true(
            "significant_baseline_improvement", evidence.significant_baseline_improvement
        ),
        _minimum("controlled_confusion_auroc", evidence.controlled_confusion_auroc, 0.90),
        _maximum("proxy_false_accept_rate", evidence.proxy_false_accept_rate, 0.05),
        _maximum("expected_calibration_error", evidence.expected_calibration_error, 0.05),
        _required_true("robustness_safe", evidence.robustness_safe),
    ]
    if evidence.track == "student":
        gates.extend(
            (
                _required_true("export_succeeded", evidence.export_succeeded),
                _maximum(
                    "compressed_size_bytes", evidence.compressed_size_bytes, 50_000_000
                ),
                _maximum("int8_per_delta", evidence.int8_per_delta, 0.01),
                _maximum(
                    "median_absolute_gop_delta",
                    evidence.median_absolute_gop_delta,
                    0.03,
                ),
                GateResult(
                    name="physical_android_p95_ms",
                    status=(
                        "not_measured"
                        if not evidence.physical_android_measured
                        or evidence.physical_android_p95_ms is None
                        else "pass"
                        if evidence.physical_android_p95_ms <= 500.0
                        else "fail"
                    ),
                    observed=(
                        evidence.physical_android_p95_ms
                        if evidence.physical_android_measured
                        else None
                    ),
                    requirement="physical device <= 500.0 ms",
                ),
            )
        )
    gate_tuple = tuple(gates)
    return PromotionReport(
        model_id=evidence.model_id,
        track=evidence.track,
        gates=gate_tuple,
        promoted=all(gate.status == "pass" for gate in gate_tuple),
    )
