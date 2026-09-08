"""Strict training profiles and immutable run bindings for deadline GPU work."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

StageName = Literal["head_only", "top_encoder_blocks", "full_encoder"]
SplitName = Literal["train", "validation", "test"]
TRAINING_CONTRACT_VERSION = "2.0"


class TrainingProfileName(str, Enum):
    SMOKE = "smoke"
    DEADLINE_7DAY = "deadline_7day"
    RESEARCH_FULL = "research_full"


class TrainingProfile(BaseModel):
    """One validated execution schedule loaded from the checked-in catalog."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    name: TrainingProfileName
    reference_epochs: dict[StageName, int]
    student_epochs: int = Field(ge=0)
    maximum_students: int = Field(ge=0, le=2)
    batch_size: int = Field(gt=0)
    gradient_accumulation: int = Field(gt=0)
    bucket_size: int = Field(gt=0)
    checkpoint_every_updates: int = Field(gt=0)
    session_max_seconds: int = Field(gt=0)
    session_reserve_seconds: int = Field(gt=0)
    minimum_full_stage_per_improvement: float = Field(ge=0.0)
    maximum_unknown_phone_record_rate: float = Field(ge=0.0, le=1.0)
    split_limits: dict[SplitName, int | None]

    @model_validator(mode="after")
    def validate_schedule(self) -> TrainingProfile:
        expected_stages = {"head_only", "top_encoder_blocks", "full_encoder"}
        if set(self.reference_epochs) != expected_stages:
            raise ValueError("reference epochs must contain exactly the three training stages")
        if any(epochs < 0 for epochs in self.reference_epochs.values()):
            raise ValueError("reference epochs must be non-negative")
        if set(self.split_limits) != {"train", "validation", "test"}:
            raise ValueError("split limits must contain train, validation, and test")
        if any(limit is not None and limit <= 0 for limit in self.split_limits.values()):
            raise ValueError("split limits must be positive or null")
        if self.bucket_size < self.batch_size:
            raise ValueError("bucket size must be at least batch size")
        if self.session_reserve_seconds >= self.session_max_seconds:
            raise ValueError("session reserve must be shorter than session maximum")
        return self


class _ProfileCatalog(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"]
    profiles: tuple[TrainingProfile, ...]


def load_training_profile(path: str | Path, name: str) -> TrainingProfile:
    """Load one uniquely named profile from a strict JSON catalog."""

    profile_path = Path(path)
    payload = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or not isinstance(payload.get("profiles"), list):
        raise TypeError("training profile catalog must contain a profile list")
    raw_names = [item.get("name") for item in payload["profiles"] if isinstance(item, dict)]
    if len(raw_names) != len(set(raw_names)):
        raise ValueError("duplicate training profile name")
    catalog = _ProfileCatalog.model_validate(payload)
    matches = [profile for profile in catalog.profiles if profile.name.value == name]
    if len(matches) != 1:
        raise ValueError(f"training profile not found: {name}")
    return matches[0]


_IMMUTABLE_FIELDS = {
    "archive_sha256",
    "corpus_index_sha256",
    "inventory_sha256",
    "teacher_model_id",
    "teacher_revision",
    "teacher_checkpoint_sha256",
    "repository_commit",
}


def build_run_binding(
    profile: TrainingProfile,
    immutable_inputs: Mapping[str, str],
) -> dict[str, object]:
    """Bind a training run to its complete profile and immutable inputs."""

    if set(immutable_inputs) != _IMMUTABLE_FIELDS:
        raise ValueError("immutable run-binding fields differ")
    if any(not isinstance(value, str) or not value for value in immutable_inputs.values()):
        raise ValueError("immutable run-binding values must be non-empty strings")
    payload: dict[str, object] = {
        "schema_version": "2.0",
        "profile": profile.model_dump(mode="json"),
        "inputs": dict(sorted(immutable_inputs.items())),
        "evidence_scope": "adult_tamil_engineering_proxy",
        "production_ready": False,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    payload["binding_sha256"] = hashlib.sha256(canonical).hexdigest()
    return payload
