"""Create a governed sentence-candidate manifest from extracted OpenSLR 65."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.corpus import SourceRegistry  # noqa: E402
from app.vaakmitra_word.openslr65 import OpenSlr65Partition, build_openslr65_manifest  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus-root", type=Path, required=True)
    parser.add_argument("--partition-root", type=Path, action="append", required=True)
    parser.add_argument("--source-registry", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260906)
    args = parser.parse_args()
    registry = SourceRegistry.from_json(args.source_registry)
    source = registry.require_ingestible("openslr-65-ta")
    partitions = tuple(
        OpenSlr65Partition(index_path=root / "line_index.tsv", audio_root=root)
        for root in args.partition_root
    )
    count = build_openslr65_manifest(
        partitions,
        corpus_root=args.corpus_root,
        output_path=args.output,
        source=source,
        seed=args.seed,
    )
    print(json.dumps({"records": count, "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
