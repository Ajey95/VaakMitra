"""Atomic, binding-aware checkpoints for exact optimizer-boundary resume."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import random
import shutil
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal, cast

import torch
from torch import nn

CheckpointStage = Literal["head_only", "top_encoder_blocks", "full_encoder", "student"]


@dataclass(frozen=True, slots=True)
class ResumeCursor:
    stage: CheckpointStage
    epoch: int
    next_batch_index: int
    global_update: int
    sampler_epoch: int
    batch_order_sha256: str

    def __post_init__(self) -> None:
        if self.stage not in {"head_only", "top_encoder_blocks", "full_encoder", "student"}:
            raise ValueError("unsupported checkpoint stage")
        if min(self.epoch, self.next_batch_index, self.global_update, self.sampler_epoch) < 0:
            raise ValueError("resume cursor counters must be non-negative")
        if len(self.batch_order_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.batch_order_sha256
        ):
            raise ValueError("batch order SHA-256 must be lowercase hexadecimal")


@dataclass(frozen=True, slots=True)
class VerifiedCheckpoint:
    local_path: Path
    durable_path: Path
    sha256: str
    size_bytes: int


class DurableCheckpointWriteError(OSError):
    """Raised after a local checkpoint succeeds but durable persistence fails."""

    failure_code = "durable_checkpoint_write_failed"

    def __init__(self, local_checkpoint: Path, cause: OSError) -> None:
        super().__init__(f"durable checkpoint write failed: {cause}")
        self.local_checkpoint = local_checkpoint


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sidecar(path: Path) -> Path:
    return path.with_name(path.name + ".sha256.json")


def _write_json_atomic(path: Path, payload: Mapping[str, object]) -> None:
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, sort_keys=True, separators=(",", ":"))
        output.write("\n")
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def capture_rng_state() -> dict[str, object]:
    """Capture all RNG state needed to reproduce the next training operation."""

    numpy = importlib.import_module("numpy")
    return {
        "python": random.getstate(),
        "numpy": numpy.random.get_state(),
        "torch_cpu": torch.get_rng_state(),
        "torch_cuda": torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [],
    }


def restore_rng_state(state: Mapping[str, object]) -> None:
    """Restore a complete RNG snapshot, failing if CUDA state cannot be restored."""

    required = {"python", "numpy", "torch_cpu", "torch_cuda"}
    if set(state) != required:
        raise ValueError("checkpoint RNG state fields differ")
    numpy = importlib.import_module("numpy")
    random.setstate(cast(tuple[Any, ...], state["python"]))
    numpy.random.set_state(state["numpy"])
    torch.set_rng_state(cast(torch.Tensor, state["torch_cpu"]))
    cuda_state = cast(list[torch.Tensor], state["torch_cuda"])
    if cuda_state:
        if not torch.cuda.is_available():
            raise RuntimeError("checkpoint requires CUDA RNG restoration")
        torch.cuda.set_rng_state_all(cuda_state)


def _cpu_model_state(model: nn.Module) -> dict[str, torch.Tensor]:
    return {
        name: value.detach().cpu().clone()
        for name, value in model.state_dict().items()
    }


def _write_torch_atomic(path: Path, payload: Mapping[str, object]) -> None:
    temporary = path.with_name(path.name + f".{os.getpid()}.tmp")
    path.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("xb") as output:
        torch.save(dict(payload), output)
        output.flush()
        os.fsync(output.fileno())
    os.replace(temporary, path)


def _copy_verified(source: Path, destination: Path) -> tuple[str, int]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + f".{os.getpid()}.tmp")
    shutil.copy2(source, temporary)
    source_size = source.stat().st_size
    source_sha256 = _sha256_file(source)
    if temporary.stat().st_size != source_size or _sha256_file(temporary) != source_sha256:
        temporary.unlink(missing_ok=True)
        raise OSError("durable checkpoint verification failed")
    os.replace(temporary, destination)
    _write_json_atomic(
        _sidecar(destination),
        {"sha256": source_sha256, "size_bytes": source_size},
    )
    return source_sha256, source_size


def save_checkpoint(
    *,
    local_dir: Path,
    durable_dir: Path,
    binding_sha256: str,
    cursor: ResumeCursor,
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    scaler_state: Mapping[str, object],
    best_validation_per: float,
    history: Sequence[Mapping[str, object]],
) -> VerifiedCheckpoint:
    """Save locally, then copy and verify durable numbered and last checkpoints."""

    if len(binding_sha256) != 64:
        raise ValueError("binding SHA-256 must contain 64 characters")
    payload: dict[str, object] = {
        "checkpoint_schema_version": "2.0",
        "binding_sha256": binding_sha256,
        "cursor": asdict(cursor),
        "model_state": _cpu_model_state(model),
        "optimizer_state": optimizer.state_dict(),
        "scaler_state": dict(scaler_state),
        "rng_state": capture_rng_state(),
        "best_validation_per": float(best_validation_per),
        "history": tuple(dict(row) for row in history),
    }
    filename = f"{cursor.stage}-update-{cursor.global_update:09d}.pt"
    local_path = local_dir / filename
    _write_torch_atomic(local_path, payload)

    durable_path = durable_dir / filename
    try:
        digest, size_bytes = _copy_verified(local_path, durable_path)
        last_path = durable_dir / "last.pt"
        _copy_verified(durable_path, last_path)
    except OSError as error:
        raise DurableCheckpointWriteError(local_path, error) from error
    return VerifiedCheckpoint(
        local_path=local_path,
        durable_path=durable_path,
        sha256=digest,
        size_bytes=size_bytes,
    )


def load_checkpoint(
    path: str | Path,
    *,
    expected_binding_sha256: str,
) -> dict[str, Any]:
    """Verify digest and binding before returning a checkpoint payload."""

    checkpoint = Path(path)
    sidecar = _sidecar(checkpoint)
    if not checkpoint.is_file() or not sidecar.is_file():
        raise ValueError("checkpoint or SHA-256 sidecar is missing")
    evidence = json.loads(sidecar.read_text(encoding="utf-8"))
    actual_size = checkpoint.stat().st_size
    actual_sha256 = _sha256_file(checkpoint)
    if evidence.get("size_bytes") != actual_size or evidence.get("sha256") != actual_sha256:
        raise ValueError("checkpoint SHA-256 mismatch")

    payload = torch.load(checkpoint, map_location="cpu", weights_only=False)
    if not isinstance(payload, dict):
        raise TypeError("checkpoint payload must be a dictionary")
    required = {
        "checkpoint_schema_version",
        "binding_sha256",
        "cursor",
        "model_state",
        "optimizer_state",
        "scaler_state",
        "rng_state",
        "best_validation_per",
        "history",
    }
    if set(payload) != required or payload["checkpoint_schema_version"] != "2.0":
        raise ValueError("checkpoint schema fields differ")
    if payload["binding_sha256"] != expected_binding_sha256:
        raise ValueError("checkpoint binding mismatch")
    raw_cursor = payload["cursor"]
    if not isinstance(raw_cursor, dict):
        raise TypeError("checkpoint cursor must be a dictionary")
    payload["cursor"] = ResumeCursor(**raw_cursor)
    rng_state = payload["rng_state"]
    if not isinstance(rng_state, dict) or set(rng_state) != {
        "python",
        "numpy",
        "torch_cpu",
        "torch_cuda",
    }:
        raise ValueError("checkpoint RNG state fields differ")
    return cast(dict[str, Any], payload)


def find_latest_valid_checkpoint(
    durable_dir: str | Path,
    *,
    expected_binding_sha256: str,
) -> Path | None:
    """Prefer `last.pt`, then fall back to the newest valid numbered checkpoint."""

    root = Path(durable_dir)
    numbered = sorted(root.glob("*-update-*.pt"), reverse=True)
    candidates = [root / "last.pt", *numbered]
    for candidate in candidates:
        try:
            load_checkpoint(candidate, expected_binding_sha256=expected_binding_sha256)
        except (OSError, RuntimeError, TypeError, ValueError, json.JSONDecodeError):
            continue
        return candidate
    return None
