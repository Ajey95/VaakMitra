"""Run a verified production bundle against its immutable canary suite."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.assessment import AssessmentContext  # noqa: E402
from app.vaakmitra_word.canary import CanaryError, CanarySuite, run_canary_suite  # noqa: E402
from app.vaakmitra_word.model import sha256_file  # noqa: E402
from app.vaakmitra_word.policy import TherapistConstraints  # noqa: E402
from app.vaakmitra_word.registry import build_technical_canary_runtime  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    suite = CanarySuite.model_validate_json(args.suite.read_text(encoding="utf-8"))
    registry, service = build_technical_canary_runtime(args.bundle)
    if service is None:
        reasons = ",".join(registry.scoring_readiness().reasons + ([registry.runtime_reason] if registry.runtime_reason else []))
        raise CanaryError(f"technical_canary_runtime_not_ready:{reasons}")

    def evaluate(record, audio: bytes) -> tuple[str, str, float]:
        result = service.assess(
            audio,
            AssessmentContext(
                session_id="CANARY-SESSION",
                attempt_id=f"CANARY-{record.canary_id}",
                word_id=record.word_id,
                target_word=record.target_word,
                attempt_count=0,
                therapist_constraints=TherapistConstraints(
                    allowed_actions=("repeat", "picture", "next_word", "break", "safe_end"),
                    next_exercise_id=record.word_id,
                ),
            ),
        )
        return result.decision.value, result.reason_code.value, float(result.latency_ms)

    report = run_canary_suite(suite, audio_root=args.audio_root, evaluate=evaluate)
    report = report.model_copy(update={"suite_hash": sha256_file(args.suite)})
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report.model_dump_json(indent=2) + "\n", encoding="utf-8")
    print(report.model_dump_json())
    return 0 if report.technical_accepted else 2


if __name__ == "__main__":
    raise SystemExit(main())
