"""CLI for a private OpenSLR lexicon and bounded Tamil expert-review packet."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import TypeAdapter

from modeling.inventory.consensus import AllophoneRule, load_inventory_sources
from modeling.inventory.corpus_lexicon import (
    build_corpus_lexicon,
    build_corpus_review_packet,
    write_corpus_review_packet,
    write_private_lexicon,
)
from modeling.inventory.tamil_ipa import EpitranTamilTransliterator


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate private Tamil lexicon and bounded clinician-review evidence."
    )
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--extract-root", required=True, type=Path)
    parser.add_argument("--archive-sha256", required=True)
    parser.add_argument("--sources", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--private-lexicon", required=True, type=Path)
    parser.add_argument("--review-output-dir", required=True, type=Path)
    parser.add_argument("--allophones", type=Path)
    parser.add_argument("--max-examples", type=int, default=200)
    parser.add_argument("--sample-seed", default="vaakmitra-clinician-review-v1")
    parser.add_argument("--reduced", action="store_true")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    allophones: tuple[AllophoneRule, ...] = ()
    if args.allophones is not None:
        allophones = TypeAdapter(tuple[AllophoneRule, ...]).validate_json(
            args.allophones.read_text(encoding="utf-8")
        )
    lexicon = build_corpus_lexicon(
        records_path=args.records,
        extracted_root=args.extract_root,
        archive_sha256=args.archive_sha256,
        transliterator=EpitranTamilTransliterator(reduced=args.reduced),
    )
    packet = build_corpus_review_packet(
        lexicon=lexicon,
        sources=load_inventory_sources(args.sources),
        allophones=allophones,
        version=args.version,
        max_examples=args.max_examples,
        sample_seed=args.sample_seed,
    )
    write_private_lexicon(args.private_lexicon, lexicon)
    write_corpus_review_packet(args.review_output_dir, packet)
    print(
        json.dumps(
            {
                "status": "pending_expert_review",
                "archive_sha256": packet.archive_sha256,
                "lexicon_digest": packet.lexicon_digest,
                "candidate_digest": packet.candidate.digest(),
                "packet_digest": packet.digest(),
                "review_output_dir": str(args.review_output_dir),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
