from __future__ import annotations

import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from modeling.data.resumable_download import (
    assemble_segments,
    build_segments,
    download_segmented,
)
from modeling.data.resumable_download_curl import download_segmented_with_curl


class _RangeHandler(BaseHTTPRequestHandler):
    payload = b""

    def do_GET(self) -> None:
        range_header = self.headers.get("Range", "")
        if not range_header.startswith("bytes=") or "-" not in range_header:
            self.send_error(416)
            return
        raw_start, raw_end = range_header.removeprefix("bytes=").split("-", 1)
        start = int(raw_start)
        end = min(int(raw_end), len(self.payload) - 1)
        body = self.payload[start : end + 1]
        self.send_response(206)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Content-Range", f"bytes {start}-{end}/{len(self.payload)}")
        self.send_header("Accept-Ranges", "bytes")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


def test_build_segments_covers_every_byte_once(tmp_path: Path) -> None:
    segments = build_segments(total_size=10, segment_count=3, work_dir=tmp_path)

    assert [(segment.start, segment.end) for segment in segments] == [
        (0, 3),
        (4, 7),
        (8, 9),
    ]
    assert len({segment.path for segment in segments}) == 3


def test_segmented_download_resumes_prefix_and_assembles_exact_file(tmp_path: Path) -> None:
    payload = bytes(range(251)) * 100
    _RangeHandler.payload = payload
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        work = tmp_path / "segments"
        segments = build_segments(
            total_size=len(payload), segment_count=4, work_dir=work
        )
        work.mkdir(parents=True)
        first_prefix = payload[segments[0].start : segments[0].start + 317]
        segments[0].path.write_bytes(first_prefix)
        output = tmp_path / "complete.bin"

        result = download_segmented(
            url=f"http://127.0.0.1:{server.server_port}/corpus.tar.gz",
            total_size=len(payload),
            segment_count=4,
            work_dir=work,
            output_path=output,
            workers=4,
        )

        assert result == output
        assert output.read_bytes() == payload
        assert all(
            segment.path.stat().st_size == segment.expected_size
            for segment in segments
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_assembly_rejects_missing_wrong_sized_or_existing_output(tmp_path: Path) -> None:
    segments = build_segments(total_size=6, segment_count=2, work_dir=tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)
    segments[0].path.write_bytes(b"abc")

    with pytest.raises(ValueError, match="segment is missing or incomplete"):
        assemble_segments(segments, tmp_path / "output.bin", expected_size=6)

    segments[1].path.write_bytes(b"def")
    output = tmp_path / "output.bin"
    output.write_bytes(b"existing")
    with pytest.raises(FileExistsError):
        assemble_segments(segments, output, expected_size=6)


def test_curl_transport_reuses_segment_prefixes_and_assembles_exact_file(
    tmp_path: Path,
) -> None:
    payload = bytes(range(199)) * 200
    _RangeHandler.payload = payload
    server = ThreadingHTTPServer(("127.0.0.1", 0), _RangeHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        work = tmp_path / "curl-segments"
        segments = build_segments(total_size=len(payload), segment_count=3, work_dir=work)
        work.mkdir(parents=True)
        segments[0].path.write_bytes(payload[:311])

        output = download_segmented_with_curl(
            url=f"http://127.0.0.1:{server.server_port}/corpus.tar.gz",
            total_size=len(payload),
            segment_count=3,
            work_dir=work,
            output_path=tmp_path / "curl-complete.bin",
            workers=2,
            curl_executable="curl.exe",
        )

        assert output.read_bytes() == payload
        assert all(segment.path.stat().st_size == segment.expected_size for segment in segments)
        assert not tuple(work.glob("*.incoming"))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
