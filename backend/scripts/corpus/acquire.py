"""Acquire one approved corpus artifact and emit a machine-readable report."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.acquisition import (
    AcquisitionRequest,
    acquire_http_file,
    require_registered_request,
)
from app.vaakmitra_word.corpus import SourceRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--source-revision", required=True)
    parser.add_argument("--url", required=True)
    parser.add_argument("--relative-path", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--expected-size", type=int, required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    registry = SourceRegistry.from_json(args.registry)
    request = AcquisitionRequest(
        source_id=args.source_id,
        source_revision=args.source_revision,
        url=args.url,
        relative_path=args.relative_path,
        sha256=args.sha256,
        expected_size=args.expected_size,
    )
    require_registered_request(request, registry)
    result = acquire_http_file(request, args.cache_root)
    report = {
        "schema_version": "vaakmitra-acquisition-report-1",
        "created_at_utc": datetime.now(UTC).isoformat(),
        "result": {
            **result.model_dump(mode="json"),
            "path": str(result.path),
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
