"""CLI for local JSONL phoneme evaluation with aggregate-only output."""

from __future__ import annotations

import argparse
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from modeling.evaluation.ctc_metrics import EvaluationRecord, evaluate_records


def _string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise TypeError(f"{field_name} must be a JSON array of strings")
    return tuple(value)


def _string_value(row: Mapping[str, Any], field_name: str) -> str:
    value = row.get(field_name)
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    return value


def _record_from_row(row: object) -> EvaluationRecord:
    if not isinstance(row, dict):
        raise TypeError("each JSONL row must be an object")
    scorable = row.get("scorable", True)
    if not isinstance(scorable, bool):
        raise TypeError("scorable must be a boolean")
    return EvaluationRecord(
        utterance_id=_string_value(row, "utterance_id"),
        reference=_string_tuple(row.get("reference"), "reference"),
        predicted_tokens=_string_tuple(row.get("predicted_tokens"), "predicted_tokens"),
        blank_token=_string_value(row, "blank_token"),
        population=_string_value(row, "population"),
        evidence_scope=_string_value(row, "evidence_scope"),
        scorable=scorable,
    )


def load_jsonl(path: str | Path) -> tuple[EvaluationRecord, ...]:
    records: list[EvaluationRecord] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            records.append(_record_from_row(json.loads(line)))
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid evaluation row {line_number}: {error}") from error
    return tuple(records)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Evaluate frozen local phoneme CTC JSONL into aggregate proxy evidence."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = evaluate_records(load_jsonl(args.input))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report.as_dict(), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
