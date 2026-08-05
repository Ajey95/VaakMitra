"""Curl-backed fixed-range downloader for mirrors that stall urllib responses."""

from __future__ import annotations

import argparse
import json
import os
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


def _tail_chunks(
    segment: DownloadSegment,
    *,
    existing_size: int,
    chunk_size: int,
) -> tuple[DownloadSegment, ...]:
    start = segment.start + existing_size
    chunks: list[DownloadSegment] = []
    index = 0
    while start <= segment.end:
        end = min(segment.end, start + chunk_size - 1)
        chunks.append(
            DownloadSegment(
                index=segment.index * 1_000_000 + index,
                start=start,
                end=end,
                path=(
                    segment.path.parent
                    / "tail-chunks"
                    / f"segment-{segment.index:05d}"
                    / f"chunk-{index:05d}.part"
                ),
            )
        )
        start = end + 1
        index += 1
    return tuple(chunks)


def _replace_segment_with_tail(
    segment: DownloadSegment,
    *,
    prefix_size: int,
    tail_chunks: Sequence[DownloadSegment],
) -> None:
    current_size = segment.path.stat().st_size if segment.path.exists() else 0
    if current_size != prefix_size:
        raise ValueError(f"download segment changed during tail transfer: {segment.index}")
    for chunk in tail_chunks:
        if not chunk.path.is_file() or chunk.path.stat().st_size != chunk.expected_size:
            raise ValueError(f"tail chunk is missing or incomplete: {chunk.index}")
    temporary = segment.path.with_suffix(segment.path.suffix + ".tail-assembling")
    temporary.unlink(missing_ok=True)
    try:
        temporary.parent.mkdir(parents=True, exist_ok=True)
        with temporary.open("xb") as output:
            if segment.path.exists():
                with segment.path.open("rb") as source:
                    shutil.copyfileobj(source, output, length=4 * 1024 * 1024)
            for chunk in tail_chunks:
                with chunk.path.open("rb") as source:
                    shutil.copyfileobj(source, output, length=4 * 1024 * 1024)
        if temporary.stat().st_size != segment.expected_size:
            raise ValueError(f"rebuilt segment has the wrong size: {segment.index}")
        os.replace(temporary, segment.path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def download_missing_segment_tails_with_curl(
    *,
    url: str,
    total_size: int,
    segment_count: int,
    work_dir: Path,
    output_path: Path,
    workers: int,
    tail_chunk_size: int,
    curl_executable: str = "curl",
    retries: int = 20,
) -> Path:
    """Parallelize only missing segment suffixes, then rebuild and assemble exactly."""

    if workers <= 0:
        raise ValueError("workers must be positive")
    if tail_chunk_size <= 0:
        raise ValueError("tail_chunk_size must be positive")
    if retries < 0:
        raise ValueError("retries must be non-negative")
    segments = build_segments(
        total_size=total_size, segment_count=segment_count, work_dir=work_dir
    )
    plans: list[tuple[DownloadSegment, int, tuple[DownloadSegment, ...]]] = []
    for segment in segments:
        _merge_incoming(segment)
        existing = segment.path.stat().st_size if segment.path.exists() else 0
        if existing > segment.expected_size:
            raise ValueError(f"download segment is oversized: {segment.index}")
        if existing < segment.expected_size:
            plans.append(
                (
                    segment,
                    existing,
                    _tail_chunks(
                        segment,
                        existing_size=existing,
                        chunk_size=tail_chunk_size,
                    ),
                )
            )
    chunks = tuple(chunk for _, _, tail in plans for chunk in tail)
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = tuple(
            executor.submit(
                _download_segment_with_curl,
                url=url,
                segment=chunk,
                curl_executable=curl_executable,
                retries=retries,
            )
            for chunk in chunks
        )
        for future in futures:
            future.result()
    for segment, prefix_size, tail in plans:
        _replace_segment_with_tail(
            segment,
            prefix_size=prefix_size,
            tail_chunks=tail,
        )
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
    parser.add_argument(
        "--tail-chunk-size",
        type=int,
        help="Split only missing segment suffixes into chunks of this many bytes.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.tail_chunk_size is None:
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
    else:
        output = download_missing_segment_tails_with_curl(
            url=args.url,
            total_size=args.total_size,
            segment_count=args.segment_count,
            work_dir=args.work_dir,
            output_path=args.output,
            workers=args.workers,
            tail_chunk_size=args.tail_chunk_size,
            curl_executable=args.curl,
            retries=args.retries,
        )
    print(json.dumps({"status": "complete", "path": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
