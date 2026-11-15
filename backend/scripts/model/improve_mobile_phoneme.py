"""DEC-030/PHN-001..006: calibration-only continuation, independent run artifacts."""

from __future__ import annotations

import argparse
import ctypes
import json
import math
import numbers
import os
import shutil
import time
from collections import Counter
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.utils.data import DataLoader, WeightedRandomSampler

try:
    from scripts.model import finetune_mobile_phoneme as original
except ModuleNotFoundError:
    import finetune_mobile_phoneme as original

from app.vaakmitra_word.phoneme_ctc import MobilePhonemeCtc, checkpoint_frame_shift


def balanced_weights(rows, target_fraction):
    if not 0 < target_fraction < 1 or any(r["split"] != "train" for r in rows):
        raise ValueError("sampling requires only train rows and a fraction in (0,1)")
    counts = Counter(r["word_id"] for r in rows if r["is_target"])
    other = sum(not r["is_target"] for r in rows)
    if not counts or not other:
        raise ValueError("both target and other train rows are required")
    return np.asarray(
        [
            target_fraction / len(counts) / counts[r["word_id"]]
            if r["is_target"]
            else (1 - target_fraction) / other
            for r in rows
        ],
        dtype=np.float64,
    )


def select_training_indices(rows, scores, minimum):
    indices = []
    for i, row in enumerate(rows):
        if row["split"] != "train":
            continue
        if row["audio_path"] not in scores:
            raise ValueError("missing training quality score")
        if scores[row["audio_path"]] >= minimum:
            indices.append(i)
    return indices


def select_extra_quality_indices(rows, original_count, minimum):
    if not 0 <= minimum <= 1 or not 0 < original_count <= len(rows):
        raise ValueError("invalid extra-data quality threshold or original count")
    selected = []
    for i, row in enumerate(rows):
        if row["split"] != "train":
            continue
        if i < original_count:
            selected.append(i)
            continue
        score = row.get("quality_score", float("nan"))
        if not math.isfinite(score) or not 0 <= score <= 1:
            raise ValueError("missing or invalid extra-data quality score")
        if score >= minimum:
            selected.append(i)
    return selected


def shift_in_padding(audio, amount):
    if not amount:
        return audio
    width = abs(amount)
    if width >= audio.shape[-1]:
        raise ValueError("shift exceeds waveform")
    # Roll only when both boundaries are silent: no samples wrap into speech.
    safe = (audio[:, :width].abs().amax(1) == 0) & (
        audio[:, -width:].abs().amax(1) == 0
    )
    return torch.where(safe[:, None], torch.roll(audio, amount, dims=1), audio)


def validate_initial_checkpoint(
    state, meta, dataset_sha, encoder_blocks, allow_expansion=False
):
    if state.get("model_kind", "single") != "single":
        raise ValueError("continuation trainer requires a single acoustic model")
    checkpoint_frame_shift(state)
    expanded = (
        allow_expansion
        and state["binding"] == meta.get("parent_binding")
        and state.get("dataset_sha256") == meta.get("parent_dataset_sha256")
    )
    if expanded:
        for key in ("base_sha256", "vocabulary_sha256"):
            if state["binding"].get(key) != meta["binding"].get(key):
                raise ValueError(f"expanded checkpoint {key} differs")
    if state["binding"] != meta["binding"] and not expanded:
        raise ValueError("checkpoint binding differs")
    if state.get("encoder_blocks", 7) != encoder_blocks:
        raise ValueError("checkpoint architecture differs")
    if state.get("dataset_sha256") != dataset_sha and not expanded:
        raise ValueError("checkpoint dataset differs")


def rate_in_padding(audio, scale):
    from scipy.signal import resample_poly

    if scale not in (0.9, 1.0, 1.1):
        raise ValueError("unsupported training duration factor")
    if scale == 1:
        return audio
    values = resample_poly(audio.detach().cpu().numpy(), round(scale * 10), 10, axis=-1)
    changed = torch.from_numpy(values.copy()).to(device=audio.device, dtype=audio.dtype)
    difference = changed.shape[-1] - audio.shape[-1]
    if difference < 0:
        left = (-difference) // 2
        return nn.functional.pad(changed, (left, -difference - left))
    left = difference // 2
    right = difference - left
    safe = (changed[:, :left].abs().amax(1) == 0) & (
        changed[:, -right:].abs().amax(1) == 0
    )
    cropped = changed[:, left : changed.shape[-1] - right]
    return torch.where(safe[:, None], cropped, audio)


def tempo_in_padding(audio, factor):
    """DEC-050: independent-channel phase vocoder; preserve pitch and all speech."""
    if (
        isinstance(factor, bool)
        or not isinstance(factor, numbers.Real)
        or factor not in (1.0, 1.5, 2.0, 3.0)
    ):
        raise ValueError("unsupported pitch-preserving duration factor")
    if factor == 1:
        return audio
    if audio.ndim != 2 or not torch.is_floating_point(audio):
        raise ValueError("tempo requires a batch of floating point waveforms")
    n_fft, hop = 512, 128
    window = torch.hann_window(n_fft, dtype=audio.dtype, device=audio.device)
    spectrum = torch.stft(
        audio.detach(),
        n_fft,
        hop_length=hop,
        window=window,
        center=True,
        pad_mode="constant",
        return_complex=True,
    )
    steps = torch.arange(
        0, spectrum.shape[-1], 1 / factor, dtype=audio.dtype, device=audio.device
    )
    left = steps.floor().long()
    right = (left + 1).clamp_max(spectrum.shape[-1] - 1)
    fraction = (steps - left)[None, None, :]
    a, b = spectrum[..., left], spectrum[..., right]
    magnitude = a.abs() * (1 - fraction) + b.abs() * fraction
    expected = (
        2
        * math.pi
        * hop
        / n_fft
        * torch.arange(spectrum.shape[1], dtype=audio.dtype, device=audio.device)
    )[None, :, None]
    difference = b.angle() - a.angle() - expected
    difference = difference - 2 * math.pi * torch.round(difference / (2 * math.pi))
    increments = difference + expected
    phase = torch.cat((spectrum[..., :1].angle(), increments[..., :-1]), dim=-1).cumsum(
        -1
    )
    changed = torch.istft(
        torch.polar(magnitude, phase),
        n_fft,
        hop_length=hop,
        window=window,
        center=True,
        length=round(audio.shape[-1] * factor),
    )
    excess = changed.shape[-1] - audio.shape[-1]
    left_crop, right_crop = excess // 2, excess - excess // 2
    # Expansion is accepted per example only when the discarded regions are silent.
    # Long utterances retain their original waveform instead of losing phones.
    safe = (changed[:, :left_crop].abs().amax(1) == 0) & (
        changed[:, -right_crop:].abs().amax(1) == 0
    )
    cropped = changed[:, left_crop : changed.shape[-1] - right_crop]
    return torch.where(safe[:, None], cropped, audio)


def augment(audio, generator, mode):
    if mode == "none":
        return audio
    # Global rate perturbation is training-only, never target-conditioned timing.
    if mode == "rate":
        factor = (0.9, 1.0, 1.1)[int(torch.randint(3, (), generator=generator))]
        audio = rate_in_padding(audio, factor)
    if mode == "tempo":
        factor = (1.0, 1.5, 2.0, 3.0)[int(torch.randint(4, (), generator=generator))]
        audio = tempo_in_padding(audio, factor)
    amount = int(torch.randint(-1280, 1281, (), generator=generator))
    audio = shift_in_padding(audio, amount)
    if float(torch.rand((), generator=generator)) < 0.5:
        rms = audio.square().mean(1, keepdim=True).clamp_min(1e-12).sqrt()
        noise = torch.randn(audio.shape, generator=generator, dtype=audio.dtype).to(
            audio.device
        )
        audio = audio + noise * rms * 0.04
    if (
        mode in ("channel", "rate", "tempo")
        and float(torch.rand((), generator=generator)) < 0.3
    ):
        delay = 640
        audio = audio + nn.functional.pad(audio[:, :-delay], (delay, 0)) * 0.12
    return audio


def configure_recurrent_dropout(model, probability):
    """PHN-001 / DEC-039: training regularization leaves inference topology unchanged."""
    if not math.isfinite(probability) or not 0 <= probability <= 0.5:
        raise ValueError("unsupported recurrent dropout")
    model.sequence.dropout = float(probability)


def configure_blank_bias(model, offset):
    """DEC-044: one global blank prior; never a word or phoneme-specific rule."""
    if (
        isinstance(offset, bool)
        or not isinstance(offset, numbers.Real)
        or not math.isfinite(offset)
        or not -0.5 <= offset <= 0.5
    ):
        raise ValueError("blank bias must be a finite scalar in [-0.5,0.5]")
    if offset:
        with torch.no_grad():
            model.head.bias[0].add_(float(offset))


def deployment_checkpoint_decision(metrics, best, best_qualified, baseline, anchor):
    """DEC-046: qualification outranks a lower-scoring but undeployable fallback."""
    from scripts.model.select_phoneme_improvement import select_candidate

    value = (
        0.7 * metrics["target19"]["phoneme_error_rate"]
        + 0.3 * metrics["all"]["phoneme_error_rate"]
    )
    try:
        select_candidate(
            {"checkpoint": {"calibration": metrics, "evaluation_accessed": False}},
            baseline,
            regression_anchor=anchor,
        )
        qualified = True
    except ValueError as exc:
        if str(exc) != "no improved calibration candidate":
            raise
        qualified = False
    improved = (
        (not best_qualified or value < best)
        if qualified
        else (not best_qualified and value < best - 0.0001)
    )
    return value, qualified, improved


def configure_encoder_training(model, frozen, freeze_statistics=False):
    """PHN-001 / DEC-037: freezing includes BatchNorm state, not only learning rate."""
    model.encoder.requires_grad_(not frozen)
    model.encoder.train(model.training and not frozen)
    if freeze_statistics:
        for layer in model.encoder.modules():
            if isinstance(layer, nn.BatchNorm1d):
                layer.eval()


def create_run_directory(path):
    path = Path(path).resolve()
    path.mkdir(parents=True, exist_ok=False)
    return path


def run(args):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required")
    if args.epochs < 0:
        raise ValueError("epochs must be nonnegative")
    output = create_run_directory(args.output_root)
    original.OUT = args.input_root.resolve()
    meta, vocab = original.load_run()
    dataset_sha = original.sha(original.OUT / "dataset.json")
    deployment_decoder, deployment_reference, anchor_calibration = None, None, None
    if args.deployment_selection:
        from scripts.model.select_phoneme_decoder import (
            load_baseline_report,
            load_regression_anchor,
            resolve_regression_anchor_root,
        )

        root = original.OUT
        if (
            not (root / "selection.json").is_file()
            or not (root / "selection-freeze.json").is_file()
        ):
            raise ValueError("deployment checkpoint selection needs a frozen baseline")
        baseline_report = load_baseline_report(root, len(vocab["tokens"]))
        selected_reference = json.loads(
            (root / "selection.json").read_text(encoding="utf8")
        )
        if selected_reference.get(
            "dataset_sha256"
        ) != dataset_sha or baseline_report.get("checkpoint_sha256") != original.sha(
            root / "best.pt"
        ):
            raise ValueError("deployment reference checkpoint or dataset changed")
        deployment_decoder = baseline_report["decoder"]
        anchor_root = resolve_regression_anchor_root(root, None)
        anchor_record = None
        if anchor_root is not None:
            anchor_report = load_regression_anchor(
                anchor_root, dataset_sha, len(vocab["tokens"])
            )
            anchor_calibration = anchor_report["calibration"]
            anchor_record = {
                "root": str(anchor_root),
                "checkpoint_sha256": original.sha(anchor_root / "best.pt"),
                "report_sha256": original.sha(anchor_root / "training-results.json"),
                "calibration": anchor_calibration,
            }
        deployment_reference = {
            "root": str(root),
            "checkpoint_sha256": baseline_report["checkpoint_sha256"],
            "selection_sha256": original.sha(root / "selection.json"),
            "report_sha256": original.sha(root / "training-results.json"),
            "dataset_sha256": dataset_sha,
            "decoder": deployment_decoder,
            "calibration": baseline_report["calibration"],
            "anchor": anchor_record,
        }
    state = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    validate_initial_checkpoint(state, meta, dataset_sha, 5, args.allow_expanded_data)
    if args.allow_expanded_data:
        try:
            from scripts.model.prepare_phoneme_expansion import validate_expansion_rows
        except ModuleNotFoundError:
            from prepare_phoneme_expansion import validate_expansion_rows
        parent_root = Path(
            meta.get(
                "parent_input_root", "D:/VaakMitraData/artifacts/phoneme-ta19-v2-early"
            )
        )
        if original.sha(parent_root / "dataset.json") != meta["parent_dataset_sha256"]:
            raise ValueError("expanded input parent metadata changed")
        parent = json.loads((parent_root / "dataset.json").read_text())
        expansion = json.loads(
            (original.OUT / "expansion-manifest.json").read_text(encoding="utf8")
        )
        validate_expansion_rows(parent["rows"], meta["rows"], expansion["audit"])
        if (
            original.sha(original.OUT / "expansion-manifest.json")
            != meta["binding"]["expansion_sha256"]
        ):
            raise ValueError("expansion source manifest changed")
    torch.set_num_threads(4)
    torch.manual_seed(args.seed)
    torch.cuda.manual_seed_all(args.seed)
    generator = torch.Generator().manual_seed(args.seed)
    initial_frame_shift = checkpoint_frame_shift(state)
    frame_shift = args.frame_shift_ms or initial_frame_shift
    model = MobilePhonemeCtc(len(vocab["tokens"]), 5, frame_shift_ms=frame_shift).cuda()
    model.load_state_dict(state["model"])
    configure_blank_bias(model, args.blank_bias_offset)
    configure_recurrent_dropout(model, args.recurrent_dropout)
    optimizer = torch.optim.AdamW(
        [
            {"params": model.encoder.parameters(), "lr": args.encoder_lr},
            {
                "params": list(model.sequence.parameters())
                + list(model.head.parameters()),
                "lr": args.head_lr,
            },
        ],
        weight_decay=args.weight_decay,
    )
    dataset = original.Clips(meta, "train")
    quality_report = None
    if args.minimum_extra_quality > 0:
        if not args.allow_expanded_data or args.minimum_quality > 0:
            raise ValueError(
                "extra quality requires expanded data without a base quality filter"
            )
        dataset.indices = select_extra_quality_indices(
            meta["rows"],
            meta["parent_binding"]["row_count"],
            args.minimum_extra_quality,
        )
        quality_report = {
            "minimum_extra_quality": args.minimum_extra_quality,
            "original_rows_preserved": True,
            "retained_train": len(dataset.indices),
        }
    if args.minimum_quality > 0:
        source = [json.loads(line) for line in original.SOURCE.open(encoding="utf8")]
        review_path = (
            original.ROOT / "manifests/openslr127-word-v1-reviewed-machine-review.json"
        )
        review = json.loads(review_path.read_text())
        if review["dataset_manifest_hash"] != meta["binding"]["source_sha256"]:
            raise ValueError("quality manifest source binding differs")
        qualities = {r["sample_id"]: r["quality_score"] for r in review["approvals"]}
        scores = {r["audio_path"]: qualities[r["sample_id"]] for r in source}
        dataset.indices = select_training_indices(
            meta["rows"], scores, args.minimum_quality
        )
        quality_report = {
            "review_sha256": original.sha(review_path),
            "minimum": args.minimum_quality,
            "retained_train": len(dataset.indices),
        }
    rows = [meta["rows"][i] for i in dataset.indices]
    weights = balanced_weights(rows, args.target_fraction)
    criterion = nn.CTCLoss(blank=0, reduction="none", zero_infinity=False)
    config = {k: str(v) if isinstance(v, Path) else v for k, v in vars(args).items()}
    config.update(
        dataset_sha256=dataset_sha,
        initial_checkpoint_sha256=original.sha(args.checkpoint),
        binding=meta["binding"],
        selection_split="calibration",
        evaluation_accessed=False,
        sampler=(
            "none (zero-gradient calibration formation)"
            if args.epochs == 0
            else "equal app-word mass, uniform other clips"
        ),
        gpu=torch.cuda.get_device_name(),
        initial_frame_shift_ms=initial_frame_shift,
        frame_shift_ms=frame_shift,
    )
    config["quality_filter"] = quality_report
    if args.augmentation == "tempo":
        config["tempo_augmentation"] = {
            "method": "independent_batch_phase_vocoder_nfft512_hop128",
            "duration_factors": [1.0, 1.5, 2.0, 3.0],
            "unsafe_expansion": "retain_original_no_speech_truncation",
            "training_only": True,
        }
    config["deployment_reference"] = deployment_reference
    config["formation_method"] = (
        "global_blank_bias_calibration" if args.epochs == 0 else "gradient_continuation"
    )
    config["retained_target_train"] = sum(r["is_target"] for r in rows)
    config["training_entrypoint_sha256"] = original.sha(Path(__file__))
    config["base_runner_sha256"] = original.sha(Path(original.__file__))
    shutil.copyfile(__file__, output / "training-entrypoint.py")
    original.write(output / "config.json", config)
    baseline = original.evaluate(
        model, meta, "calibration", "cuda", decoder=deployment_decoder
    )

    def score(m):
        return (
            0.7 * m["target19"]["phoneme_error_rate"]
            + 0.3 * m["all"]["phoneme_error_rate"]
        )

    best, best_qualified, stale, history = score(baseline), False, 0, []
    if args.deployment_selection:
        best, best_qualified, _ = deployment_checkpoint_decision(
            baseline,
            float("inf"),
            False,
            deployment_reference["calibration"],
            anchor_calibration,
        )

    def checkpoint(epoch):
        return {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "epoch": epoch,
            "best": best,
            "best_qualified": best_qualified,
            "stale": stale,
            "binding": meta["binding"],
            "dataset_sha256": dataset_sha,
            "encoder_blocks": 5,
            "frame_shift_ms": frame_shift,
            "rng": torch.get_rng_state(),
            "cuda_rng": torch.cuda.get_rng_state_all(),
            "augmentation_rng": generator.get_state(),
            "experiment_config": config,
        }

    original.save(output / "best.pt", checkpoint(0))
    original.write(output / "baseline.json", baseline)
    print(
        json.dumps({"stage": "started", "output": str(output), "baseline": baseline}),
        flush=True,
    )
    start = time.monotonic()
    for epoch in range(1, args.epochs + 1):
        epoch_start = time.monotonic()
        model.train()
        configure_encoder_training(
            model, args.freeze_encoder, args.freeze_batchnorm_statistics
        )
        sampler = WeightedRandomSampler(
            weights,
            len(rows),
            replacement=True,
            generator=torch.Generator().manual_seed(args.seed + epoch),
        )
        loader = DataLoader(
            dataset,
            sampler=sampler,
            batch_size=args.batch_size,
            num_workers=0,
            collate_fn=original.collate,
            pin_memory=True,
        )
        loss_sum = 0.0
        n = 0
        for audio, targets, lengths, _, _ in loader:
            audio = augment(audio.cuda(non_blocking=True), generator, args.augmentation)
            optimizer.zero_grad(set_to_none=True)
            logits = model(audio)
            losses = criterion(
                logits.log_softmax(-1).transpose(0, 1),
                targets.cuda(),
                torch.full((len(audio),), logits.shape[1], dtype=torch.long),
                lengths,
            )
            loss = (losses / lengths.cuda()).mean()
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite CTC loss")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5, error_if_nonfinite=True)
            optimizer.step()
            loss_sum += float(loss.detach()) * len(audio)
            n += len(audio)
        calibration = original.evaluate(
            model, meta, "calibration", "cuda", decoder=deployment_decoder
        )
        value = score(calibration)
        qualified = False
        if args.deployment_selection:
            value, qualified, improved = deployment_checkpoint_decision(
                calibration,
                best,
                best_qualified,
                deployment_reference["calibration"],
                anchor_calibration,
            )
        else:
            improved = value < best - 0.0001
        stale = 0 if improved else stale + 1
        if improved:
            best = value
            best_qualified = qualified
        if stale and stale % 4 == 0:
            for group in optimizer.param_groups:
                group["lr"] *= 0.5
        record = {
            "epoch": epoch,
            "loss": loss_sum / n,
            "seconds": round(time.monotonic() - epoch_start, 2),
            "calibration": calibration,
            "selection_score": value,
            "qualified": qualified if args.deployment_selection else None,
            "learning_rates": [g["lr"] for g in optimizer.param_groups],
        }
        history.append(record)
        original.write(output / "history.json", history)
        original.save(output / "last.pt", checkpoint(epoch))
        if improved:
            original.save(output / "best.pt", checkpoint(epoch))
        print(json.dumps(record), flush=True)
        if stale >= args.patience or time.monotonic() - start > args.max_minutes * 60:
            break
    selected = torch.load(output / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(selected["model"])
    result = {
        "selected_epoch": selected["epoch"],
        "calibration": original.evaluate(
            model, meta, "calibration", "cuda", decoder=deployment_decoder
        ),
        "initial_calibration": baseline,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "seconds": time.monotonic() - start,
        "evaluation_accessed": False,
        "checkpoint_sha256": original.sha(output / "best.pt"),
        "approved_for_child_scoring": False,
        "gradient_epochs": len(history),
        "formation_method": config["formation_method"],
    }
    if args.deployment_selection:
        result["decoder"] = deployment_decoder
        result["selected_checkpoint_qualified"] = selected["best_qualified"]
    original.write(output / "training-results.json", result)
    print(json.dumps(result), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-root",
        type=Path,
        default=Path("D:/VaakMitraData/artifacts/phoneme-ta19-v2-early"),
    )
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("D:/VaakMitraData/artifacts/phoneme-ta19-v2-early/best.pt"),
    )
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument(
        "--epochs", type=int, default=30, help="0 forms a calibration-only candidate"
    )
    parser.add_argument("--patience", type=int, default=12)
    parser.add_argument("--max-minutes", type=float, default=40)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--target-fraction", type=float, default=0.5)
    parser.add_argument("--encoder-lr", type=float, default=0.00002)
    parser.add_argument("--freeze-encoder", action="store_true")
    parser.add_argument("--freeze-batchnorm-statistics", action="store_true")
    parser.add_argument("--recurrent-dropout", type=float, default=0.1)
    parser.add_argument("--blank-bias-offset", type=float, default=0.0)
    parser.add_argument("--deployment-selection", action="store_true")
    parser.add_argument("--head-lr", type=float, default=0.0002)
    parser.add_argument("--weight-decay", type=float, default=0.0001)
    parser.add_argument(
        "--augmentation",
        choices=["none", "basic", "channel", "rate", "tempo"],
        default="none",
    )
    parser.add_argument("--minimum-quality", type=float, default=0.0)
    parser.add_argument("--minimum-extra-quality", type=float, default=0.0)
    parser.add_argument("--allow-expanded-data", action="store_true")
    parser.add_argument("--frame-shift-ms", type=int, choices=[20, 40])
    args = parser.parse_args()
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        run(args)
    finally:
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
