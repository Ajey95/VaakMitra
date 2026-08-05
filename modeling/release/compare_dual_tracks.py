"""CLI for assembling a hash-linked dual-track comparison report."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import TypeAdapter

from modeling.release.dual_track_comparison import (
    ComparisonCandidate,
    compare_dual_tracks,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare full reference, edge students, and historical proxy evidence."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidates = TypeAdapter(tuple[ComparisonCandidate, ...]).validate_json(
        args.input.read_text(encoding="utf-8")
    )
    report = compare_dual_tracks(candidates)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report.as_dict(), output, indent=2, ensure_ascii=False)
        output.write("\n")
    print(
        json.dumps(
            {
                "status": "ok",
                "edge_selection_status": report.edge_selection_status,
                "selected_edge_model_id": report.selected_edge_model_id,
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
