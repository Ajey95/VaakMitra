"""Deterministic CPU-only smoke training for both compact student candidates."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import torch
from pydantic import BaseModel, ConfigDict, Field

from modeling.distillation.losses import DistillationCriterion, DistillationWeights
from modeling.distillation.students import CompactConformerCtc, CompactConvBiGruCtc
from modeling.distillation.training import distillation_training_step
from modeling.training.ctc_batch import PhonemeBatch


class StudentCandidateSmoke(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    architecture: Literal["conformer", "conv_bigru"]
    parameter_count: int = Field(gt=0)
    fp32_size_bytes: int = Field(gt=0)
    initial_loss: float = Field(ge=0.0)
    final_loss: float = Field(ge=0.0)


class StudentTrackSmokeReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    seed: int
    steps: int = Field(gt=0)
    candidates: tuple[StudentCandidateSmoke, StudentCandidateSmoke]
    evidence_scope: Literal["distillation_smoke_only"] = "distillation_smoke_only"
    teacher_checkpoint_loaded: Literal[False] = False
    cuda_training_completed: Literal[False] = False
    production_ready: Literal[False] = False

    def digest(self) -> str:
        canonical = json.dumps(
            self.model_dump(mode="json"), separators=(",", ":"), sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()

    def as_dict(self) -> dict[str, Any]:
        result = self.model_dump(mode="json")
        result["report_sha256"] = self.digest()
        return result


def _batch() -> PhonemeBatch:
    audio = torch.tensor(
        [
            [0.0, 0.1, 0.2, 0.3] * 400,
            [0.3, 0.2, 0.1, 0.0] * 400,
        ],
        dtype=torch.float32,
    )
    return PhonemeBatch(
        audio=audio,
        input_lengths=torch.tensor([1_600, 1_600]),
        padded_targets=torch.tensor([[1, 2, -1], [2, 3, -1]]),
        target_lengths=torch.tensor([2, 2]),
    )


def _train_candidate(
    *, architecture: Literal["conformer", "conv_bigru"], seed: int, steps: int
) -> StudentCandidateSmoke:
    torch.manual_seed(seed)
    model: CompactConformerCtc | CompactConvBiGruCtc
    if architecture == "conformer":
        model = CompactConformerCtc(
            vocabulary_size=4,
            frontend_channels=4,
            hidden_size=8,
            encoder_layers=1,
            attention_heads=2,
        )
    else:
        model = CompactConvBiGruCtc(
            vocabulary_size=4,
            frontend_channels=4,
            hidden_size=4,
            encoder_layers=1,
        )
    batch = _batch()
    with torch.no_grad():
        frame_count = model(batch.audio, batch.input_lengths).hidden.shape[1]
    teacher_hidden = torch.linspace(
        -1.0, 1.0, steps=batch.audio.shape[0] * frame_count * 6
    ).reshape(batch.audio.shape[0], frame_count, 6)
    criterion = DistillationCriterion(
        student_dimension=8,
        teacher_dimension=6,
        weights=DistillationWeights(
            supervised_ctc=1.0,
            representation=0.5,
            relational=0.25,
            sequence_consistency=0.1,
        ),
        blank_index=0,
    )
    optimizer = torch.optim.Adam((*model.parameters(), *criterion.parameters()), lr=0.001)
    losses: list[float] = []
    for _ in range(steps):
        result = distillation_training_step(
            model=model,
            criterion=criterion,
            optimizer=optimizer,
            batch=batch,
            teacher_hidden=teacher_hidden,
            vocabulary_size=4,
            gradient_clip_norm=1.0,
        )
        losses.append(float(result.total.detach()))
    parameters = model.parameter_report()
    return StudentCandidateSmoke(
        architecture=architecture,
        parameter_count=parameters.parameter_count,
        fp32_size_bytes=parameters.fp32_size_bytes,
        initial_loss=losses[0],
        final_loss=losses[-1],
    )


def run_student_smoke(*, seed: int, steps: int) -> StudentTrackSmokeReport:
    if steps <= 0:
        raise ValueError("steps must be positive")
    return StudentTrackSmokeReport(
        seed=seed,
        steps=steps,
        candidates=(
            _train_candidate(architecture="conformer", seed=seed, steps=steps),
            _train_candidate(architecture="conv_bigru", seed=seed, steps=steps),
        ),
    )


def write_student_smoke_report(path: Path, report: StudentTrackSmokeReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report.as_dict(), output, ensure_ascii=False, indent=2)
        output.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CPU-only distillation smoke training for both students."
    )
    parser.add_argument("--seed", type=int, default=23)
    parser.add_argument("--steps", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_student_smoke(seed=args.seed, steps=args.steps)
    write_student_smoke_report(args.output, report)
    print(json.dumps(report.as_dict(), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
