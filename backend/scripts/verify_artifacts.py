"""Verify a local VaakMitra word-model bundle without loading child audio."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.artifacts import verify_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify immutable VaakMitra word-model artifacts")
    parser.add_argument("--config", required=True, type=Path, help="Path to bundle.json")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON")
    parser.add_argument(
        "--allow-engineering",
        action="store_true",
        help="Exit zero for an integrity-complete engineering bundle that remains non-production",
    )
    arguments = parser.parse_args()

    result = verify_bundle(arguments.config)
    payload = result.model_dump(mode="json")
    if arguments.json:
        print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    else:
        state = "READY" if result.ready else "ENGINEERING READY" if result.engineering_ready else "NOT READY"
        print(f"VaakMitra word bundle: {state}")
        for reason in result.reasons:
            print(f"- {reason}")
    return 0 if result.ready or (arguments.allow_engineering and result.engineering_ready) else 2


if __name__ == "__main__":
    raise SystemExit(main())
