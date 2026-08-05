"""Seeded child-like acoustic stress transforms without child-domain claims."""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import numpy as np
import numpy.typing as npt
from pydantic import BaseModel, ConfigDict, Field, model_validator

StressKind = Literal[
    "rate",
    "pitch_formant",
    "vtln",
    "pause",
    "repetition",
    "noise",
    "gain",
    "clipping",
    "bandwidth",
    "resampling",
]
Severity = Literal["moderate", "severe"]
FloatWave = npt.NDArray[np.float32]


class StressSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)

    transform_id: str = Field(min_length=1)
    kind: StressKind
    severity: Severity
    value: float

    @model_validator(mode="after")
    def validate_value_for_kind(self) -> StressSpec:
        valid = {
            "rate": 0.5 <= self.value <= 2.0,
            "pitch_formant": 0.5 <= self.value <= 2.0,
            "vtln": 0.5 <= self.value <= 2.0,
            "pause": 0.0 < self.value <= 1.0,
            "repetition": 0.0 < self.value <= 1.0,
            "noise": -10.0 <= self.value <= 60.0,
            "gain": 0.0 < self.value <= 4.0,
            "clipping": 0.0 < self.value <= 1.0,
            "bandwidth": 100.0 <= self.value < 8_000.0,
            "resampling": 1_000.0 <= self.value <= 16_000.0,
        }[self.kind]
        if not valid:
            raise ValueError(f"value is outside the supported range for {self.kind}")
        return self


class StressMatrix(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    sample_rate_hz: Literal[16000]
    evidence_scope: Literal["transformation_robustness_only"]
    child_domain_accuracy_measured: Literal[False]
    transforms: tuple[StressSpec, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def reject_duplicate_transform_ids(self) -> StressMatrix:
        identifiers = [item.transform_id for item in self.transforms]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("stress transform identifiers must be unique")
        return self


def load_stress_matrix(path: str | Path) -> StressMatrix:
    return StressMatrix.model_validate_json(Path(path).read_text(encoding="utf-8"))


@dataclass(frozen=True, slots=True)
class StressResult:
    waveform: FloatWave
    transform_id: str
    preserves_expected_sequence: bool
    expected_outcome: Literal["relative_score_preservation", "unscorable_preferred"]
    evidence_scope: Literal["transformation_robustness_only"] = (
        "transformation_robustness_only"
    )


def _validate_waveform(waveform: npt.NDArray[np.generic]) -> FloatWave:
    if not isinstance(waveform, np.ndarray) or waveform.dtype != np.float32:
        raise TypeError("waveform must be a float32 NumPy array")
    if waveform.ndim != 1 or waveform.size == 0:
        raise ValueError("waveform must be non-empty mono audio")
    if not np.isfinite(waveform).all():
        raise ValueError("waveform must contain only finite values")
    if float(np.max(np.abs(waveform))) > 1.0:
        raise ValueError("waveform samples must be within [-1, 1]")
    return np.ascontiguousarray(waveform)


def _resample_to_length(waveform: FloatWave, output_length: int) -> FloatWave:
    if output_length <= 0:
        raise ValueError("resampled output length must be positive")
    if output_length == waveform.size:
        return waveform.copy()
    source = np.linspace(0.0, 1.0, waveform.size, dtype=np.float64)
    target = np.linspace(0.0, 1.0, output_length, dtype=np.float64)
    return np.interp(target, source, waveform).astype(np.float32)


def _warp_spectrum(waveform: FloatWave, factor: float) -> FloatWave:
    spectrum = np.fft.rfft(waveform)
    positions = np.arange(spectrum.size, dtype=np.float64) * factor
    base = np.arange(spectrum.size, dtype=np.float64)
    real = np.interp(positions, base, spectrum.real, left=0.0, right=0.0)
    imaginary = np.interp(positions, base, spectrum.imag, left=0.0, right=0.0)
    warped = np.fft.irfft(real + 1j * imaginary, n=waveform.size)
    return warped.astype(np.float32)


def apply_stress(
    waveform: npt.NDArray[np.generic], spec: StressSpec, *, seed: int
) -> StressResult:
    """Apply one deterministic local stress and attach metamorphic expectations."""

    source = _validate_waveform(waveform)
    if spec.kind == "rate":
        stressed = _resample_to_length(source, max(1, round(source.size / spec.value)))
    elif spec.kind == "pitch_formant":
        stressed = _warp_spectrum(source, spec.value)
    elif spec.kind == "vtln":
        stressed = _warp_spectrum(source, 1.0 / spec.value)
    elif spec.kind == "pause":
        pause = np.zeros(round(16_000 * spec.value), dtype=np.float32)
        midpoint = source.size // 2
        stressed = np.concatenate((source[:midpoint], pause, source[midpoint:]))
    elif spec.kind == "repetition":
        segment_length = min(source.size, max(1, round(16_000 * spec.value)))
        start = max(0, (source.size - segment_length) // 2)
        segment = source[start : start + segment_length]
        stressed = np.concatenate((source[: start + segment_length], segment, source[start + segment_length :]))
    elif spec.kind == "noise":
        randomizer = np.random.default_rng(seed)
        root_mean_square = math.sqrt(float(np.mean(np.square(source, dtype=np.float64))))
        noise_scale = root_mean_square / (10.0 ** (spec.value / 20.0))
        stressed = source + randomizer.normal(0.0, noise_scale, source.shape).astype(np.float32)
    elif spec.kind == "gain":
        stressed = source * np.float32(spec.value)
    elif spec.kind == "clipping":
        stressed = np.clip(source, -spec.value, spec.value)
    elif spec.kind == "bandwidth":
        spectrum = np.fft.rfft(source)
        frequencies = np.fft.rfftfreq(source.size, d=1.0 / 16_000.0)
        spectrum[frequencies > spec.value] = 0.0
        stressed = np.fft.irfft(spectrum, n=source.size).astype(np.float32)
    else:
        down_length = max(1, round(source.size * spec.value / 16_000.0))
        stressed = _resample_to_length(_resample_to_length(source, down_length), source.size)
    bounded = np.clip(stressed, -1.0, 1.0).astype(np.float32)
    if not np.isfinite(bounded).all():
        raise FloatingPointError("stress transform produced non-finite samples")
    return StressResult(
        waveform=np.ascontiguousarray(bounded),
        transform_id=spec.transform_id,
        preserves_expected_sequence=True,
        expected_outcome=(
            "relative_score_preservation"
            if spec.severity == "moderate"
            else "unscorable_preferred"
        ),
    )
