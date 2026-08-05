"""CLI for generating an explicitly provisional Epitran Tamil inventory."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from modeling.inventory.tamil_ipa import EpitranTamilTransliterator, generate_inventory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a provisional, non-expert-approved Tamil IPA inventory."
    )
    parser.add_argument("--words", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--version", required=True)
    parser.add_argument("--reduced", action="store_true")
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
    manifest = generate_inventory(
        words,
        EpitranTamilTransliterator(reduced=args.reduced),
        args.version,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as output_file:
        json.dump(manifest.as_dict(), output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")
    print(json.dumps(manifest.as_dict(), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
