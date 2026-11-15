"""GOV-004: finalize an exact candidate suite after signed qualified-human review."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.canary import CanaryError, CanarySuite, approve_canary_suite  # noqa: E402
from app.vaakmitra_word.model import sha256_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-suite", type=Path, required=True)
    parser.add_argument("--approval-export", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    key = os.environ.get("VAAKMITRA_REVIEW_SIGNING_KEY", "")
    if not key:
        raise CanaryError("canary_review_signing_key_missing")
    suite = CanarySuite.model_validate_json(args.candidate_suite.read_text(encoding="utf-8"))
    review = json.loads(args.approval_export.read_text(encoding="utf-8"))
    approved = approve_canary_suite(suite, review, sha256_file(args.candidate_suite), key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(approved.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(approved.model_dump_json())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
