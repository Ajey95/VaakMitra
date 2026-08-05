"""Fail-closed integrity and extraction helpers for local speech archives."""

from __future__ import annotations

import hashlib
import posixpath
import re
import shutil
import tarfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True, slots=True)
class ArchiveInspection:
    """Immutable evidence that every tar member was safe at inspection time."""

    archive_sha256: str
    member_count: int
    file_count: int
    directory_count: int
    total_file_bytes: int
    safe_member_names: tuple[str, ...]


def sha256_file(path: Path, *, chunk_size: int = 1024 * 1024) -> str:
    """Hash a regular file without loading it into memory."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if not path.is_file():
        raise ValueError("artifact must be a regular file")
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _safe_relative_name(raw_name: str) -> str:
    if not raw_name or raw_name.startswith(("/", "\\")):
        raise ValueError(f"unsafe archive member: {raw_name!r}")
    slash_name = raw_name.replace("\\", "/")
    if _WINDOWS_DRIVE.match(slash_name):
        raise ValueError(f"unsafe archive member: {raw_name!r}")
    parts = PurePosixPath(slash_name).parts
    if not parts or any(part == ".." for part in parts):
        raise ValueError(f"unsafe archive member: {raw_name!r}")
    normalized = posixpath.normpath(slash_name)
    if normalized in ("", ".") or normalized.startswith("../"):
        raise ValueError(f"unsafe archive member: {raw_name!r}")
    return normalized


def _validated_members(
    archive: tarfile.TarFile, extraction_root: Path
) -> tuple[tuple[tarfile.TarInfo, str], ...]:
    resolved_root = extraction_root.resolve()
    seen: set[str] = set()
    validated: list[tuple[tarfile.TarInfo, str]] = []
    for member in archive.getmembers():
        if not (member.isfile() or member.isdir()):
            raise ValueError(f"unsupported archive member type: {member.name}")
        normalized = _safe_relative_name(member.name)
        duplicate_key = normalized.casefold()
        if duplicate_key in seen:
            raise ValueError(f"duplicate archive destination: {normalized}")
        seen.add(duplicate_key)
        destination = (resolved_root / Path(*PurePosixPath(normalized).parts)).resolve()
        if not destination.is_relative_to(resolved_root):
            raise ValueError(f"unsafe archive member: {member.name!r}")
        validated.append((member, normalized))
    if not validated:
        raise ValueError("archive must contain at least one member")
    return tuple(validated)


def inspect_tar_archive(path: Path, extraction_root: Path) -> ArchiveInspection:
    """Read all tar metadata and reject unsafe members without extracting them."""

    try:
        with tarfile.open(path, mode="r:gz") as archive:
            members = _validated_members(archive, extraction_root)
    except (tarfile.TarError, EOFError) as error:
        raise ValueError("archive is not a valid complete gzip tar") from error
    return ArchiveInspection(
        archive_sha256=sha256_file(path),
        member_count=len(members),
        file_count=sum(member.isfile() for member, _ in members),
        directory_count=sum(member.isdir() for member, _ in members),
        total_file_bytes=sum(member.size for member, _ in members if member.isfile()),
        safe_member_names=tuple(normalized for _, normalized in members),
    )


def extract_validated_archive(
    path: Path,
    extraction_root: Path,
    expected: ArchiveInspection,
) -> None:
    """Reinspect and extract regular files only into a new or empty destination."""

    if extraction_root.exists() and any(extraction_root.iterdir()):
        raise ValueError("extraction destination must be empty")
    current = inspect_tar_archive(path, extraction_root)
    if current != expected:
        raise ValueError("archive changed after safety inspection")
    extraction_root.mkdir(parents=True, exist_ok=True)
    resolved_root = extraction_root.resolve()
    with tarfile.open(path, mode="r:gz") as archive:
        members = _validated_members(archive, resolved_root)
        for member, normalized in members:
            destination = resolved_root / Path(*PurePosixPath(normalized).parts)
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
                continue
            destination.parent.mkdir(parents=True, exist_ok=True)
            source = archive.extractfile(member)
            if source is None:
                raise ValueError(f"unable to read archive member: {normalized}")
            with source, destination.open("xb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)

