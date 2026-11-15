"""PHN-006: freeze calibration-selected artifacts before final evaluation."""

import argparse
import json
import math
import numbers
import os
import shutil
from pathlib import Path

try:
    from scripts.model import finetune_mobile_phoneme as original
except ModuleNotFoundError:
    import finetune_mobile_phoneme as original


def validate_per_metrics(metrics):
    """DEC-040: NaN comparisons must never turn a failed measurement into success."""
    for group in ("all", "target19"):
        value = metrics[group]["phoneme_error_rate"]
        if (
            isinstance(value, bool)
            or not isinstance(value, numbers.Real)
            or not math.isfinite(value)
            or value < 0
        ):
            raise ValueError("PER must be finite and nonnegative")


def capture_selection_helper(root, selection):
    """PHN-006: future freezes include the implementation that ranks candidates."""
    target = Path(root) / "selection-helper.py"
    with target.open("xb") as stream:
        stream.write(Path(__file__).read_bytes())
    selection["selection_helper_sha256"] = original.sha(target)


def validate_selection_helper(root, selection):
    expected = selection.get("selection_helper_sha256")
    if expected is not None:
        source = Path(root) / "selection-helper.py"
        if not source.is_file() or original.sha(source) != expected:
            raise ValueError("frozen selection helper changed")


def validate_export_evaluation(
    manifest, report, measured, checkpoint_sha, dataset_sha, model_sha, decoder
):
    """DEC-040: accept only metrics replayed from the exact delivered ONNX."""
    format_name = {"phoneme.fp32.onnx": "fp32", "phoneme.int8.onnx": "int8"}.get(
        manifest.get("model_file")
    )
    if (
        format_name is None
        or report.get("chosen") != format_name
        or manifest.get("checkpoint_sha256") != checkpoint_sha
        or manifest.get("dataset_sha256") != dataset_sha
        or manifest.get("model_sha256") != model_sha
        or manifest.get("decoder") != decoder
        or report.get("metrics", {}).get(format_name) != measured
    ):
        raise ValueError("export metrics differ from bound model replay")
    validate_per_metrics(measured)
    return measured


def select_candidate(results, baseline, regression_anchor=None):
    validate_per_metrics(baseline)
    broader_reference = baseline["all"]["phoneme_error_rate"]
    if regression_anchor is not None:
        validate_per_metrics(regression_anchor)
        broader_reference = min(
            broader_reference, regression_anchor["all"]["phoneme_error_rate"]
        )
    candidates = []
    for name, result in results.items():
        if result.get("evaluation_accessed") is not False:
            raise ValueError("experiment accessed evaluation during selection")
        metrics = result["calibration"]
        validate_per_metrics(metrics)
        target = metrics["target19"]["phoneme_error_rate"]
        overall = metrics["all"]["phoneme_error_rate"]
        if (
            target < baseline["target19"]["phoneme_error_rate"]
            and overall <= broader_reference + 0.01
        ):
            candidates.append((0.7 * target + 0.3 * overall, name))
    if not candidates:
        raise ValueError("no improved calibration candidate")
    return min(candidates)[1]


def validate_final_metrics(
    baseline, candidate, parity_disagreements, regression_anchor=None
):
    validate_per_metrics(baseline)
    validate_per_metrics(candidate)
    broader_reference = baseline["all"]["phoneme_error_rate"]
    if regression_anchor is not None:
        validate_per_metrics(regression_anchor)
        broader_reference = min(
            broader_reference, regression_anchor["all"]["phoneme_error_rate"]
        )
    if parity_disagreements != 0:
        raise ValueError("FP32 export differs from selected model")
    if (
        candidate["target19"]["phoneme_error_rate"]
        >= baseline["target19"]["phoneme_error_rate"]
    ):
        raise ValueError("candidate did not improve final target PER")
    if candidate["all"]["phoneme_error_rate"] > broader_reference + 0.01:
        raise ValueError("broader-vocabulary regression exceeds gate")


def validate_selection_binding(result, config, checkpoint_sha, dataset_sha):
    if result.get("checkpoint_sha256") != checkpoint_sha:
        raise ValueError("checkpoint differs from its calibration report")
    if config.get("dataset_sha256") != dataset_sha:
        raise ValueError("dataset differs from the winning run configuration")


def validate_comparison_rows(baseline, candidate):
    # Expanded training may append only train rows; calibration/evaluation must
    # describe the same recordings for a comparable selection score.
    if candidate[: len(baseline)] != baseline or any(
        row["split"] != "train" for row in candidate[len(baseline) :]
    ):
        raise ValueError(
            "selection requires unchanged original rows and heldout splits"
        )


def main():
    root = Path("D:/VaakMitraData/artifacts")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--baseline-root", type=Path, default=root / "phoneme-ta19-v2-early"
    )
    parser.add_argument("--run", type=Path, action="append")
    parser.add_argument(
        "--output-root", type=Path, default=root / "phoneme-ta19-v3-improved"
    )
    args = parser.parse_args()
    base = args.baseline_root
    names = ["balanced", "quality", "channel", "expanded-channel"]
    paths = (
        {str(p.resolve()): p for p in args.run}
        if args.run
        else {name: root / f"phoneme-improvement-{name}-v1" for name in names}
    )
    results = {
        name: json.loads((p / "training-results.json").read_text())
        for name, p in paths.items()
    }
    baseline = json.loads((base / "training-results.json").read_text())["calibration"]
    baseline_meta, _ = original.load_run(base)
    for candidate, path in paths.items():
        cfg = json.loads((path / "config.json").read_text())
        inputs = Path(cfg["input_root"])
        candidate_meta, _ = original.load_run(inputs)
        validate_comparison_rows(baseline_meta["rows"], candidate_meta["rows"])
        validate_selection_binding(
            results[candidate],
            cfg,
            original.sha(path / "best.pt"),
            original.sha(inputs / "dataset.json"),
        )
    name = select_candidate(results, baseline)
    run = paths[name]
    config = json.loads((run / "config.json").read_text())
    inputs = Path(config["input_root"])
    validate_selection_binding(
        results[name],
        config,
        original.sha(run / "best.pt"),
        original.sha(inputs / "dataset.json"),
    )
    output = args.output_root
    output.mkdir(parents=True, exist_ok=False)
    selection = {
        "selection_split": "calibration",
        "evaluation_accessed": False,
        "criterion": ".7 target19 PER + .3 overall PER, target improvement and no >1pp overall regression",
        "winner": name,
        "winner_run": str(run),
        "input_root": str(inputs),
        "baseline_calibration": baseline,
        "experiments": results,
        "checkpoint_sha256": original.sha(run / "best.pt"),
        "dataset_sha256": original.sha(inputs / "dataset.json"),
        "baseline_dataset_sha256": original.sha(base / "dataset.json"),
        "baseline_checkpoint_sha256": original.sha(base / "best.pt"),
    }
    # Written before any new held-out evaluation is executed.
    original.write(output / "selection.json", selection)
    for filename in [
        "dataset.json",
        "vocabulary.json",
        "input-binding.json",
        "cache-complete.json",
    ]:
        shutil.copyfile(inputs / filename, output / filename)
    if (inputs / "expansion-manifest.json").exists():
        shutil.copyfile(
            inputs / "expansion-manifest.json", output / "expansion-manifest.json"
        )
    os.link(inputs / "audio.npy", output / "audio.npy")
    shutil.copyfile(run / "best.pt", output / "best.pt")
    shutil.copyfile(run / "config.json", output / "active-training-config.json")
    shutil.copyfile(run / "history.json", output / "history.json")
    original.write(output / "training-results.json", results[name])
    original.load_run(output)
    print(
        json.dumps(
            {
                "winner": name,
                "output": str(output),
                "calibration": results[name]["calibration"],
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
