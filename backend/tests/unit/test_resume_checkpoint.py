from __future__ import annotations

import random
from pathlib import Path
from typing import Any

import numpy as np
import pytest
import torch
from modeling.training.resume_checkpoint import (
    DurableCheckpointWriteError,
    ResumeCursor,
    find_latest_valid_checkpoint,
    load_checkpoint,
    restore_rng_state,
    save_checkpoint,
)
from torch import nn


def _model_and_optimizer() -> tuple[nn.Module, torch.optim.Optimizer]:
    model = nn.Linear(2, 1)
    optimizer = torch.optim.AdamW(model.parameters(), lr=0.01)
    return model, optimizer


def _cursor(*, update: int = 500) -> ResumeCursor:
    return ResumeCursor(
        stage="head_only",
        epoch=1,
        next_batch_index=7,
        global_update=update,
        sampler_epoch=1,
        batch_order_sha256="b" * 64,
    )


def _save(tmp_path: Path, *, update: int = 500, binding: str = "a" * 64) -> Path:
    model, optimizer = _model_and_optimizer()
    saved = save_checkpoint(
        local_dir=tmp_path / "local",
        durable_dir=tmp_path / "durable",
        binding_sha256=binding,
        cursor=_cursor(update=update),
        model=model,
        optimizer=optimizer,
        scaler_state={"scale": 1024.0},
        best_validation_per=0.42,
        history=({"epoch": 0, "validation_per": 0.42},),
    )
    return saved.durable_path


def test_mid_epoch_resume_restores_rng_and_next_unapplied_batch(tmp_path: Path) -> None:
    random.seed(9)
    np.random.seed(9)
    torch.manual_seed(9)
    model, optimizer = _model_and_optimizer()
    saved = save_checkpoint(
        local_dir=tmp_path / "local",
        durable_dir=tmp_path / "durable",
        binding_sha256="a" * 64,
        cursor=_cursor(),
        model=model,
        optimizer=optimizer,
        scaler_state={},
        best_validation_per=0.42,
        history=(),
    )
    expected_python = random.random()
    expected_numpy = float(np.random.random())
    expected_torch = torch.rand(3)
    random.seed(100)
    np.random.seed(100)
    torch.manual_seed(100)

    payload = load_checkpoint(
        saved.durable_path,
        expected_binding_sha256="a" * 64,
    )
    restore_rng_state(payload["rng_state"])

    assert payload["cursor"] == _cursor()
    assert random.random() == expected_python
    assert float(np.random.random()) == expected_numpy
    assert torch.equal(torch.rand(3), expected_torch)


def test_load_rejects_binding_mismatch(tmp_path: Path) -> None:
    checkpoint = _save(tmp_path)

    with pytest.raises(ValueError, match="checkpoint binding mismatch"):
        load_checkpoint(checkpoint, expected_binding_sha256="c" * 64)


def test_corrupt_last_checkpoint_falls_back_to_newest_numbered_file(
    tmp_path: Path,
) -> None:
    _save(tmp_path, update=500)
    newest = _save(tmp_path, update=1_000)
    last = tmp_path / "durable" / "last.pt"
    last.write_bytes(b"truncated")

    selected = find_latest_valid_checkpoint(
        tmp_path / "durable",
        expected_binding_sha256="a" * 64,
    )

    assert selected == newest


def test_hash_mismatch_is_rejected_before_deserialization(tmp_path: Path) -> None:
    checkpoint = _save(tmp_path)
    checkpoint.write_bytes(checkpoint.read_bytes() + b"tamper")

    with pytest.raises(ValueError, match="checkpoint SHA-256 mismatch"):
        load_checkpoint(checkpoint, expected_binding_sha256="a" * 64)


def test_durable_write_failure_retains_verified_local_checkpoint(tmp_path: Path) -> None:
    model, optimizer = _model_and_optimizer()
    invalid_durable = tmp_path / "durable-file"
    invalid_durable.write_text("not a directory", encoding="utf-8")

    with pytest.raises(DurableCheckpointWriteError) as caught:
        save_checkpoint(
            local_dir=tmp_path / "local",
            durable_dir=invalid_durable,
            binding_sha256="a" * 64,
            cursor=_cursor(),
            model=model,
            optimizer=optimizer,
            scaler_state={},
            best_validation_per=0.42,
            history=(),
        )

    assert caught.value.local_checkpoint.is_file()
    assert caught.value.failure_code == "durable_checkpoint_write_failed"


@pytest.mark.parametrize(
    "overrides",
    [
        {"epoch": -1},
        {"next_batch_index": -1},
        {"global_update": -1},
        {"sampler_epoch": -1},
        {"batch_order_sha256": "short"},
    ],
)
def test_resume_cursor_rejects_invalid_state(overrides: dict[str, Any]) -> None:
    values: dict[str, Any] = {
        "stage": "head_only",
        "epoch": 0,
        "next_batch_index": 0,
        "global_update": 0,
        "sampler_epoch": 0,
        "batch_order_sha256": "b" * 64,
    }
    values.update(overrides)

    with pytest.raises(ValueError):
        ResumeCursor(**values)
