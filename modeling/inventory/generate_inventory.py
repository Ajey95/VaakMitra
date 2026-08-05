"""CLI for generating an explicitly provisional Epitran Tamil inventory."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import TypeAdapter

from modeling.inventory.consensus import (
    AllophoneRule,
    InventorySource,
    build_candidate_inventory,
    load_inventory_sources,
)
from modeling.inventory.tamil_ipa import EpitranTamilTransliterator, generate_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a provisional, non-expert-approved Tamil IPA inventory."
    )
    parser.add_argument("--words", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--reduced", action="store_true")
    parser.add_argument(
        "--consensus-sources",
        type=Path,
        help="Optional pinned published-source catalog to produce a candidate consensus.",
    )
    parser.add_argument(
        "--transliterator-revision",
        help="Immutable Epitran revision; required with --consensus-sources.",
    )
    parser.add_argument(
        "--allophones",
        type=Path,
        help="Optional JSON array of explicit acoustic-only allophone rules.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.output.exists():
        raise ValueError("inventory output exists")
    words = tuple(
        line.strip()
        for line in args.words.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    generated = generate_inventory(
        words,
        EpitranTamilTransliterator(reduced=args.reduced),
        args.version,
    )
    payload = generated.as_dict()
    if args.consensus_sources is not None:
        if not args.transliterator_revision:
            raise ValueError(
                "--transliterator-revision is required with --consensus-sources"
            )
        generated_units = tuple(
            sorted({unit for entry in generated.lexicon for unit in entry.units})
        )
        transliterator_source = InventorySource(
            source_id="epitran-tam-Taml-red" if args.reduced else "epitran-tam-Taml",
            revision=args.transliterator_revision,
            source_scope="transliterator",
            segments=generated_units,
        )
        allophones: tuple[AllophoneRule, ...] = ()
        if args.allophones is not None:
            allophones = TypeAdapter(tuple[AllophoneRule, ...]).validate_json(
                args.allophones.read_text(encoding="utf-8")
            )
        candidate = build_candidate_inventory(
            sources=(*load_inventory_sources(args.consensus_sources), transliterator_source),
            observed_units=generated_units,
            allophones=allophones,
            version=args.version,
        )
        payload = candidate.as_dict()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as output_file:
        json.dump(payload, output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
