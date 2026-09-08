"""Resumable execution and promotion gates for reference-model stages."""

from __future__ import annotations

import json
import math
import os
import platform
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, Protocol, cast

import torch
from torch import nn

from modeling.training.batch_order import LengthRecord, build_batch_order
from modeling.training.resume_checkpoint import (
    CheckpointStage,
    ResumeCursor,
    VerifiedCheckpoint,
    find_latest_valid_checkpoint,
    load_checkpoint,
    restore_rng_state,
    save_checkpoint,
)
from modeling.training.session_control import SessionBudget, StopDecision

StageStatus = Literal["complete", "checkpointed_for_session_stop"]


class Scaler(Protocol):
    """Small common surface shared by CUDA GradScaler and CPU test scalers."""

    def scale(self, loss: torch.Tensor) -> torch.Tensor: ...

    def unscale_(self, optimizer: torch.optim.Optimizer) -> None: ...

    def step(self, optimizer: torch.optim.Optimizer) -> None: ...

    def update(self) -> None: ...

    def state_dict(self) -> dict[str, object]: ...

    def load_state_dict(self, state: dict[str, object]) -> None: ...


TrainBatch = Callable[[nn.Module, tuple[int, ...]], torch.Tensor | None]
EvaluateValidation = Callable[[nn.Module], Mapping[str, float]]


@dataclass(frozen=True, slots=True)
class GateDecision:
    allowed: bool
    reason: str | None


@dataclass(frozen=True, slots=True)
class StageResult:
    status: StageStatus
    stage: CheckpointStage
    global_updates: int
    best_validation_per: float
    history: tuple[dict[str, object], ...]
    latest_checkpoint: Path


def _validate_phone_error_rate(*values: float) -> None:
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("phone error rates must be finite and non-negative")


def _validate_time_budget(projected_seconds: float, available_seconds: float) -> None:
    if not math.isfinite(projected_seconds) or projected_seconds < 0.0:
        raise ValueError("projected seconds must be finite and non-negative")
    if not math.isfinite(available_seconds) or available_seconds < 0.0:
        raise ValueError("available seconds must be finite and non-negative")


def should_run_top_stage(
    *,
    head_checkpoint_reloadable: bool,
    head_validation_per: float,
    projected_seconds: float,
    available_seconds: float,
) -> GateDecision:
    """Allow top-block tuning only from a usable head checkpoint that fits."""

    _validate_phone_error_rate(head_validation_per)
    _validate_time_budget(projected_seconds, available_seconds)
    if not head_checkpoint_reloadable:
        return GateDecision(False, "head_checkpoint_not_reloadable")
    if projected_seconds > available_seconds:
        return GateDecision(False, "projected_stage_exceeds_available_time")
    return GateDecision(True, None)


def should_run_full_stage(
    *,
    head_validation_per: float,
    top_validation_per: float,
    minimum_improvement: float,
    projected_seconds: float,
    available_seconds: float,
) -> GateDecision:
    """Promote to full tuning only when validation gain pays for its runtime."""

    _validate_phone_error_rate(head_validation_per, top_validation_per)
    if not math.isfinite(minimum_improvement) or minimum_improvement < 0.0:
        raise ValueError("minimum improvement must be finite and non-negative")
    _validate_time_budget(projected_seconds, available_seconds)
    if head_validation_per - top_validation_per < minimum_improvement:
        return GateDecision(
            False,
            f"validation_per_improvement_below_{minimum_improvement:g}",
        )
    if projected_seconds > available_seconds:
        return GateDecision(False, "projected_stage_exceeds_available_time")
    return GateDecision(True, None)


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    with temporary.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, sort_keys=True, separators=(",", ":"))
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def _write_failure(
    durable_dir: Path,
    *,
    stage: CheckpointStage,
    code: str,
    binding_sha256: str,
    cursor: ResumeCursor,
    scalar_summary: Mapping[str, object],
) -> None:
    _write_json_atomic(
        durable_dir / "diagnostic-failure.json",
        {
            "binding_sha256": binding_sha256,
            "cursor": asdict(cursor),
            "environment": {
                "cuda": torch.version.cuda,
                "python": platform.python_version(),
                "torch": torch.__version__,
            },
            "failure_code": code,
            "scalar_summary": dict(scalar_summary),
            "stage": stage,
        },
    )


def _finite_validation_per(metrics: Mapping[str, float]) -> float:
    if "phoneme_error_rate" not in metrics:
        raise ValueError("validation metrics must contain phoneme_error_rate")
    value = float(metrics["phoneme_error_rate"])
    _validate_phone_error_rate(value)
    return value


def _save(
    *,
    local_dir: Path,
    durable_dir: Path,
    binding_sha256: str,
    cursor: ResumeCursor,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: Scaler,
    best_validation_per: float,
    history: Sequence[Mapping[str, object]],
) -> VerifiedCheckpoint:
    return save_checkpoint(
        local_dir=local_dir,
        durable_dir=durable_dir,
        binding_sha256=binding_sha256,
        cursor=cursor,
        model=model,
        optimizer=optimizer,
        scaler_state=scaler.state_dict(),
        best_validation_per=best_validation_per,
        history=history,
    )


def _write_status(
    status_path: Path,
    *,
    status: StageStatus,
    binding_sha256: str,
    cursor: ResumeCursor,
    checkpoint: VerifiedCheckpoint,
    decision: StopDecision,
    reason: str | None,
) -> None:
    _write_json_atomic(
        status_path,
        {
            "binding_sha256": binding_sha256,
            "checkpoint_sha256": checkpoint.sha256,
            "cursor": asdict(cursor),
            "elapsed_seconds": decision.elapsed_seconds,
            "production_ready": False,
            "reason": reason,
            "stage": cursor.stage,
            "status": status,
        },
    )


def run_reference_stage(
    *,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler: Scaler,
    stage: CheckpointStage,
    epochs: int,
    length_records: Sequence[LengthRecord],
    batch_size: int,
    bucket_size: int,
    seed: int,
    gradient_accumulation: int,
    binding_sha256: str,
    local_dir: Path,
    durable_dir: Path,
    session_budget: SessionBudget,
    train_batch: TrainBatch,
    evaluate_validation: EvaluateValidation,
    checkpoint_every_updates: int,
    status_path: Path,
    stop_after_global_update: int | None = None,
    gradient_clip_norm: float = 1.0,
) -> StageResult:
    """Run one reference stage with exact optimizer-boundary checkpoint resume."""

    if epochs <= 0:
        raise ValueError("epochs must be positive")
    if batch_size <= 0 or bucket_size < batch_size:
        raise ValueError("invalid batch or bucket size")
    if gradient_accumulation <= 0 or checkpoint_every_updates <= 0:
        raise ValueError("update intervals must be positive")
    if gradient_clip_norm <= 0.0 or not math.isfinite(gradient_clip_norm):
        raise ValueError("gradient clip norm must be finite and positive")
    if stop_after_global_update is not None and stop_after_global_update < 0:
        raise ValueError("stop update must be non-negative")

    cursor = ResumeCursor(stage, 0, 0, 0, 0, "0" * 64)
    history: list[dict[str, object]] = []
    best_validation_per = math.inf
    latest: VerifiedCheckpoint | None = None

    checkpoint_path = find_latest_valid_checkpoint(
        durable_dir,
        expected_binding_sha256=binding_sha256,
    )
    if checkpoint_path is not None:
        payload = load_checkpoint(
            checkpoint_path,
            expected_binding_sha256=binding_sha256,
        )
        loaded_cursor = cast(ResumeCursor, payload["cursor"])
        if loaded_cursor.stage != stage:
            raise ValueError("checkpoint stage mismatch")
        model.load_state_dict(payload["model_state"])
        optimizer.load_state_dict(payload["optimizer_state"])
        scaler.load_state_dict(cast(dict[str, object], payload["scaler_state"]))
        restore_rng_state(cast(Mapping[str, object], payload["rng_state"]))
        cursor = loaded_cursor
        history = [dict(row) for row in payload["history"]]
        best_validation_per = float(payload["best_validation_per"])

    if cursor.epoch > epochs:
        raise ValueError("checkpoint epoch exceeds configured epochs")

    for epoch in range(cursor.epoch, epochs):
        order = build_batch_order(
            length_records,
            seed=seed,
            epoch=epoch,
            batch_size=batch_size,
            bucket_size=bucket_size,
        )
        next_batch_index = cursor.next_batch_index if epoch == cursor.epoch else 0
        if next_batch_index and cursor.batch_order_sha256 != order.order_sha256:
            raise ValueError("checkpoint batch order mismatch")

        model.train()
        if stage == "head_only":
            for attribute in ("acoustic", "encoder"):
                frozen_encoder = getattr(model, attribute, None)
                if isinstance(frozen_encoder, nn.Module):
                    frozen_encoder.eval()
        optimizer.zero_grad(set_to_none=True)
        accumulated = 0
        for batch_index in range(next_batch_index, len(order.batches)):
            loss = train_batch(model, order.batches[batch_index])
            if loss is None:
                continue
            if loss.numel() != 1 or not bool(torch.isfinite(loss.detach()).item()):
                _write_failure(
                    durable_dir,
                    stage=stage,
                    code="non_finite_training_loss",
                    binding_sha256=binding_sha256,
                    cursor=cursor,
                    scalar_summary={"loss_finite": False},
                )
                raise FloatingPointError("non-finite training loss")

            scaler.scale(loss / gradient_accumulation).backward()
            accumulated += 1
            is_last_batch = batch_index + 1 == len(order.batches)
            if accumulated < gradient_accumulation and not is_last_batch:
                continue

            scaler.unscale_(optimizer)
            gradient_norm = torch.nn.utils.clip_grad_norm_(
                tuple(parameter for parameter in model.parameters() if parameter.requires_grad),
                gradient_clip_norm,
            )
            if not bool(torch.isfinite(gradient_norm).item()):
                _write_failure(
                    durable_dir,
                    stage=stage,
                    code="non_finite_gradient_norm",
                    binding_sha256=binding_sha256,
                    cursor=cursor,
                    scalar_summary={"gradient_norm_finite": False},
                )
                raise FloatingPointError("non-finite gradient norm")
            scaler.step(optimizer)
            scaler.update()
            optimizer.zero_grad(set_to_none=True)
            accumulated = 0

            cursor = ResumeCursor(
                stage,
                epoch,
                batch_index + 1,
                cursor.global_update + 1,
                epoch,
                order.order_sha256,
            )
            if cursor.global_update % checkpoint_every_updates == 0:
                latest = _save(
                    local_dir=local_dir,
                    durable_dir=durable_dir,
                    binding_sha256=binding_sha256,
                    cursor=cursor,
                    model=model,
                    optimizer=optimizer,
                    scaler=scaler,
                    best_validation_per=best_validation_per,
                    history=history,
                )

            decision = session_budget.decision()
            requested_stop = (
                stop_after_global_update is not None
                and cursor.global_update >= stop_after_global_update
            )
            if decision.should_stop or requested_stop:
                if latest is None or cursor.global_update % checkpoint_every_updates:
                    latest = _save(
                        local_dir=local_dir,
                        durable_dir=durable_dir,
                        binding_sha256=binding_sha256,
                        cursor=cursor,
                        model=model,
                        optimizer=optimizer,
                        scaler=scaler,
                        best_validation_per=best_validation_per,
                        history=history,
                    )
                _write_status(
                    status_path,
                    status="checkpointed_for_session_stop",
                    binding_sha256=binding_sha256,
                    cursor=cursor,
                    checkpoint=latest,
                    decision=decision,
                    reason=(
                        decision.reason
                        if decision.should_stop
                        else "requested_global_update_stop"
                    ),
                )
                return StageResult(
                    "checkpointed_for_session_stop",
                    stage,
                    cursor.global_update,
                    best_validation_per,
                    tuple(history),
                    latest.durable_path,
                )

        validation_per = _finite_validation_per(evaluate_validation(model))
        best_validation_per = min(best_validation_per, validation_per)
        history.append(
            {
                "epoch": epoch,
                "global_update": cursor.global_update,
                "phoneme_error_rate": validation_per,
                "stage": stage,
            }
        )
        cursor = ResumeCursor(
            stage,
            epoch + 1,
            0,
            cursor.global_update,
            epoch + 1,
            order.order_sha256,
        )
        latest = _save(
            local_dir=local_dir,
            durable_dir=durable_dir,
            binding_sha256=binding_sha256,
            cursor=cursor,
            model=model,
            optimizer=optimizer,
            scaler=scaler,
            best_validation_per=best_validation_per,
            history=history,
        )

    if latest is None:
        if checkpoint_path is None:
            raise RuntimeError("stage completed without a checkpoint")
        sidecar = json.loads(
            Path(str(checkpoint_path) + ".sha256.json").read_text(encoding="utf-8")
        )
        latest = VerifiedCheckpoint(
            local_path=checkpoint_path,
            durable_path=checkpoint_path,
            sha256=str(sidecar["sha256"]),
            size_bytes=int(sidecar["size_bytes"]),
        )

    decision = session_budget.decision()
    _write_status(
        status_path,
        status="complete",
        binding_sha256=binding_sha256,
        cursor=cursor,
        checkpoint=latest,
        decision=decision,
        reason=None,
    )
    return StageResult(
        "complete",
        stage,
        cursor.global_update,
        best_validation_per,
        tuple(history),
        latest.durable_path,
    )
