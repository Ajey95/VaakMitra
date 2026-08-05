"""CLI for creating a hash-linked Member 2 release evidence report."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from modeling.release.evidence import EvidenceInput, assemble_release_evidence


class EvidenceAssemblyRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    requested_status: str
    inputs: tuple[EvidenceInput, ...]


def _load_request(path: Path) -> EvidenceAssemblyRequest:
    request = EvidenceAssemblyRequest.model_validate_json(path.read_text(encoding="utf-8"))
    resolved = tuple(
        item
        if item.path.is_absolute()
        else item.model_copy(update={"path": (path.parent / item.path).resolve()})
        for item in request.inputs
    )
    return request.model_copy(update={"inputs": resolved})


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assemble hash-linked Member 2 technical-prototype release evidence."
    )
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    request = _load_request(args.request)
    report = assemble_release_evidence(
        request.inputs,
        requested_status=request.requested_status,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report.as_dict(), indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

