"""Safe, resumable acquisition primitives for governed adult corpora.

The downloader deliberately knows nothing about clinical labels.  It only
promotes a file after its pinned size and SHA-256 are verified (DATA-001,
DATA-007, DATA-010, DATA-011).
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Literal
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .corpus import CorpusManifestError, SourceEntry, SourceRegistry


class AcquisitionError(RuntimeError):
    """Raised when an artifact cannot be acquired without weakening a gate."""


class AcquisitionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: str = Field(min_length=1)
    source_revision: str = Field(min_length=1)
    url: str = Field(pattern=r"^https?://")
    relative_path: str = Field(min_length=1)
    sha256: str
    expected_size: int = Field(gt=0)

    @field_validator("relative_path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("relative_path must remain inside the acquisition cache")
        return value

    @field_validator("sha256")
    @classmethod
    def valid_sha256(cls, value: str) -> str:
        normalized = value.lower()
        if len(normalized) != 64 or any(character not in "0123456789abcdef" for character in normalized):
            raise ValueError("sha256 must be lowercase hexadecimal SHA-256")
        return normalized


class AcquisitionResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    source_id: str
    source_revision: str
    status: Literal["downloaded", "reused"]
    path: Path
    size: int
    sha256: str
    resumed_from: int


def require_registered_request(
    request: AcquisitionRequest,
    registry: SourceRegistry,
) -> SourceEntry:
    """Fail closed unless source status and immutable revision match the registry."""
    try:
        source = registry.require_ingestible(request.source_id)
    except CorpusManifestError as exc:
        raise AcquisitionError(str(exc)) from exc
    if source.source_revision != request.source_revision:
        raise AcquisitionError(
            f"source_revision_mismatch:registry={source.source_revision}:requested={request.source_revision}"
        )
    return source


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def acquire_http_file(
    request: AcquisitionRequest,
    cache_root: Path | str,
    *,
    chunk_size: int = 1024 * 1024,
    timeout_seconds: float = 60.0,
) -> AcquisitionResult:
    """Download one pinned artifact and atomically promote it after verification."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    root = Path(cache_root).resolve()
    destination = (root / request.relative_path).resolve()
    try:
        destination.relative_to(root)
    except ValueError as exc:  # defensive check beyond Pydantic's lexical gate
        raise AcquisitionError("destination_outside_cache") from exc
    destination.parent.mkdir(parents=True, exist_ok=True)

    if destination.exists():
        if not destination.is_file():
            raise AcquisitionError("destination_conflict:not_a_file")
        existing_size = destination.stat().st_size
        existing_hash = sha256_file(destination, chunk_size=chunk_size)
        if existing_size != request.expected_size or existing_hash != request.sha256:
            raise AcquisitionError("destination_conflict:existing_file_not_verified")
        return AcquisitionResult(
            source_id=request.source_id,
            source_revision=request.source_revision,
            status="reused",
            path=destination,
            size=existing_size,
            sha256=existing_hash,
            resumed_from=existing_size,
        )

    partial = Path(f"{destination}.part")
    resumed_from = partial.stat().st_size if partial.exists() else 0
    if resumed_from > request.expected_size:
        raise AcquisitionError("partial_size_exceeds_expected")

    headers = {"User-Agent": "VaakMitra-governed-acquisition/1"}
    if resumed_from:
        headers["Range"] = f"bytes={resumed_from}-"

    try:
        with urlopen(Request(request.url, headers=headers), timeout=timeout_seconds) as response:
            status = getattr(response, "status", response.getcode())
            if resumed_from and status != 206:
                raise AcquisitionError("range_not_honoured")
            if resumed_from:
                expected_prefix = f"bytes {resumed_from}-"
                if not (response.headers.get("Content-Range") or "").startswith(expected_prefix):
                    raise AcquisitionError("content_range_mismatch")
            mode = "ab" if resumed_from else "wb"
            with partial.open(mode) as sink:
                while chunk := response.read(chunk_size):
                    sink.write(chunk)
    except AcquisitionError:
        raise
    except (HTTPError, URLError, OSError) as exc:
        raise AcquisitionError(f"transport_error:{type(exc).__name__}") from exc

    actual_size = partial.stat().st_size
    if actual_size != request.expected_size:
        raise AcquisitionError(f"size_mismatch:expected={request.expected_size}:actual={actual_size}")
    actual_hash = sha256_file(partial, chunk_size=chunk_size)
    if actual_hash != request.sha256:
        raise AcquisitionError(f"checksum_mismatch:expected={request.sha256}:actual={actual_hash}")

    partial.replace(destination)
    return AcquisitionResult(
        source_id=request.source_id,
        source_revision=request.source_revision,
        status="downloaded",
        path=destination,
        size=actual_size,
        sha256=actual_hash,
        resumed_from=resumed_from,
    )
