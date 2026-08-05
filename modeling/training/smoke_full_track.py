"""Deterministic CPU-only shape/loss smoke for the full reference training core."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import torch
from pydantic import BaseModel, ConfigDict, Field
from torch import nn

from modeling.training.phoneme_head import PhonemeCtcModel, phoneme_ctc_loss
from modeling.training.stages import TrainingStage, select_trainable_parameters


class FullTrackSmokeReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    seed: int
    steps: int = Field(gt=0)
    initial_loss: float = Field(ge=0.0)
    final_loss: float = Field(ge=0.0)
    parameter_count: int = Field(gt=0)
    trainable_parameter_count: int = Field(gt=0)
    evidence_scope: Literal["fixture_encoder_shapes_only"] = "fixture_encoder_shapes_only"
    upstream_checkpoint_loaded: Literal[False] = False
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


class _FixtureEncoder(nn.Module):
    def __init__(self) -> None:
        super().__init__()
        self.layers = nn.ModuleList([nn.Linear(4, 8), nn.Linear(8, 8)])

    def forward(
        self, audio: torch.Tensor, input_lengths: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor]:
        usable_samples = (audio.shape[1] // 4) * 4
        frames = audio[:, :usable_samples].reshape(audio.shape[0], -1, 4)
        hidden = torch.tanh(self.layers[0](frames))
        hidden = torch.tanh(self.layers[1](hidden))
        lengths = torch.div(input_lengths, 4, rounding_mode="floor")
        return hidden, lengths


def _fixture_batch() -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    audio = torch.tensor(
        [
            [0.0, 0.1, 0.2, 0.3] * 6,
            [0.3, 0.2, 0.1, 0.0] * 6,
        ],
        dtype=torch.float32,
    )
    return (
        audio,
        torch.tensor([24, 24], dtype=torch.long),
        torch.tensor([[1, 2, -1], [2, 3, -1]], dtype=torch.long),
        torch.tensor([2, 2], dtype=torch.long),
    )


def run_cpu_smoke(*, seed: int, steps: int) -> FullTrackSmokeReport:
    """Train only a new head over a tiny fixture encoder; never load IndicConformer."""

    if steps <= 0:
        raise ValueError("steps must be positive")
    torch.manual_seed(seed)
    model = PhonemeCtcModel(_FixtureEncoder(), hidden_size=8, vocabulary_size=4)
    freeze = select_trainable_parameters(model, TrainingStage.HEAD_ONLY)
    optimizer = torch.optim.SGD(
        (parameter for parameter in model.parameters() if parameter.requires_grad), lr=0.1
    )
    audio, input_lengths, targets, target_lengths = _fixture_batch()

    losses: list[float] = []
    for _ in range(steps):
        optimizer.zero_grad(set_to_none=True)
        logits, frame_lengths = model(audio, input_lengths)
        loss = phoneme_ctc_loss(
            logits,
            frame_lengths,
            targets,
            target_lengths,
            blank_index=model.blank_index,
        )
        losses.append(float(loss.detach()))
        torch.autograd.backward(loss)
        nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
        optimizer.step()

    return FullTrackSmokeReport(
        seed=seed,
        steps=steps,
        initial_loss=losses[0],
        final_loss=losses[-1],
        parameter_count=freeze.total_parameter_count,
        trainable_parameter_count=freeze.trainable_parameter_count,
    )


def write_smoke_report(path: Path, report: FullTrackSmokeReport) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(report.as_dict(), output, indent=2, ensure_ascii=False)
        output.write("\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run CPU-only phoneme-head smoke training with a fixture encoder."
    )
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--steps", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    report = run_cpu_smoke(seed=args.seed, steps=args.steps)
    write_smoke_report(args.output, report)
    print(json.dumps(report.as_dict(), ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
