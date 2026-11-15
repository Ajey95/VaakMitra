"""PHN-006 / DEC-035: joint calibration-only weight and audio-only decoder selection."""

import argparse
import json
import os
import shutil
from pathlib import Path

import numpy as np
import torch

from app.vaakmitra_word.phoneme_ctc import model_from_checkpoint
from app.vaakmitra_word.phoneme_decoder import decode_logits, validate_decoder
from scripts.model import finetune_mobile_phoneme as original
from scripts.model.phoneme_checkpoint_dependencies import validate_ensemble_dependencies
from scripts.model.select_phoneme_improvement import (
    capture_selection_helper,
    select_candidate,
    validate_selection_binding,
)

# DEC-039/040: identity, not a mutable directory name, fixes the R5 allowance.
FIXED_ANCHOR_CHECKPOINT = (
    "cd4e738aa3605d0a99047c955cc09af3295b277af5d09de8bc2f396834446574"
)
FIXED_ANCHOR_REPORT = "34990c2f9e256e003fd3673a5e3863216d3122d7d425294092e7f83deb729619"
R5_BASELINE_CHECKPOINT = (
    "fd9ce7f6f0d9cbf6830512a2ab13dc25e9aeee2dc0d7ba49f67b122277b40315"
)
FIXED_ANCHOR_ROOT = Path("D:/VaakMitraData/artifacts/phoneme-ta19-v5-improved")


def resolve_regression_anchor_root(baseline_root, requested):
    """DEC-040: R5 cannot omit its anchor; later continuations inherit it."""
    baseline_root = Path(baseline_root)
    selected = baseline_root / "selection.json"
    prior = json.loads(selected.read_text(encoding="utf8")) if selected.exists() else {}
    inherited = prior.get("regression_anchor")
    if (
        inherited is not None
        and inherited.get("checkpoint_sha256") != FIXED_ANCHOR_CHECKPOINT
    ):
        raise ValueError("inherited regression anchor identity differs")
    required = (
        inherited is not None
        or original.sha(baseline_root / "best.pt") == R5_BASELINE_CHECKPOINT
    )
    if requested is None:
        return (
            Path(inherited["root"])
            if inherited is not None
            else (FIXED_ANCHOR_ROOT if required else None)
        )
    requested = Path(requested)
    if original.sha(requested / "best.pt") != FIXED_ANCHOR_CHECKPOINT:
        raise ValueError("fixed regression anchor identity differs")
    return requested


def load_selected_model(checkpoint, meta, dataset_sha, vocabulary_size, device):
    state = torch.load(checkpoint, map_location="cpu", weights_only=True)
    if (
        state["binding"] != meta["binding"]
        or state.get("dataset_sha256") != dataset_sha
    ):
        raise ValueError("checkpoint data binding changed")
    validate_ensemble_dependencies(checkpoint, state)
    model = model_from_checkpoint(state, vocabulary_size)
    return model.to(device).eval()


def validate_report_calibration(report, computed):
    """PHN-006 / DEC-037: a beam baseline must not be checked as greedy."""
    decoder = validate_decoder(report.get("decoder", {"type": "greedy"}), 61)
    allowed = [
        {"type": "greedy"},
        {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 8},
    ]
    if decoder not in allowed or computed.get(decoder["type"]) != report.get(
        "calibration"
    ):
        raise ValueError(
            "recomputed declared-decoder calibration differs from bound report"
        )


def resolve_training_provenance(run):
    """PHN-001/006: resolve historical selected roots before publishing a winner."""
    run = Path(run)
    config_path = run / "config.json"
    if not config_path.exists():
        config_path = run / "active-training-config.json"
    config = json.loads(config_path.read_text(encoding="utf8"))
    source = run / "training-entrypoint.py"
    if not source.exists():
        selection = json.loads((run / "selection.json").read_text(encoding="utf8"))
        source = Path(selection["winner_run"]) / "training-entrypoint.py"
    if not source.exists() or original.sha(source) != config.get(
        "training_entrypoint_sha256"
    ):
        raise ValueError("original training source differs from bound configuration")
    checkpoint = torch.load(run / "best.pt", map_location="cpu", weights_only=True)
    if checkpoint.get("experiment_config") != config:
        raise ValueError(
            "published configuration differs from checkpoint experiment_config"
        )
    return config_path, source


def load_baseline_report(root, vocabulary_size):
    """PHN-006: authenticate deployment decoder before accepting baseline metrics."""
    root = Path(root)
    decoder = original.frozen_decoder(root, vocabulary_size)
    report = json.loads((root / "training-results.json").read_text(encoding="utf8"))
    if (
        validate_decoder(report.get("decoder", {"type": "greedy"}), vocabulary_size)
        != decoder
    ):
        raise ValueError("baseline report decoder differs from frozen deployment")
    return report


def load_regression_anchor(root, dataset_sha, vocabulary_size):
    """PHN-006 / DEC-039: a fixed anchor must authenticate on exactly the same data."""
    root = Path(root)
    if original.sha(root / "dataset.json") != dataset_sha:
        raise ValueError("regression anchor uses different data")
    if (
        original.sha(root / "best.pt") != FIXED_ANCHOR_CHECKPOINT
        or original.sha(root / "training-results.json") != FIXED_ANCHOR_REPORT
        or not (root / "selection.json").is_file()
        or not (root / "selection-freeze.json").is_file()
    ):
        raise ValueError("fixed regression anchor identity or freeze differs")
    report = load_baseline_report(root, vocabulary_size)
    if report.get("checkpoint_sha256") != original.sha(root / "best.pt"):
        raise ValueError("regression anchor checkpoint differs")
    selected = root / "selection.json"
    if (
        selected.exists()
        and json.loads(selected.read_text(encoding="utf8")).get("dataset_sha256")
        != dataset_sha
    ):
        raise ValueError("regression anchor selected different data")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline-root", type=Path, required=True)
    parser.add_argument("--run", type=Path, action="append", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--regression-anchor-root", type=Path)
    args = parser.parse_args()
    torch.set_num_threads(4)
    if not torch.cuda.is_available():
        raise ValueError("local CUDA required")
    meta, vocab = original.load_run(args.baseline_root)
    dataset_sha = original.sha(args.baseline_root / "dataset.json")
    args.regression_anchor_root = resolve_regression_anchor_root(
        args.baseline_root, args.regression_anchor_root
    )
    audio = np.load(args.baseline_root / "audio.npy", mmap_mode="r")
    indices = [i for i, r in enumerate(meta["rows"]) if r["split"] == "calibration"]
    rows = [meta["rows"][i] for i in indices]
    baseline_run_report = load_baseline_report(args.baseline_root, len(vocab["tokens"]))
    baseline_report = baseline_run_report["calibration"]
    anchor = None
    if args.regression_anchor_root is not None:
        anchor_report = load_regression_anchor(
            args.regression_anchor_root, dataset_sha, len(vocab["tokens"])
        )
        anchor = {
            "root": str(args.regression_anchor_root),
            "calibration": anchor_report["calibration"],
            "checkpoint_sha256": original.sha(args.regression_anchor_root / "best.pt"),
            "dataset_sha256": dataset_sha,
            "report_sha256": original.sha(
                args.regression_anchor_root / "training-results.json"
            ),
        }
    decoders = [
        {"type": "greedy"},
        {"type": "ctc_prefix_beam", "beam_width": 5, "nonblank_top_k": 8},
    ]
    results = {}
    paths = [args.baseline_root] + args.run
    for path in paths:
        checkpoint_sha = original.sha(path / "best.pt")
        if path != args.baseline_root:
            config = json.loads((path / "config.json").read_text())
            report = json.loads((path / "training-results.json").read_text())
            validate_selection_binding(report, config, checkpoint_sha, dataset_sha)
            if (
                Path(config["input_root"]).resolve() != args.baseline_root.resolve()
                or report["evaluation_accessed"] is not False
            ):
                raise ValueError("trial inputs or selection discipline changed")
        model = load_selected_model(
            path / "best.pt", meta, dataset_sha, len(vocab["tokens"]), "cuda"
        )
        predictions = [[] for _ in decoders]
        with torch.inference_mode():
            for start in range(0, len(indices), 64):
                raw = (
                    model(
                        torch.from_numpy(
                            np.array(audio[indices[start : start + 64]])
                        ).cuda()
                    )
                    .cpu()
                    .numpy()
                )
                for j, decoder in enumerate(decoders):
                    predictions[j].extend(decode_logits(x, decoder) for x in raw)
        for decoder, preds in zip(decoders, predictions):
            name = path.name + "/" + decoder["type"]
            result = {
                "calibration": original.metrics(preds, rows),
                "decoder": decoder,
                "checkpoint_sha256": checkpoint_sha,
                "winner_run": str(path),
                "evaluation_accessed": False,
            }
            results[name] = result
            print(json.dumps({"candidate": name, **result}), flush=True)
        validate_report_calibration(
            baseline_run_report if path == args.baseline_root else report,
            {
                decoder["type"]: results[path.name + "/" + decoder["type"]][
                    "calibration"
                ]
                for decoder in decoders
            },
        )
        del model
        torch.cuda.empty_cache()
    winner = select_candidate(
        results,
        baseline_report,
        regression_anchor=anchor["calibration"] if anchor else None,
    )
    result = results[winner]
    run = Path(result["winner_run"])
    training_config_path, training_source_path = resolve_training_provenance(run)
    output = args.output_root
    output.mkdir(parents=True, exist_ok=False)
    selection = {
        "winner": winner,
        "winner_run": str(run),
        "decoder": result["decoder"],
        "selection_split": "calibration",
        "evaluation_accessed": False,
        "criterion": ".7 target PER + .3 overall PER; target improvement; <=1pp overall regression",
        "checkpoint_sha256": result["checkpoint_sha256"],
        "dataset_sha256": dataset_sha,
        "baseline_checkpoint_sha256": original.sha(args.baseline_root / "best.pt"),
        "baseline_calibration": baseline_report,
        "regression_anchor": anchor,
        "experiments": results,
        "selector_sha256": original.sha(__file__),
        "decoder_source_sha256": original.sha(
            Path(original.BACKEND) / "app/vaakmitra_word/phoneme_decoder.py"
        ),
    }
    capture_selection_helper(output, selection)
    original.write(
        output / "selection.json", selection
    )  # Before any held-out inference.
    original.write(
        output / "selection-freeze.json",
        {
            "selection_sha256": original.sha(output / "selection.json"),
            "checkpoint_sha256": result["checkpoint_sha256"],
            "selection_split": "calibration",
        },
    )
    for filename in [
        "dataset.json",
        "vocabulary.json",
        "input-binding.json",
        "cache-complete.json",
        "expansion-manifest.json",
    ]:
        shutil.copyfile(args.baseline_root / filename, output / filename)
    os.link(args.baseline_root / "audio.npy", output / "audio.npy")
    shutil.copyfile(run / "best.pt", output / "best.pt")
    shutil.copyfile(training_config_path, output / "active-training-config.json")
    shutil.copyfile(training_source_path, output / "training-entrypoint.py")
    for source, target in [
        ("history.json", "history.json"),
    ]:
        if (run / source).exists():
            shutil.copyfile(run / source, output / target)
    training_report = json.loads((run / "training-results.json").read_text())
    original.write(output / "weight-training-results.json", training_report)
    original.write(
        output / "training-results.json",
        {
            **training_report,
            "calibration": result["calibration"],
            "decoder": result["decoder"],
            "weight_training_calibration": training_report["calibration"],
        },
    )
    shutil.copyfile(__file__, output / "selection-entrypoint.py")
    shutil.copyfile(
        Path(original.BACKEND) / "app/vaakmitra_word/phoneme_decoder.py",
        output / "decoder-source.py",
    )
    print(
        json.dumps(
            {
                "frozen": str(output),
                "winner": winner,
                "calibration": result["calibration"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
