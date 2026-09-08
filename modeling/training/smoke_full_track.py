"""Deterministic CPU-only shape/loss smoke for the full reference training core."""

from __future__ import annotations

import argparse
import hashlib
import json
import tempfile
import time
from collections.abc import Sequence
from pathlib import Path
from typing import Any, Literal

import torch
from pydantic import BaseModel, ConfigDict, Field
from torch import nn

from modeling.training.batch_order import LengthRecord
from modeling.training.phoneme_head import PhonemeCtcModel, phoneme_ctc_loss
from modeling.training.reference_stage import StageResult, run_reference_stage
from modeling.training.session_control import SessionBudget
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
    checkpoint_schema_version: Literal["2.0"] = "2.0"
    mid_epoch_resume_verified: Literal[True] = True
    final_state_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
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


# PyTorch is an optional, externally typed dependency in the backend mypy boundary.
class _FixtureEncoder(nn.Module):  # type: ignore[misc]
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


class _IdentityScaler:
    def __init__(self) -> None:
        self._steps = 0

    def scale(self, loss: torch.Tensor) -> torch.Tensor:
        return loss

    def unscale_(self, optimizer: torch.optim.Optimizer) -> None:
        del optimizer

    def step(self, optimizer: torch.optim.Optimizer) -> None:
        optimizer.step()
        self._steps += 1

    def update(self) -> None:
        return None

    def state_dict(self) -> dict[str, object]:
        return {"steps": self._steps}

    def load_state_dict(self, state: dict[str, object]) -> None:
        steps = state.get("steps")
        if not isinstance(steps, int) or isinstance(steps, bool):
            raise TypeError("scaler step count must be an integer")
        self._steps = steps


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


def _new_fixture_model(seed: int) -> tuple[PhonemeCtcModel, torch.optim.Optimizer, int, int]:
    torch.manual_seed(seed)
    model = PhonemeCtcModel(_FixtureEncoder(), hidden_size=8, vocabulary_size=4)
    freeze = select_trainable_parameters(model, TrainingStage.HEAD_ONLY)
    optimizer = torch.optim.SGD(
        (parameter for parameter in model.parameters() if parameter.requires_grad), lr=0.1
    )
    return (
        model,
        optimizer,
        freeze.total_parameter_count,
        freeze.trainable_parameter_count,
    )


def _run_fixture_stage(
    *,
    seed: int,
    steps: int,
    root: Path,
    stop_after_updates: int | None,
) -> tuple[PhonemeCtcModel, StageResult, list[float], int, int]:
    model, optimizer, parameter_count, trainable_parameter_count = _new_fixture_model(seed)
    audio, input_lengths, targets, target_lengths = _fixture_batch()
    losses: list[float] = []

    def train_batch(
        active_model: nn.Module,
        _indexes: tuple[int, ...],
    ) -> torch.Tensor:
        assert isinstance(active_model, PhonemeCtcModel)
        logits, frame_lengths = active_model(audio, input_lengths)
        loss = phoneme_ctc_loss(
            logits,
            frame_lengths,
            targets,
            target_lengths,
            blank_index=active_model.blank_index,
        )
        losses.append(float(loss.detach()))
        return loss

    def evaluate(active_model: nn.Module) -> dict[str, float]:
        assert isinstance(active_model, PhonemeCtcModel)
        with torch.inference_mode():
            logits, frame_lengths = active_model(audio, input_lengths)
            loss = phoneme_ctc_loss(
                logits,
                frame_lengths,
                targets,
                target_lengths,
                blank_index=active_model.blank_index,
            )
        return {"phoneme_error_rate": float(loss)}

    result = run_reference_stage(
        model=model,
        optimizer=optimizer,
        scaler=_IdentityScaler(),
        stage="head_only",
        epochs=1,
        length_records=tuple(LengthRecord(index, 24) for index in range(steps)),
        batch_size=1,
        bucket_size=max(1, steps),
        seed=seed,
        gradient_accumulation=1,
        binding_sha256=hashlib.sha256(f"fixture:{seed}:{steps}".encode()).hexdigest(),
        local_dir=root / "local",
        durable_dir=root / "durable",
        session_budget=SessionBudget(time.monotonic(), 3_600, 60, time.monotonic),
        train_batch=train_batch,
        evaluate_validation=evaluate,
        checkpoint_every_updates=max(1, steps),
        stop_after_global_update=stop_after_updates,
        status_path=root / "run-status.json",
    )
    return model, result, losses, parameter_count, trainable_parameter_count


def _state_sha256(model: nn.Module) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(model.state_dict().items()):
        tensor = value.detach().cpu().contiguous()
        digest.update(name.encode("utf-8"))
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(json.dumps(tuple(tensor.shape), separators=(",", ":")).encode())
        digest.update(tensor.view(torch.uint8).numpy().tobytes())
    return digest.hexdigest()


def run_cpu_smoke(*, seed: int, steps: int) -> FullTrackSmokeReport:
    """Verify fixture training and interruption-safe resume without teacher weights."""

    if steps <= 0:
        raise ValueError("steps must be positive")
    with tempfile.TemporaryDirectory(prefix="vaakmitra-smoke-") as temporary:
        root = Path(temporary)
        uninterrupted, complete, losses, parameter_count, trainable_count = (
            _run_fixture_stage(
                seed=seed,
                steps=steps,
                root=root / "uninterrupted",
                stop_after_updates=None,
            )
        )
        stop_after = max(1, steps // 2)
        _, stopped, _, _, _ = _run_fixture_stage(
            seed=seed,
            steps=steps,
            root=root / "resumed",
            stop_after_updates=stop_after,
        )
        resumed, resumed_result, _, _, _ = _run_fixture_stage(
            seed=seed,
            steps=steps,
            root=root / "resumed",
            stop_after_updates=None,
        )
        uninterrupted_sha256 = _state_sha256(uninterrupted)
        resumed_sha256 = _state_sha256(resumed)
        if complete.status != "complete" or stopped.status != "checkpointed_for_session_stop":
            raise RuntimeError("fixture interruption did not reach expected states")
        if resumed_result.status != "complete" or resumed_sha256 != uninterrupted_sha256:
            raise RuntimeError("resumed fixture state differs from uninterrupted state")

    return FullTrackSmokeReport(
        seed=seed,
        steps=steps,
        initial_loss=losses[0],
        final_loss=losses[-1],
        parameter_count=parameter_count,
        trainable_parameter_count=trainable_count,
        final_state_sha256=resumed_sha256,
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
