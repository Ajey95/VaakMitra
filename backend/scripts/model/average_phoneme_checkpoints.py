"""PHN-001/006: calibration-only same-source checkpoint averaging."""

from __future__ import annotations

import argparse
import json
import math
import numbers
import shutil
import time
from pathlib import Path

import torch

try:
    from scripts.model import finetune_mobile_phoneme as original
    from scripts.model.improve_mobile_phoneme import create_run_directory
    from scripts.model.select_phoneme_decoder import resolve_training_provenance
    from scripts.model.select_phoneme_improvement import validate_selection_binding
except ModuleNotFoundError:
    import finetune_mobile_phoneme as original
    from improve_mobile_phoneme import create_run_directory
    from select_phoneme_decoder import resolve_training_provenance
    from select_phoneme_improvement import validate_selection_binding

from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc, checkpoint_frame_shift


def average_states(a, b, right_weight=0.5):
    if (
        isinstance(right_weight, bool)
        or not isinstance(right_weight, numbers.Real)
        or not math.isfinite(right_weight)
        or not 0 < right_weight < 1
    ):
        raise ValueError("averaging weight must be finite and strictly between 0 and 1")
    for key in ("binding", "dataset_sha256", "encoder_blocks"):
        if a[key] != b[key]:
            raise ValueError("incompatible checkpoint " + key)
    if checkpoint_frame_shift(a) != checkpoint_frame_shift(b):
        raise ValueError("different frame contract")
    initial = a["experiment_config"].get("initial_checkpoint_sha256")
    if not initial or initial != b["experiment_config"].get(
        "initial_checkpoint_sha256"
    ):
        raise ValueError("weight averaging requires shared initialization")
    if a["model"].keys() != b["model"].keys():
        raise ValueError("different parameter keys")
    result = {}
    for key, left in a["model"].items():
        right = b["model"][key]
        if left.shape != right.shape or left.dtype != right.dtype:
            raise ValueError("different tensor contract")
        if torch.is_floating_point(left):
            if not torch.isfinite(left).all() or not torch.isfinite(right).all():
                raise ValueError("nonfinite weights")
            result[key] = left * (1 - right_weight) + right * right_weight
        elif key.endswith("num_batches_tracked"):
            result[key] = torch.maximum(left, right)
        elif torch.equal(left, right):
            result[key] = left.clone()
        else:
            raise ValueError("different fixed buffer")
    return result


def unique_training_seconds(configs, reports):
    """DEC-042: best/terminal views of one exclusive run share its loop duration."""
    if not configs or len(configs) != len(reports):
        raise ValueError("source configurations and durations differ")
    durations = {}
    for config, report in zip(configs, reports, strict=True):
        seconds = report["seconds"]
        if (
            isinstance(seconds, bool)
            or not isinstance(seconds, numbers.Real)
            or not math.isfinite(seconds)
            or seconds < 0
        ):
            raise ValueError("invalid source training duration")
        source = json.dumps(config, sort_keys=True)
        if source in durations and durations[source] != seconds:
            raise ValueError("same source has conflicting duration")
        durations[source] = seconds
    return sum(durations.values())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--right-weight", type=float, default=0.5)
    args = parser.parse_args()
    if len(args.run) != 2 or not torch.cuda.is_available():
        raise ValueError("two parents and CUDA required")
    read = lambda p: json.loads(p.read_text(encoding="utf8"))
    # DEC-049: authenticate the configuration used for parent/time accounting.
    provenance = [resolve_training_provenance(p) for p in args.run]
    configs = [read(config) for config, _ in provenance]
    results = [read(p / "training-results.json") for p in args.run]
    inputs = Path(configs[0]["input_root"])
    if any(Path(c["input_root"]).resolve() != inputs.resolve() for c in configs):
        raise ValueError("different datasets")
    for path, cfg, result in zip(args.run, configs, results, strict=True):
        if result["evaluation_accessed"] is not False:
            raise ValueError("parent accessed evaluation")
        validate_selection_binding(
            result,
            cfg,
            original.sha(path / "best.pt"),
            original.sha(inputs / "dataset.json"),
        )
    original.OUT = inputs
    meta, vocab = original.load_run()
    states = [
        torch.load(p / "best.pt", map_location="cpu", weights_only=True)
        for p in args.run
    ]
    if states[0]["binding"] != meta["binding"] or states[0][
        "dataset_sha256"
    ] != original.sha(inputs / "dataset.json"):
        raise ValueError("dataset binding differs")
    if states[0]["encoder_blocks"] != 5:
        raise ValueError("this comparison requires the five-block student")
    merged = average_states(*states, right_weight=args.right_weight)
    output = create_run_directory(args.output_root)
    started = time.monotonic()
    torch.set_num_threads(4)
    frame = checkpoint_frame_shift(states[0])
    model = MobilePhonemeCtc(len(vocab["tokens"]), 5, frame_shift_ms=frame).cuda()
    model.load_state_dict(merged)
    calibration = original.evaluate(model, meta, "calibration", "cuda")
    parents = [
        {
            "run": str(path),
            "checkpoint_sha256": result["checkpoint_sha256"],
            "selected_epoch": result["selected_epoch"],
            "training_seconds": result["seconds"],
            "retained_target_train": cfg["retained_target_train"],
            "weight": weight,
        }
        for path, cfg, result, weight in zip(
            args.run,
            configs,
            results,
            [1 - args.right_weight, args.right_weight],
            strict=True,
        )
    ]
    composition = (
        f"Weighted average ({1 - args.right_weight:.3f},{args.right_weight:.3f}) "
        "of two same-initialization fine-tuned checkpoints; no additional gradient updates"
    )
    config = {
        "input_root": str(inputs),
        "dataset_sha256": original.sha(inputs / "dataset.json"),
        "initial_checkpoint_sha256": configs[0]["initial_checkpoint_sha256"],
        "composition": composition,
        "right_weight": args.right_weight,
        "parents": parents,
        "binding": meta["binding"],
        "frame_shift_ms": frame,
        "selection_split": "calibration",
        "evaluation_accessed": False,
        "retained_target_train": max(c["retained_target_train"] for c in configs),
        "allow_expanded_data": bool(meta.get("parent_binding")),
        "minimum_extra_quality": 0,
        "training_entrypoint_sha256": original.sha(Path(__file__)),
        "base_runner_sha256": original.sha(Path(original.__file__)),
        "gpu": torch.cuda.get_device_name(),
    }
    original.save(
        output / "best.pt",
        {
            "model": merged,
            "binding": meta["binding"],
            "dataset_sha256": config["dataset_sha256"],
            "encoder_blocks": 5,
            "frame_shift_ms": frame,
            "epoch": 0,
            "composition": composition,
            "parents": parents,
            "experiment_config": config,
        },
    )
    report = {
        "selected_epoch": 0,
        "composition": composition,
        "calibration": calibration,
        "evaluation_accessed": False,
        "checkpoint_sha256": original.sha(output / "best.pt"),
        "seconds": time.monotonic() - started,
        "source_training_seconds": unique_training_seconds(configs, results),
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "approved_for_child_scoring": False,
    }
    original.write(output / "config.json", config)
    original.write(output / "history.json", [])
    original.write(output / "training-results.json", report)
    shutil.copyfile(__file__, output / "training-entrypoint.py")
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
