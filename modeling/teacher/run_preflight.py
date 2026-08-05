"""Credential-safe local CLI for teacher environment readiness."""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
from collections.abc import Sequence
from pathlib import Path

from modeling.distillation.teacher_features import load_teacher_config
from modeling.teacher.preflight import (
    PreflightMode,
    TeacherEnvironmentProbe,
    evaluate_teacher_preflight,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check local IndicConformer readiness without reading or printing credentials."
    )
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--mode", choices=("cpu_smoke", "feature_extract", "full_train"), required=True
    )
    parser.add_argument(
        "--access-authorized",
        action="store_true",
        help="Assert that the user has independently accepted and verified gated access.",
    )
    return parser


def _local_probe(config_path: Path, *, access_authorized: bool) -> TeacherEnvironmentProbe:
    config = load_teacher_config(config_path)
    torch_spec = importlib.util.find_spec("torch")
    cuda_available = False
    cuda_device_count = 0
    if torch_spec is not None:
        import torch

        cuda_available = bool(torch.cuda.is_available())
        cuda_device_count = int(torch.cuda.device_count()) if cuda_available else 0
    return TeacherEnvironmentProbe(
        model_id=config.model_id,
        model_revision=config.revision,
        access_authorized=access_authorized,
        nemo_available=importlib.util.find_spec("nemo") is not None,
        torch_available=torch_spec is not None,
        cuda_available=cuda_available,
        cuda_device_count=cuda_device_count,
        free_storage_bytes=shutil.disk_usage(Path.cwd()).free,
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    mode: PreflightMode = args.mode
    report = evaluate_teacher_preflight(
        _local_probe(args.config, access_authorized=args.access_authorized),
        mode=mode,
    )
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=True, sort_keys=True))
    return 0 if report.ready else 2


if __name__ == "__main__":
    raise SystemExit(main())
