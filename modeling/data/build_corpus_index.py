"""CLI for freezing aggregate corpus split evidence from private local indexes."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from modeling.data.corpus_index import (
    CorpusRecord,
    CorpusSource,
    freeze_corpus_index,
    write_frozen_corpus_index,
)


def load_corpus_records(path: Path) -> tuple[CorpusRecord, ...]:
    """Load strict JSONL records containing digests and identifiers but no paths/text."""

    lines = tuple(line for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    if not lines:
        raise ValueError("corpus record JSONL must be non-empty")
    return tuple(CorpusRecord.model_validate_json(line) for line in lines)


def load_assignments(path: Path) -> dict[str, str]:
    """Load speaker-to-split assignments used only before aggregate index freezing."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, Mapping) or not payload:
        raise TypeError("assignments must be a non-empty JSON object")
    result: dict[str, str] = {}
    for speaker, split_name in payload.items():
        if not isinstance(speaker, str) or not speaker.strip():
            raise TypeError("assignment speaker identifiers must be non-empty strings")
        if not isinstance(split_name, str):
            raise TypeError("assignment split names must be strings")
        result[speaker.strip()] = split_name.strip()
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Freeze a privacy-safe aggregate Tamil corpus index."
    )
    parser.add_argument("--records", type=Path, required=True)
    parser.add_argument("--assignments", type=Path, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    source = CorpusSource.model_validate_json(args.source.read_text(encoding="utf-8"))
    index = freeze_corpus_index(
        load_corpus_records(args.records),
        load_assignments(args.assignments),
        source,
    )
    write_frozen_corpus_index(args.output, index)
    print(
        json.dumps(
            {
                "status": "ok",
                "record_count": index.record_count,
                "speaker_count": index.speaker_count,
                "evidence_scope": index.evidence_scope,
                "corpus_index_sha256": index.digest(),
            },
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
