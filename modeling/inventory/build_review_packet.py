"""Create and finalize Tamil inventory review packets without silent approval."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from modeling.inventory.clinician_review import (
    ClinicianReviewPacket,
    create_review_template,
    finalize_expert_inventory,
)
from modeling.inventory.consensus import CandidateInventory


def _load_candidate(path: Path) -> CandidateInventory:
    payload: Any = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError("candidate inventory must be a JSON object")
    declared_digest = payload.pop("inventory_digest", None)
    candidate = CandidateInventory.model_validate(payload)
    if declared_digest is not None and declared_digest != candidate.digest():
        raise ValueError("candidate inventory digest is invalid")
    return candidate


def _write_exclusive(path: Path, payload: object) -> None:
    if path.exists():
        raise ValueError("output exists")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or finalize a digest-bound Tamil inventory review."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    template = commands.add_parser("template")
    template.add_argument("--candidate", required=True, type=Path)
    template.add_argument("--output", required=True, type=Path)
    finalize = commands.add_parser("finalize")
    finalize.add_argument("--candidate", required=True, type=Path)
    finalize.add_argument("--review", required=True, type=Path)
    finalize.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    candidate = _load_candidate(args.candidate)
    if args.command == "template":
        packet = create_review_template(candidate)
        _write_exclusive(args.output, packet.model_dump(mode="json"))
        print(json.dumps({"status": packet.review_status, "output": str(args.output)}))
        return 0
    packet = ClinicianReviewPacket.model_validate_json(
        args.review.read_text(encoding="utf-8")
    )
    approved = finalize_expert_inventory(candidate, packet)
    _write_exclusive(args.output, approved.model_dump(mode="json"))
    print(json.dumps({"status": approved.review_status, "output": str(args.output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
