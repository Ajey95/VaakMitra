"""Create a governed Tamil OTHER manifest from extracted MLCommons CSV/audio."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.corpus import SourceRegistry  # noqa: E402
from app.vaakmitra_word.mswc import build_mswc_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv", type=Path, action="append", required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--source-registry", type=Path, required=True)
    parser.add_argument("--source-id", default="mlcommons-mswc-ta")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260906)
    args = parser.parse_args()
    registry = SourceRegistry.from_json(args.source_registry)
    source = registry.require_ingestible(args.source_id)
    count = build_mswc_manifest(
        args.csv,
        audio_root=args.audio_root,
        output_path=args.output,
        source=source,
        seed=args.seed,
    )
    print(json.dumps({"records": count, "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
