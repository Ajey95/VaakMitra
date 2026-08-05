"""Curl-backed fixed-range downloader for mirrors that stall urllib responses."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from modeling.data.resumable_download import (
    DownloadSegment,
    assemble_segments,
    build_segments,
)


def _merge_incoming(segment: DownloadSegment) -> None:
    incoming = segment.path.with_suffix(segment.path.suffix + ".incoming")
    if not incoming.exists():
        return
    existing = segment.path.stat().st_size if segment.path.exists() else 0
    incoming_size = incoming.stat().st_size
    remaining = segment.expected_size - existing
    if remaining < 0 or incoming_size > remaining:
        raise ValueError(f"curl range artifact is oversized: {segment.index}")
    if incoming_size:
        segment.path.parent.mkdir(parents=True, exist_ok=True)
        with segment.path.open("ab") as output, incoming.open("rb") as source:
            shutil.copyfileobj(source, output, length=4 * 1024 * 1024)
    incoming.unlink()


def _download_segment_with_curl(
    *,
    url: str,
    segment: DownloadSegment,
    curl_executable: str,
    retries: int,
) -> None:
    segment.path.parent.mkdir(parents=True, exist_ok=True)
    for attempt in range(retries + 1):
        _merge_incoming(segment)
        existing = segment.path.stat().st_size if segment.path.exists() else 0
        if existing > segment.expected_size:
            raise ValueError(f"download segment is oversized: {segment.index}")
        if existing == segment.expected_size:
            return
        remote_start = segment.start + existing
        incoming = segment.path.with_suffix(segment.path.suffix + ".incoming")
        if incoming.exists():
            raise FileExistsError(f"unexpected curl range artifact: {segment.index}")
        result = subprocess.run(
            (
                curl_executable,
                "--location",
                "--fail",
                "--speed-limit",
                "1024",
                "--speed-time",
                "30",
                "--max-time",
                "180",
                "--range",
                f"{remote_start}-{segment.end}",
                "--output",
                str(incoming),
                url,
            ),
            check=False,
        )
        progress = incoming.stat().st_size if incoming.exists() else 0
        if progress:
            _merge_incoming(segment)
            continue
        incoming.unlink(missing_ok=True)
        if attempt == retries:
            raise RuntimeError(f"curl range download made no progress: {segment.index}")
        if result.returncode == 0:
            raise ValueError(f"curl returned no bytes for range: {segment.index}")
    raise RuntimeError(f"curl segment retry budget exhausted: {segment.index}")


def download_segmented_with_curl(
    *,
    url: str,
    total_size: int,
    segment_count: int,
    work_dir: Path,
    output_path: Path,
    workers: int,
    curl_executable: str = "curl",
    retries: int = 20,
) -> Path:
    """Complete fixed ranges using curl, then reuse the strict atomic assembler."""

    if workers <= 0 or workers > segment_count:
        raise ValueError("workers must be between one and segment_count")
    if retries < 0:
        raise ValueError("retries must be non-negative")
    segments = build_segments(
        total_size=total_size, segment_count=segment_count, work_dir=work_dir
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = tuple(
            executor.submit(
                _download_segment_with_curl,
                url=url,
                segment=segment,
                curl_executable=curl_executable,
                retries=retries,
            )
            for segment in segments
        )
        for future in futures:
            future.result()
    return assemble_segments(segments, output_path, expected_size=total_size)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resume fixed HTTP ranges through curl and assemble an exact file."
    )
    parser.add_argument("--url", required=True)
    parser.add_argument("--total-size", type=int, required=True)
    parser.add_argument("--segment-count", type=int, default=16)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--curl", default="curl")
    parser.add_argument("--retries", type=int, default=20)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    output = download_segmented_with_curl(
        url=args.url,
        total_size=args.total_size,
        segment_count=args.segment_count,
        work_dir=args.work_dir,
        output_path=args.output,
        workers=args.workers,
        curl_executable=args.curl,
        retries=args.retries,
    )
    print(json.dumps({"status": "complete", "path": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
