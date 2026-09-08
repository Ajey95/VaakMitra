"""Privacy-safe throughput evidence for deadline GPU decisions."""

from __future__ import annotations

import json
import os
import secrets
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

_ENVIRONMENT_FIELDS = {
    "gpu",
    "gpu_total_bytes",
    "python",
    "torch",
    "cuda",
    "bf16",
    "run_profile",
}
_SENSITIVE_FRAGMENTS = {
    "audio",
    "transcript",
    "speaker",
    "utterance",
    "token",
    "secret",
    "password",
    "path",
}


@dataclass(frozen=True, slots=True)
class StageWorkload:
    optimizer_updates: int

    def __post_init__(self) -> None:
        if self.optimizer_updates <= 0:
            raise ValueError("stage optimizer updates must be positive")


class CanaryReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    elapsed_seconds: float = Field(gt=0)
    records: int = Field(gt=0)
    audio_seconds: float = Field(gt=0)
    frames: int = Field(gt=0)
    batches: int = Field(gt=0)
    optimizer_updates: int = Field(gt=0)
    checkpoint_seconds: float = Field(ge=0)
    staging_bytes: int = Field(ge=0)
    staging_seconds: float = Field(gt=0)
    staging_mib_per_second: float = Field(ge=0)
    records_per_minute: float = Field(gt=0)
    audio_seconds_per_second: float = Field(gt=0)
    optimizer_updates_per_minute: float = Field(gt=0)
    peak_gpu_allocated_bytes: int = Field(ge=0)
    peak_gpu_reserved_bytes: int = Field(ge=0)
    peak_host_rss_bytes: int = Field(ge=0)
    environment: dict[str, str | int | bool | None]
    evidence_scope: Literal["throughput_projection_not_model_quality"] = (
        "throughput_projection_not_model_quality"
    )
    production_ready: Literal[False] = False

    @field_validator("environment")
    @classmethod
    def validate_environment(
        cls,
        value: dict[str, str | int | bool | None],
    ) -> dict[str, str | int | bool | None]:
        if set(value) != _ENVIRONMENT_FIELDS:
            raise ValueError("canary environment must use the privacy-safe field set")
        serialized = json.dumps(value, sort_keys=True).lower()
        if any(fragment in serialized for fragment in _SENSITIVE_FRAGMENTS):
            raise ValueError("canary environment must remain privacy-safe")
        if any(marker in serialized for marker in ("hf_", ":/", ":\\")):
            raise ValueError("canary environment must remain privacy-safe")
        return value

    @classmethod
    def from_measurements(
        cls,
        *,
        elapsed_seconds: float,
        records: int,
        audio_seconds: float,
        frames: int,
        batches: int,
        optimizer_updates: int,
        checkpoint_seconds: float,
        staging_bytes: int,
        staging_seconds: float,
        peak_gpu_allocated_bytes: int,
        peak_gpu_reserved_bytes: int,
        peak_host_rss_bytes: int,
        environment: dict[str, str | int | bool | None],
    ) -> Self:
        return cls(
            elapsed_seconds=elapsed_seconds,
            records=records,
            audio_seconds=audio_seconds,
            frames=frames,
            batches=batches,
            optimizer_updates=optimizer_updates,
            checkpoint_seconds=checkpoint_seconds,
            staging_bytes=staging_bytes,
            staging_seconds=staging_seconds,
            staging_mib_per_second=staging_bytes / staging_seconds / (1024 * 1024),
            records_per_minute=records / elapsed_seconds * 60,
            audio_seconds_per_second=audio_seconds / elapsed_seconds,
            optimizer_updates_per_minute=optimizer_updates / elapsed_seconds * 60,
            peak_gpu_allocated_bytes=peak_gpu_allocated_bytes,
            peak_gpu_reserved_bytes=peak_gpu_reserved_bytes,
            peak_host_rss_bytes=peak_host_rss_bytes,
            environment=environment,
        )


def project_stage_seconds(report: CanaryReport, workload: StageWorkload) -> float:
    """Project stage wall time from measured optimizer-update throughput."""

    return workload.optimizer_updates / report.optimizer_updates_per_minute * 60


def write_canary_report(path: str | Path, report: CanaryReport) -> None:
    """Atomically create canary evidence without overwriting an earlier run."""

    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(
        output_path.name + f".{os.getpid()}.{secrets.token_hex(4)}.tmp"
    )
    try:
        with temporary.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(report.model_dump(mode="json"), output, indent=2, sort_keys=True)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.link(temporary, output_path)
    finally:
        temporary.unlink(missing_ok=True)
