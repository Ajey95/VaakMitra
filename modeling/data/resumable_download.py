"""Dependency-free segmented HTTP range downloader for large public corpora."""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, cast

_CONTENT_RANGE = re.compile(r"^bytes ([0-9]+)-([0-9]+)/([0-9]+)$")


@dataclass(frozen=True, slots=True)
class DownloadSegment:
    index: int
    start: int
    end: int
    path: Path

    @property
    def expected_size(self) -> int:
        return self.end - self.start + 1


def build_segments(
    *, total_size: int, segment_count: int, work_dir: Path
) -> tuple[DownloadSegment, ...]:
    """Partition an inclusive byte range into stable contiguous segment files."""

    if total_size <= 0:
        raise ValueError("total_size must be positive")
    if segment_count <= 0 or segment_count > total_size:
        raise ValueError("segment_count must be between one and total_size")
    chunk_size = (total_size + segment_count - 1) // segment_count
    segments: list[DownloadSegment] = []
    for index in range(segment_count):
        start = index * chunk_size
        if start >= total_size:
            break
        end = min(total_size - 1, start + chunk_size - 1)
        segments.append(
            DownloadSegment(
                index=index,
                start=start,
                end=end,
                path=work_dir / f"segment-{index:05d}.part",
            )
        )
    return tuple(segments)


def _response_stream(
    url: str, segment: DownloadSegment, remote_start: int, *, timeout_seconds: float
) -> BinaryIO:
    request = urllib.request.Request(
        url,
        headers={
            "Range": f"bytes={remote_start}-{segment.end}",
            "Accept-Encoding": "identity",
            "User-Agent": "VaakMitra-Corpus-Materializer/1.0",
        },
    )
    response = urllib.request.urlopen(request, timeout=timeout_seconds)
    status = getattr(response, "status", None)
    content_range = response.headers.get("Content-Range", "")
    match = _CONTENT_RANGE.fullmatch(content_range)
    if (
        status != 206
        or match is None
        or int(match.group(1)) != remote_start
        or int(match.group(2)) != segment.end
    ):
        response.close()
        raise ValueError("server did not honor the exact requested byte range")
    return cast(BinaryIO, response)


def _download_segment(
    url: str,
    segment: DownloadSegment,
    *,
    retries: int,
    timeout_seconds: float,
) -> None:
    if retries < 0:
        raise ValueError("retries must be non-negative")
    segment.path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries + 1):
        existing = segment.path.stat().st_size if segment.path.exists() else 0
        if existing > segment.expected_size:
            raise ValueError(f"download segment is oversized: {segment.index}")
        if existing == segment.expected_size:
            return
        remote_start = segment.start + existing
        try:
            with _response_stream(
                url, segment, remote_start, timeout_seconds=timeout_seconds
            ) as response, segment.path.open("ab") as output:
                while True:
                    block = response.read(1024 * 1024)
                    if not block:
                        break
                    output.write(block)
            if segment.path.stat().st_size == segment.expected_size:
                return
        except (OSError, TimeoutError, urllib.error.URLError):
            if attempt == retries:
                raise
        if attempt < retries:
            time.sleep(min(5.0, 0.25 * (2**attempt)))
    raise RuntimeError(f"download segment did not complete: {segment.index}")


def assemble_segments(
    segments: Sequence[DownloadSegment], output_path: Path, *, expected_size: int
) -> Path:
    """Concatenate complete segments atomically and validate the final byte count."""

    if not segments:
        raise ValueError("at least one segment is required")
    if output_path.exists():
        raise FileExistsError("assembled output already exists")
    for segment in segments:
        if not segment.path.is_file() or segment.path.stat().st_size != segment.expected_size:
            raise ValueError(f"segment is missing or incomplete: {segment.index}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_path.with_name(f"{output_path.name}.assembling")
    if temporary.exists():
        raise FileExistsError("assembly temporary output already exists")
    try:
        with temporary.open("xb") as output:
            for segment in segments:
                with segment.path.open("rb") as source:
                    while True:
                        block = source.read(4 * 1024 * 1024)
                        if not block:
                            break
                        output.write(block)
        if temporary.stat().st_size != expected_size:
            raise ValueError("assembled output size does not match remote metadata")
        os.replace(temporary, output_path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return output_path


def download_segmented(
    *,
    url: str,
    total_size: int,
    segment_count: int,
    work_dir: Path,
    output_path: Path,
    workers: int,
    retries: int = 8,
    timeout_seconds: float = 120.0,
) -> Path:
    """Resume all fixed ranges concurrently and assemble the exact remote object."""

    if workers <= 0 or workers > segment_count:
        raise ValueError("workers must be between one and segment_count")
    segments = build_segments(
        total_size=total_size, segment_count=segment_count, work_dir=work_dir
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = tuple(
            executor.submit(
                _download_segment,
                url,
                segment,
                retries=retries,
                timeout_seconds=timeout_seconds,
            )
            for segment in segments
        )
        for future in futures:
            future.result()
    return assemble_segments(segments, output_path, expected_size=total_size)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resume a large file over fixed HTTP ranges.")
    parser.add_argument("--url", required=True)
    parser.add_argument("--total-size", type=int, required=True)
    parser.add_argument("--segment-count", type=int, default=16)
    parser.add_argument("--workers", type=int, default=16)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--retries", type=int, default=8)
    parser.add_argument("--timeout-seconds", type=float, default=120.0)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = download_segmented(
        url=args.url,
        total_size=args.total_size,
        segment_count=args.segment_count,
        work_dir=args.work_dir,
        output_path=args.output,
        workers=args.workers,
        retries=args.retries,
        timeout_seconds=args.timeout_seconds,
    )
    print(json.dumps({"status": "complete", "path": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
