"""Preprocess one governed adult-corpus manifest into immutable 16 kHz WAVs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.corpus_preprocessing import preprocess_manifest  # noqa: E402
from app.vaakmitra_word.vocabulary import VocabularyRegistry  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=20260906)
    args = parser.parse_args()

    report = preprocess_manifest(
        args.manifest,
        audio_root=args.audio_root,
        output_root=args.output_root,
        registry=VocabularyRegistry.from_json(args.vocabulary),
        seed=args.seed,
    )
    print(
        json.dumps(
            {
                "accepted": report.accepted,
                "rejected": report.rejected,
                "rejection_counts": report.rejection_counts,
                "manifest_path": str(report.manifest_path),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
