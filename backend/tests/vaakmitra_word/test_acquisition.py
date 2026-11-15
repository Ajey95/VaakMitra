"""Resumable, integrity-checked corpus acquisition (DATA-001/007/010/011)."""

from __future__ import annotations

import hashlib
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.vaakmitra_word.acquisition import (
    AcquisitionError,
    AcquisitionRequest,
    acquire_http_file,
    require_registered_request,
)
from app.vaakmitra_word.corpus import SourceRegistry


@pytest.fixture
def range_server() -> tuple[str, bytes, list[str | None]]:
    payload = b"governed-tamil-corpus-bytes"
    ranges: list[str | None] = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            requested_range = self.headers.get("Range")
            ranges.append(requested_range)
            start = int(requested_range.removeprefix("bytes=").removesuffix("-")) if requested_range else 0
            body = payload[start:]
            self.send_response(206 if requested_range else 200)
            self.send_header("Content-Length", str(len(body)))
            if requested_range:
                self.send_header("Content-Range", f"bytes {start}-{len(payload) - 1}/{len(payload)}")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/corpus.bin", payload, ranges
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()


def test_request_requires_pinned_source_revision_and_safe_relative_path() -> None:
    base = {
        "source_id": "approved-source",
        "url": "https://example.invalid/corpus.bin",
        "relative_path": "approved/corpus.bin",
        "sha256": "a" * 64,
        "expected_size": 12,
    }
    with pytest.raises(ValidationError):
        AcquisitionRequest.model_validate(base)
    with pytest.raises(ValidationError):
        AcquisitionRequest.model_validate({**base, "source_revision": "rev", "relative_path": "../escape.bin"})


def test_registry_gate_rejects_disabled_source_and_revision_drift() -> None:
    registry = SourceRegistry.model_validate(
        {
            "schema_version": "vaakmitra-source-registry-1",
            "sources": [
                {
                    "source_id": "approved-source",
                    "source_revision": "pinned-revision",
                    "homepage": "https://example.invalid/source",
                    "licence_id": "CC-BY-4.0",
                    "licence_url": "https://example.invalid/licence",
                    "licence_status": "verified",
                    "terms_checked_at": "2026-09-06",
                    "enabled": True,
                },
                {
                    "source_id": "disabled-source",
                    "source_revision": "pinned-revision",
                    "homepage": "https://example.invalid/disabled",
                    "licence_id": "CC-BY-4.0",
                    "licence_url": "https://example.invalid/licence",
                    "licence_status": "verified",
                    "terms_checked_at": "2026-09-06",
                    "enabled": False,
                },
            ],
        }
    )
    request = AcquisitionRequest(
        source_id="approved-source",
        source_revision="different-revision",
        url="https://example.invalid/corpus.bin",
        relative_path="approved/corpus.bin",
        sha256="a" * 64,
        expected_size=12,
    )
    with pytest.raises(AcquisitionError, match="source_revision_mismatch"):
        require_registered_request(request, registry)

    disabled = request.model_copy(
        update={"source_id": "disabled-source", "source_revision": "pinned-revision"}
    )
    with pytest.raises(AcquisitionError, match="source_disabled"):
        require_registered_request(disabled, registry)


def test_http_acquisition_resumes_partial_file_with_range(
    tmp_path: Path,
    range_server: tuple[str, bytes, list[str | None]],
) -> None:
    url, payload, observed_ranges = range_server
    request = _request(url, payload)
    partial = tmp_path / "approved" / "corpus.bin.part"
    partial.parent.mkdir(parents=True)
    partial.write_bytes(payload[:9])

    result = acquire_http_file(request, tmp_path, chunk_size=4)

    assert result.status == "downloaded"
    assert result.resumed_from == 9
    assert observed_ranges == ["bytes=9-"]
    assert result.path.read_bytes() == payload


def test_checksum_mismatch_never_promotes_partial_to_final(
    tmp_path: Path,
    range_server: tuple[str, bytes, list[str | None]],
) -> None:
    url, payload, _ = range_server
    request = _request(url, payload, sha256="0" * 64)

    with pytest.raises(AcquisitionError, match="checksum_mismatch"):
        acquire_http_file(request, tmp_path)

    assert not (tmp_path / request.relative_path).exists()
    assert (tmp_path / f"{request.relative_path}.part").exists()


def test_incomplete_archive_is_preserved_for_a_later_resume(tmp_path: Path) -> None:
    payload = b"short-response"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802 - stdlib callback name
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        request = AcquisitionRequest(
            source_id="approved-source",
            source_revision="immutable-revision",
            url=f"http://127.0.0.1:{server.server_port}/corpus.bin",
            relative_path="approved/corpus.bin",
            sha256=hashlib.sha256(payload + b"expected-tail").hexdigest(),
            expected_size=len(payload) + len(b"expected-tail"),
        )
        with pytest.raises(AcquisitionError, match="size_mismatch"):
            acquire_http_file(request, tmp_path)
    finally:
        server.shutdown()
        thread.join(timeout=2)
        server.server_close()

    assert (tmp_path / "approved" / "corpus.bin.part").read_bytes() == payload


def test_existing_unverified_file_is_not_silently_overwritten(
    tmp_path: Path,
    range_server: tuple[str, bytes, list[str | None]],
) -> None:
    url, payload, observed_ranges = range_server
    request = _request(url, payload)
    destination = tmp_path / request.relative_path
    destination.parent.mkdir(parents=True)
    destination.write_bytes(b"different-existing-data")

    with pytest.raises(AcquisitionError, match="destination_conflict"):
        acquire_http_file(request, tmp_path)

    assert destination.read_bytes() == b"different-existing-data"
    assert observed_ranges == []


def test_existing_verified_file_is_reused_without_network(
    tmp_path: Path,
    range_server: tuple[str, bytes, list[str | None]],
) -> None:
    url, payload, observed_ranges = range_server
    request = _request(url, payload)
    destination = tmp_path / request.relative_path
    destination.parent.mkdir(parents=True)
    destination.write_bytes(payload)

    result = acquire_http_file(request, tmp_path)

    assert result.status == "reused"
    assert result.sha256 == request.sha256
    assert observed_ranges == []


def test_acquisition_cli_runs_directly_from_backend_root() -> None:
    backend_root = Path(__file__).resolve().parents[2]
    completed = subprocess.run(
        [sys.executable, "scripts/corpus/acquire.py", "--help"],
        cwd=backend_root,
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    assert "--source-revision" in completed.stdout


def _request(url: str, payload: bytes, *, sha256: str | None = None) -> AcquisitionRequest:
    return AcquisitionRequest(
        source_id="approved-source",
        source_revision="immutable-revision",
        url=url,
        relative_path="approved/corpus.bin",
        sha256=sha256 or hashlib.sha256(payload).hexdigest(),
        expected_size=len(payload),
    )
