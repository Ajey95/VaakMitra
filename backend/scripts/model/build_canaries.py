"""Build an immutable, leakage-checked Tamil release canary suite."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.canary import CanaryInput, build_canary_suite  # noqa: E402
from app.vaakmitra_word.model import sha256_file  # noqa: E402


def _forbidden_ids(paths: list[Path]) -> set[str]:
    identifiers: set[str] = set()
    for path in paths:
        with path.open("r", encoding="utf-8") as source:
            for line in source:
                if not line.strip():
                    continue
                payload = json.loads(line)
                identifier = payload.get("sample_id") or payload.get("source_sample_id")
                if identifier:
                    identifiers.add(str(identifier))
    return identifiers


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--dataset-manifest", type=Path, required=True)
    parser.add_argument("--forbidden-manifest", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    vocabulary = json.loads(args.vocabulary.read_text(encoding="utf-8"))
    entries = vocabulary.get("entries", [])
    active_words = tuple(
        str(item["word_id"])
        for item in entries
        if item.get("state") == "active" and item.get("scoreable") is True
    )
    candidates = []
    with args.candidate_manifest.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                payload = json.loads(line)
                payload["allowed_reason_codes"] = tuple(payload["allowed_reason_codes"])
                candidates.append(CanaryInput(**payload))
    suite = build_canary_suite(
        candidates,
        active_words=active_words,
        vocabulary_hash=sha256_file(args.vocabulary),
        dataset_manifest_hash=sha256_file(args.dataset_manifest),
        forbidden_sample_ids=_forbidden_ids(args.forbidden_manifest),
        audio_root=args.audio_root,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(suite.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(suite.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
