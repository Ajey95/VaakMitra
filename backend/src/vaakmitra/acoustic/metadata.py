"""Integrity-checked metadata for locally packaged acoustic models."""

from __future__ import annotations

import hashlib
import hmac
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ModelIntegrityError(ValueError):
    """Raised when a model file is absent or does not match its manifest."""


class ModelManifest(BaseModel):
    """Versioned tensor and integrity contract for one local model artifact."""

    model_config = ConfigDict(frozen=True)

    schema_version: str = Field(min_length=1)
    model_version: str = Field(min_length=1)
    vocabulary_version: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    sample_rate: Literal[16000]
    frame_shift_ms: float = Field(gt=0)
    blank_index: int = Field(ge=0)
    vocabulary_size: int = Field(gt=1)
    input_name: str = Field(min_length=1)
    output_name: str = Field(min_length=1)
    output_kind: Literal["log_probabilities", "logits"]

    @classmethod
    def from_json(cls, path: str | Path) -> ModelManifest:
        """Load and validate a UTF-8 JSON manifest."""

        return cls.model_validate_json(Path(path).read_text(encoding="utf-8"))


def verify_model_integrity(path: str | Path, manifest: ModelManifest) -> None:
    """Stream a model file through SHA-256 and compare in constant time."""

    model_path = Path(path)
    if not model_path.is_file():
        raise ModelIntegrityError("model file is missing")
    digest = hashlib.sha256()
    with model_path.open("rb") as model_file:
        while chunk := model_file.read(1024 * 1024):
            digest.update(chunk)
    if not hmac.compare_digest(digest.hexdigest(), manifest.sha256):
        raise ModelIntegrityError("model SHA-256 does not match manifest")

