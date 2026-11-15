"""Bounded deterministic auxiliary audio view (DEC-005, NORM-001..007)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .audio import DecodedAudio


@dataclass(frozen=True)
class NormalizationConfig:
    peak_target: float = 0.95
    rate_factor: float = 1.0
    vtln_warp: float = 1.0
    rate_approved: bool = False
    vtln_approved: bool = False

    def __post_init__(self) -> None:
        if not 0.1 <= self.peak_target <= 0.95:
            raise ValueError("peak_target must be in [0.1, 0.95]")
        if not 0.85 <= self.rate_factor <= 1.18:
            raise ValueError("rate_factor must be in [0.85, 1.18]")
        if not 0.88 <= self.vtln_warp <= 1.12:
            raise ValueError("vtln_warp must be in [0.88, 1.12]")


@dataclass(frozen=True)
class NormalizedView:
    available: bool
    samples: np.ndarray
    sample_rate: int
    transforms: tuple[str, ...]
    reason: str | None = None


def create_normalized_view(
    decoded: DecodedAudio,
    config: NormalizationConfig,
) -> NormalizedView:
    original = np.asarray(decoded.samples, dtype=np.float32)
    if config.rate_factor != 1.0 and not config.rate_approved:
        return NormalizedView(False, np.empty(0, dtype=np.float32), decoded.sample_rate, (), "rate_transform_not_approved")
    if config.vtln_warp != 1.0 and not config.vtln_approved:
        return NormalizedView(False, np.empty(0, dtype=np.float32), decoded.sample_rate, (), "vtln_transform_not_approved")
    if config.rate_factor != 1.0 or config.vtln_warp != 1.0:
        return NormalizedView(False, np.empty(0, dtype=np.float32), decoded.sample_rate, (), "approved_transform_runtime_not_installed")
    if original.ndim != 1 or original.size == 0 or not np.isfinite(original).all():
        return NormalizedView(False, np.empty(0, dtype=np.float32), decoded.sample_rate, (), "invalid_original_view")

    normalized = original.copy()
    normalized -= float(np.mean(normalized, dtype=np.float64))
    peak = float(np.max(np.abs(normalized)))
    transforms = ["dc_remove"]
    if peak > 1e-8:
        normalized *= config.peak_target / peak
        transforms.append(f"peak_normalize:{config.peak_target:.2f}")
    if not np.isfinite(normalized).all() or float(np.max(np.abs(normalized))) > 1.0:
        return NormalizedView(False, np.empty(0, dtype=np.float32), decoded.sample_rate, tuple(transforms), "normalization_failed")
    return NormalizedView(True, normalized.astype(np.float32, copy=False), decoded.sample_rate, tuple(transforms))

