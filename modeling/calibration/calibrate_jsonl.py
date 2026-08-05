"""CLI for aggregate-only, proxy-labelled GOP/confidence calibration."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from modeling.calibration.proxy_calibration import (
    ProxyCalibrationExample,
    calibrate_proxy_thresholds,
)


def _example_from_row(row: object) -> ProxyCalibrationExample:
    if not isinstance(row, dict):
        raise TypeError("each JSONL row must be an object")
    example_id = row.get("example_id")
    if not isinstance(example_id, str):
        raise TypeError("example_id must be a string")
    score_value = row.get("score")
    if score_value is not None and (
        isinstance(score_value, bool) or not isinstance(score_value, (int, float))
    ):
        raise TypeError("score must be numeric or null")
    acceptable = row.get("acceptable")
    if acceptable is not None and not isinstance(acceptable, bool):
        raise TypeError("acceptable must be a boolean or null")
    return ProxyCalibrationExample(
        example_id=example_id,
        score=float(score_value) if score_value is not None else None,
        acceptable=acceptable,
    )


def load_jsonl(path: str | Path) -> tuple[ProxyCalibrationExample, ...]:
    examples: list[ProxyCalibrationExample] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), start=1):
        if not line.strip():
            continue
        try:
            examples.append(_example_from_row(json.loads(line)))
        except (json.JSONDecodeError, TypeError, ValueError) as error:
            raise ValueError(f"invalid calibration row {line_number}: {error}") from error
    return tuple(examples)


def _parse_thresholds(raw: str) -> tuple[float, ...]:
    try:
        return tuple(float(value.strip()) for value in raw.split(",") if value.strip())
    except ValueError as error:
        raise ValueError("candidate thresholds must be comma-separated numbers") from error


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Calibrate conservative thresholds using local non-clinical proxy labels."
    )
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--candidate-thresholds", default="0.30,0.40,0.50,0.60,0.70,0.80,0.90")
    parser.add_argument("--max-false-accept-rate", type=float, default=0.05)
    parser.add_argument("--calibration-bins", type=int, default=10)
    parser.add_argument("--calibration-status", default="proxy_not_therapist_calibrated")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.calibration_status != "proxy_not_therapist_calibrated":
        raise ValueError(
            "therapist_calibrated status requires therapist-labelled target-user evidence"
        )
    report = calibrate_proxy_thresholds(
        load_jsonl(args.input),
        candidate_thresholds=_parse_thresholds(args.candidate_thresholds),
        max_false_accept_rate=args.max_false_accept_rate,
        calibration_bins=args.calibration_bins,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

