"""Shared immutable metadata for generated model artifacts."""

from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ArtifactRecord:
    """Size and digest evidence for a generated local artifact."""

    path: str
    size_bytes: int
    sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def describe_artifact(path: str | Path) -> ArtifactRecord:
    artifact = Path(path)
    if not artifact.is_file() or artifact.stat().st_size == 0:
        raise ValueError("artifact must be a non-empty file")
    digest = hashlib.sha256()
    with artifact.open("rb") as artifact_file:
        while chunk := artifact_file.read(1024 * 1024):
            digest.update(chunk)
    return ArtifactRecord(
        path=str(artifact),
        size_bytes=artifact.stat().st_size,
        sha256=digest.hexdigest(),
    )

