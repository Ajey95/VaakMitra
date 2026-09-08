"""Run a complete contract flow with explicit non-production teammate mocks."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
from vaakmitra.contracts.acoustic import AcousticOutput
from vaakmitra.contracts.alignment import SyllableDefinition
from vaakmitra.ctc.vocabulary import PhonemeVocabulary
from vaakmitra.pipeline.assessment import AssessmentPipeline
from vaakmitra.scoring.confidence import ScoringConfig

from modeling.team_mocks.member1_alignment import build_mock_alignment
from modeling.team_mocks.member3_actions import choose_mock_action


class _FixtureRuntime:
    def __init__(self, vocabulary: PhonemeVocabulary) -> None:
        self._vocabulary = vocabulary

    def infer(
        self,
        audio: npt.NDArray[np.floating[Any]],
        sample_rate: int,
    ) -> AcousticOutput:
        del audio, sample_rate
        probabilities = np.array(
            [
                [0.05, 0.90, 0.05],
                [0.05, 0.85, 0.10],
                [0.05, 0.10, 0.85],
                [0.05, 0.05, 0.90],
            ],
            dtype=np.float32,
        )
        return AcousticOutput(
            log_probabilities=np.log(probabilities),
            frame_shift_ms=20.0,
            model_version="mock-flow-model-1.0.0",
            vocabulary_version=self._vocabulary.version,
            blank_index=self._vocabulary.blank_index,
            vocabulary_size=len(self._vocabulary.tokens),
        )


@dataclass(frozen=True, slots=True)
class MockedPipelineReport:
    schema_version: str
    evidence_scope: str
    release_status: str
    production_eligible: bool
    clinical_validity: bool
    attempt_id: str
    member1: dict[str, Any]
    member2: dict[str, Any]
    member3: dict[str, Any]
    limitations: tuple[str, ...]
    evidence_digest: str

    def as_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["limitations"] = list(self.limitations)
        return payload


def _digest(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def run_mocked_pipeline(report_path: str | Path) -> MockedPipelineReport:
    """Exercise Member 2 between deterministic Member 1 and Member 3 mocks."""

    destination = Path(report_path)
    if destination.exists():
        raise ValueError("mocked pipeline output exists")

    vocabulary = PhonemeVocabulary(
        version="mock-flow-vocab-1.0.0",
        tokens=("<blank>", "a", "m"),
    )
    pipeline = AssessmentPipeline(
        runtime=_FixtureRuntime(vocabulary),
        vocabulary=vocabulary,
        config=ScoringConfig(scoring_version="mock-flow-gop-1.0.0"),
    )
    acoustic_output = pipeline.infer(np.zeros(3200, dtype=np.float32), 16000)
    member1 = build_mock_alignment(
        ("a", "m"),
        acoustic_output.log_probabilities.shape[0],
        acoustic_output.frame_shift_ms,
        confidence=0.9,
    )
    assessment = pipeline.score_aligned_attempt(
        attempt_id="ATT-MOCK-TEAM-1",
        acoustic_output=acoustic_output,
        alignment=member1.alignment,
        syllables=(
            SyllableDefinition(
                text="\u0b85\u0bae\u0bcd",
                phoneme_indices=(0, 1),
            ),
        ),
    )
    member3 = choose_mock_action(assessment)
    report_without_digest: dict[str, Any] = {
        "schema_version": "1.0",
        "evidence_scope": "mocked_three_member_pipeline",
        "release_status": "technical_prototype",
        "production_eligible": False,
        "clinical_validity": False,
        "attempt_id": assessment.attempt_id,
        "member1": member1.as_dict(),
        "member2": assessment.model_dump(mode="json"),
        "member3": member3.as_dict(),
        "limitations": (
            "member1 alignment is deterministic mock evidence",
            "member3 action is deterministic mock evidence",
            "no therapist-labelled target-user validation",
            "no physical target-device benchmark",
        ),
    }
    report = MockedPipelineReport(
        **report_without_digest,
        evidence_digest=_digest(report_without_digest),
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    with destination.open("x", encoding="utf-8", newline="\n") as output_file:
        json.dump(report.as_dict(), output_file, ensure_ascii=False, indent=2)
        output_file.write("\n")
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the explicit non-production mocked three-member pipeline."
    )
    parser.add_argument("--report", required=True, type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_mocked_pipeline(args.report)
    print(json.dumps(report.as_dict(), ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
