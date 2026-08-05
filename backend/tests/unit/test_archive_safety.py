from __future__ import annotations

import hashlib
import io
import tarfile
from pathlib import Path

import pytest
from modeling.data.archive_safety import (
    extract_validated_archive,
    inspect_tar_archive,
    sha256_file,
)


def _write_tar(
    path: Path,
    files: dict[str, bytes],
    *,
    special: tarfile.TarInfo | None = None,
) -> Path:
    with tarfile.open(path, "w:gz") as archive:
        for name, content in files.items():
            member = tarfile.TarInfo(name)
            member.size = len(content)
            archive.addfile(member, io.BytesIO(content))
        if special is not None:
            archive.addfile(special)
    return path


def test_sha256_file_streams_the_complete_artifact(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact.bin"
    artifact.write_bytes(b"abc" * 100_000)

    assert sha256_file(artifact) == hashlib.sha256(b"abc" * 100_000).hexdigest()


def test_inspection_accepts_only_regular_files_and_directories(tmp_path: Path) -> None:
    archive = _write_tar(
        tmp_path / "safe.tar.gz",
        {
            "mile/train/audio_files/a.wav": b"audio",
            "mile/train/trans_files/a.txt": "தமிழ்".encode(),
        },
    )

    report = inspect_tar_archive(archive, tmp_path / "extract")

    assert report.member_count == 2
    assert report.file_count == 2
    assert report.total_file_bytes == 5 + len("தமிழ்".encode())
    assert report.safe_member_names == (
        "mile/train/audio_files/a.wav",
        "mile/train/trans_files/a.txt",
    )
    assert report.archive_sha256 == sha256_file(archive)


@pytest.mark.parametrize(
    "unsafe_name",
    (
        "../escape.txt",
        "mile/../../escape.txt",
        "/absolute.txt",
        "C:/drive-qualified.txt",
        "C:\\drive-qualified.txt",
    ),
)
def test_inspection_rejects_unsafe_member_paths_before_extraction(
    tmp_path: Path, unsafe_name: str
) -> None:
    archive = _write_tar(tmp_path / "bad.tar.gz", {unsafe_name: b"x"})

    with pytest.raises(ValueError, match="unsafe archive member"):
        inspect_tar_archive(archive, tmp_path / "extract")

    assert not (tmp_path / "escape.txt").exists()


def test_inspection_rejects_links_and_duplicate_normalized_destinations(
    tmp_path: Path,
) -> None:
    link = tarfile.TarInfo("mile/link")
    link.type = tarfile.SYMTYPE
    link.linkname = "../outside"
    linked = _write_tar(tmp_path / "link.tar.gz", {}, special=link)

    with pytest.raises(ValueError, match="unsupported archive member type"):
        inspect_tar_archive(linked, tmp_path / "extract-link")

    duplicate = tmp_path / "duplicate.tar.gz"
    with tarfile.open(duplicate, "w:gz") as archive:
        for name in ("mile/train/a.txt", "mile/train/./a.txt"):
            member = tarfile.TarInfo(name)
            member.size = 1
            archive.addfile(member, io.BytesIO(b"x"))

    with pytest.raises(ValueError, match="duplicate archive destination"):
        inspect_tar_archive(duplicate, tmp_path / "extract-duplicate")


def test_validated_extraction_refuses_nonempty_destination_and_writes_inside_root(
    tmp_path: Path,
) -> None:
    archive = _write_tar(
        tmp_path / "safe.tar.gz",
        {"mile/train/trans_files/a.txt": "தமிழ்".encode()},
    )
    destination = tmp_path / "extract"
    report = inspect_tar_archive(archive, destination)

    extract_validated_archive(archive, destination, report)

    assert (destination / "mile/train/trans_files/a.txt").read_text(
        encoding="utf-8"
    ) == "தமிழ்"
    with pytest.raises(ValueError, match="destination must be empty"):
        extract_validated_archive(archive, destination, report)
