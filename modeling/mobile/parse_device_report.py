"""CLI for reducing Android benchmark samples to aggregate promotion evidence."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from modeling.mobile.device_benchmark import (
    DeviceBenchmarkInput,
    validate_device_benchmark,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate physical/emulator Android benchmark evidence."
    )
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--expected-model-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    benchmark = DeviceBenchmarkInput.model_validate_json(
        args.input.read_text(encoding="utf-8")
    )
    report = validate_device_benchmark(
        benchmark, expected_model_sha256=args.expected_model_sha256
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report.model_dump(mode="json"), output, indent=2, ensure_ascii=False)
        output.write("\n")
    print(json.dumps({"status": "ok", "promotable": report.promotable}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
