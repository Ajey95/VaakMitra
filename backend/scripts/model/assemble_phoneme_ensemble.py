"""DEC-048 / PHN-001..006: fixed two-member posterior mean, calibration only."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path

import torch

import app.vaakmitra_word.mobile_student_model as encoder_architecture
import app.vaakmitra_word.phoneme_ctc as architecture
from scripts.model import finetune_mobile_phoneme as original
from scripts.model.improve_mobile_phoneme import create_run_directory
from scripts.model.select_phoneme_decoder import resolve_training_provenance


def validate_parent_states(states, dataset_sha, binding):
    if len(states) != 2:
        raise ValueError("exactly two parents required")
    for state in states:
        if (
            state.get("model_kind", "single") != "single"
            or state.get("binding") != binding
            or state.get("dataset_sha256") != dataset_sha
            or type(state.get("encoder_blocks")) is not int
            or state["encoder_blocks"] != 5
            or type(state.get("frame_shift_ms", 40)) is not int
            or state.get("frame_shift_ms", 40) != 40
        ):
            raise ValueError("ensemble parent data or architecture differs")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--parent", type=Path, action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    args = parser.parse_args()
    if len(args.parent) != 2 or not torch.cuda.is_available():
        raise ValueError("two parents and local CUDA required")
    original.OUT = args.input_root.resolve()
    meta, vocab = original.load_run()
    dataset_sha = original.sha(original.OUT / "dataset.json")
    states, parents = [], []
    for path in args.parent:
        config_path, source = resolve_training_provenance(path)
        cfg = json.loads(config_path.read_text(encoding="utf8"))
        report = json.loads((path / "training-results.json").read_text(encoding="utf8"))
        digest = original.sha(path / "best.pt")
        if (
            report.get("evaluation_accessed") is not False
            or report.get("checkpoint_sha256") != digest
            or cfg.get("dataset_sha256") != dataset_sha
        ):
            raise ValueError("parent report, data or selection discipline changed")
        states.append(
            torch.load(path / "best.pt", map_location="cpu", weights_only=True)
        )
        parents.append(
            {
                "run": str(path),
                "checkpoint_sha256": digest,
                "selected_epoch": report["selected_epoch"],
                "config_sha256": original.sha(config_path),
                "config_file": config_path.name,
                "training_entrypoint_sha256": original.sha(source),
                "report_sha256": original.sha(path / "training-results.json"),
                "weight": 0.5,
                "parent_reported_seconds": report["seconds"],
            }
        )
    validate_parent_states(states, dataset_sha, meta["binding"])
    output = create_run_directory(args.output_root)
    torch.set_num_threads(4)
    model = architecture.MobilePhonemeEnsemble(len(vocab["tokens"]))
    for member, state in zip(model.members, states, strict=True):
        member.load_state_dict(state["model"])
    model = model.cuda().eval().requires_grad_(False)
    arch_source = Path(architecture.__file__)
    config = {
        "input_root": str(original.OUT),
        "output_root": str(output),
        "dataset_sha256": dataset_sha,
        "binding": meta["binding"],
        "model_kind": "posterior_mean_2",
        "ensemble_members": 2,
        "ensemble_weights": [0.5, 0.5],
        "frame_shift_ms": 40,
        "composition": "Uniform arithmetic mean of two per-frame acoustic posteriors; no additional gradient updates",
        "composition_method": "posterior_mean_2",
        "parents": parents,
        "retained_target_train": sum(
            row["split"] == "train" and row["is_target"] for row in meta["rows"]
        ),
        "selection_split": "calibration",
        "evaluation_accessed": False,
        "training_entrypoint_sha256": original.sha(Path(__file__)),
        "base_runner_sha256": original.sha(Path(original.__file__)),
        "architecture_source_sha256": original.sha(arch_source),
        "encoder_architecture_source_sha256": original.sha(
            Path(encoder_architecture.__file__)
        ),
        "gpu": torch.cuda.get_device_name(),
    }
    started = time.monotonic()
    calibration = original.evaluate(model, meta, "calibration", "cuda")
    checkpoint = {
        "model": model.state_dict(),
        "binding": meta["binding"],
        "dataset_sha256": dataset_sha,
        "encoder_blocks": 5,
        "frame_shift_ms": 40,
        "model_kind": "posterior_mean_2",
        "ensemble_members": 2,
        "ensemble_weights": [0.5, 0.5],
        "architecture_source_sha256": config["architecture_source_sha256"],
        "encoder_architecture_source_sha256": config[
            "encoder_architecture_source_sha256"
        ],
        "epoch": 0,
        "experiment_config": config,
    }
    original.save(output / "best.pt", checkpoint)
    report = {
        "selected_epoch": 0,
        "composition": config["composition"],
        "formation_method": "posterior_mean_2",
        "gradient_epochs": 0,
        "calibration": calibration,
        "evaluation_accessed": False,
        "checkpoint_sha256": original.sha(output / "best.pt"),
        "seconds": time.monotonic() - started,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "parameters": sum(p.numel() for p in model.parameters()),
        "approved_for_child_scoring": False,
    }
    original.write(output / "config.json", config)
    original.write(output / "history.json", [])
    original.write(output / "training-results.json", report)
    shutil.copyfile(__file__, output / "training-entrypoint.py")
    shutil.copyfile(arch_source, output / "architecture-entrypoint.py")
    shutil.copyfile(
        encoder_architecture.__file__, output / "encoder-architecture-source.py"
    )
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
