"""Local CUDA transfer training, held-out robustness WAVs and Android ONNX bundle."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import io
import json
import os
import re
import sys
import time
import zipfile
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import soundfile as sf
import torch
from torch import nn
from torch.utils.data import DataLoader, Dataset

BACKEND = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND))
import itertools

from app.vaakmitra_word.phoneme_ctc import (
    SAMPLES,
    MobilePhonemeCtc,
    checkpoint_frame_shift,
    choose_quantization,
    ctc_decode,
    model_from_checkpoint,
    prepare_waveform,
    stress_waveform,
    validate_splits,
)
from app.vaakmitra_word.phoneme_decoder import decode_logits, validate_decoder
from scripts.model.phoneme_checkpoint_dependencies import validate_ensemble_dependencies

ROOT = Path("D:/VaakMitraData")
OUT = ROOT / "artifacts/phoneme-ta19-v1"
SOURCE = ROOT / "manifests/openslr127-word-v1-reviewed.jsonl"
AUDIO = ROOT / "prepared/openslr127-word-v1"
BASE = ROOT / "artifacts/mobile-student-ta19-v1/training/mobile_word_student.pt"
ZIP = Path("D:/VaakMitra/modeling/artifacts/colab/vaakmitra-colab-private-metadata.zip")
APP = BACKEND.parent / "SpeakEasyAndroid/app/src/main"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for b in iter(lambda: f.read(1024 * 1024), b""):
            h.update(b)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
    tmp.replace(path)


def save(path, value):
    tmp = Path(str(path) + ".tmp")
    torch.save(value, tmp)
    tmp.replace(path)


def load_run(root=None, source=SOURCE, base=BASE):
    root = OUT if root is None else Path(root)
    frozen = json.loads((root / "input-binding.json").read_text())
    if frozen["dataset_sha256"] != sha(root / "dataset.json"):
        raise ValueError("prepared dataset rows changed")
    meta = json.loads((root / "dataset.json").read_text(encoding="utf8"))
    validate_splits(meta["rows"])
    vocab = json.loads((root / "vocabulary.json").read_text(encoding="utf8"))
    binding = meta["binding"]
    if (
        "expansion_sha256" in binding
        and sha(root / "expansion-manifest.json") != binding["expansion_sha256"]
    ):
        raise ValueError("expansion manifest changed")
    if sha(source) != binding["source_sha256"] or sha(base) != binding["base_sha256"]:
        raise ValueError("source or base checkpoint changed")
    digest = hashlib.sha256(
        json.dumps(vocab, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()
    if digest != binding["vocabulary_sha256"]:
        raise ValueError("vocabulary changed")
    marker = json.loads((root / "cache-complete.json").read_text())
    audio = np.load(root / "audio.npy", mmap_mode="r")
    if marker["binding_sha256"] != binding["binding_sha256"] or list(audio.shape) != [
        len(meta["rows"]),
        SAMPLES,
    ]:
        raise ValueError("cache binding or shape changed")
    if (
        marker.get("audio_sha256") != sha(root / "audio.npy")
        or audio.dtype != np.float32
    ):
        raise ValueError("cache digest or dtype changed")
    return meta, vocab


def prepare():
    OUT.mkdir(parents=True, exist_ok=True)
    z = zipfile.ZipFile(ZIP)
    lex = {
        e["word"]: e["units"] for e in json.load(z.open("full-lexicon.json"))["entries"]
    }
    tokens = json.load(z.open("tamil-phoneme-candidate.json"))["tokens"]
    lookup = {t: i for i, t in enumerate(tokens)}
    app_words = re.findall(
        r'StarterWord\("(TA_WORD_[0-9]+)",\s*"([^"]+)"',
        (APP / "java/com/team96/speakeasy/journey/ReviewJourney.kt").read_text(
            encoding="utf8"
        ),
    )
    target_ids = {i for i, _ in app_words}
    source_rows = [json.loads(l) for l in SOURCE.open(encoding="utf8")]
    # Remove all cross-split exact-audio duplicates, never reassign a test example.
    split_hashes = defaultdict(set)
    for r in source_rows:
        split_hashes[r["audio_sha256"]].add(r["split"])
    rows, excluded = [], Counter()
    for r in source_rows:
        if len(split_hashes[r["audio_sha256"]]) != 1:
            excluded["cross_split_audio"] += 1
            continue
        units = lex.get(r["transcript"])
        if not units or any(t not in lookup for t in units):
            excluded["missing_phone"] += 1
            continue
        if r["duration_seconds"] > 3:
            excluded["too_long"] += 1
            continue
        targets = [lookup[t] for t in units]
        needed = len(targets) + sum(a == b for a, b in itertools.pairwise(targets))
        if needed > 75:
            excluded["ctc_incompatible"] += 1
            continue
        rows.append(
            {
                "audio_path": r["audio_path"],
                "audio_sha256": r["audio_sha256"],
                "speaker": r["speaker_pseudonym"],
                "split": r["split"],
                "targets": targets,
                "word_id": r["canonical_word_id"],
                "is_target": r["canonical_word_id"] in target_ids,
            }
        )
    validate_splits(rows)
    vocab = {
        "tokens": tokens,
        "blank_index": 0,
        "sample_rate": 16000,
        "input_samples": SAMPLES,
        "frame_shift_ms": 40,
        "expected": {i: lex[w] for i, w in app_words},
        "expert_approved": False,
        "approved_for_child_scoring": False,
        "label_source": "frozen_epitran_candidate",
        "source_zip_sha256": sha(ZIP),
    }
    binding = {
        "source_sha256": sha(SOURCE),
        "base_sha256": sha(BASE),
        "vocabulary_sha256": hashlib.sha256(
            json.dumps(vocab, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest(),
        "row_count": len(rows),
        "excluded": dict(excluded),
    }
    binding["binding_sha256"] = hashlib.sha256(
        json.dumps(binding, sort_keys=True).encode()
    ).hexdigest()
    if (OUT / "dataset.json").exists():
        old = json.loads((OUT / "dataset.json").read_text())
        if old["binding"] != binding:
            raise ValueError(
                "existing run binding differs; use a new artifact directory"
            )
        if (OUT / "audio.npy").exists() and (OUT / "cache-complete.json").exists():
            load_run()
            print(
                json.dumps({"dataset": "reused", "counts": old["counts"]}), flush=True
            )
            return
    write(OUT / "vocabulary.json", vocab)
    counts = {
        s: sum(r["split"] == s for r in rows)
        for s in ("train", "calibration", "evaluation")
    }
    write(OUT / "dataset.json", {"binding": binding, "counts": counts, "rows": rows})
    array = np.lib.format.open_memmap(
        OUT / "audio.npy", mode="w+", dtype="float32", shape=(len(rows), SAMPLES)
    )
    for i, r in enumerate(rows):
        path = (AUDIO / r["audio_path"]).resolve()
        if not path.is_relative_to(AUDIO.resolve()):
            raise ValueError("audio path escapes root")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != r["audio_sha256"]:
            raise ValueError("audio digest mismatch")
        wav, sr = sf.read(io.BytesIO(raw), dtype="float32")
        if sr != 16000:
            raise ValueError("sample rate mismatch")
        array[i] = prepare_waveform(wav)
        if i % 1000 == 0:
            print(json.dumps({"cache": i, "total": len(rows)}), flush=True)
    array.flush()
    del array
    write(
        OUT / "cache-complete.json",
        {
            "binding_sha256": binding["binding_sha256"],
            "shape": [len(rows), SAMPLES],
            "audio_sha256": sha(OUT / "audio.npy"),
        },
    )
    write(OUT / "input-binding.json", {"dataset_sha256": sha(OUT / "dataset.json")})
    print(
        json.dumps({"prepared": counts, "targets": sum(r["is_target"] for r in rows)}),
        flush=True,
    )


class Clips(Dataset):
    def __init__(self, meta, split):
        self.rows = meta["rows"]
        self.indices = [i for i, r in enumerate(self.rows) if r["split"] == split]
        self.audio = np.load(OUT / "audio.npy", mmap_mode="r")

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, i):
        j = self.indices[i]
        r = self.rows[j]
        return (
            torch.from_numpy(self.audio[j].copy()),
            torch.tensor(r["targets"]),
            r["is_target"],
            j,
        )


def collate(batch):
    audio, targets, focus, indices = zip(*batch)
    return (
        torch.stack(audio),
        nn.utils.rnn.pad_sequence(targets, batch_first=True),
        torch.tensor([len(t) for t in targets]),
        torch.tensor(focus),
        indices,
    )


def loader(meta, split, batch=64, epoch=0):
    return DataLoader(
        Clips(meta, split),
        batch_size=batch,
        shuffle=split == "train",
        num_workers=0,
        pin_memory=torch.cuda.is_available(),
        collate_fn=collate,
        generator=torch.Generator().manual_seed(300 + epoch),
    )


def distance(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j - 1] + (x != y)))
        row = new
    return row[-1]


def metrics(predictions, rows):
    def group(pairs):
        n = len(pairs)
        phones = sum(len(r["targets"]) for p, r in pairs)
        return {
            "records": n,
            "phoneme_error_rate": sum(distance(r["targets"], p) for p, r in pairs)
            / max(1, phones),
            "exact_sequence_accuracy": sum(p == r["targets"] for p, r in pairs)
            / max(1, n),
            "empty_prediction_rate": sum(not p for p, r in pairs) / max(1, n),
        }

    pairs = list(zip(predictions, rows))
    return {
        "all": group(pairs),
        "target19": group([(p, r) for p, r in pairs if r["is_target"]]),
    }


@torch.no_grad()
def evaluate(model, meta, split, device, decoder=None):
    model.eval()
    predictions = []
    rows = []
    for audio, _, _, _, idx in loader(meta, split):
        logits = model(audio.to(device))
        config = (
            {"type": "greedy"}
            if decoder is None
            else validate_decoder(decoder, logits.shape[-1])
        )
        if config["type"] == "greedy":
            paths = logits.argmax(-1).cpu().tolist()
            predictions += [ctc_decode(p) for p in paths]
        else:
            predictions += [decode_logits(x, config) for x in logits.cpu().numpy()]
        rows += [meta["rows"][i] for i in idx]
    return metrics(predictions, rows)


def train(args):
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA required for this authorized GPU run")
    torch.set_num_threads(4)
    torch.manual_seed(17)
    torch.cuda.manual_seed_all(17)
    meta, vocab = load_run()
    model = MobilePhonemeCtc(len(vocab["tokens"]), args.encoder_blocks).cuda()
    initial = torch.load(BASE, map_location="cpu", weights_only=True)
    model.load_encoder(initial["model"])
    with torch.no_grad():
        model.head.bias[0] = -2
    optimizer = torch.optim.AdamW(
        [
            {"params": model.encoder.parameters(), "lr": 0.0001},
            {
                "params": list(model.sequence.parameters())
                + list(model.head.parameters()),
                "lr": 0.002,
            },
        ],
        weight_decay=0.0001,
    )
    start = 1
    best = float("inf")
    stale = 0
    if (OUT / "last.pt").exists():
        resume_file = "best.pt" if args.refine else "last.pt"
        previous = torch.load(OUT / resume_file, map_location="cpu", weights_only=True)
        if previous["binding"] != meta["binding"]:
            raise ValueError("resume binding mismatch")
        if previous.get("encoder_blocks", 7) != args.encoder_blocks:
            raise ValueError("resume encoder architecture mismatch")
        if previous.get("dataset_sha256", sha(OUT / "dataset.json")) != sha(
            OUT / "dataset.json"
        ):
            raise ValueError("checkpoint prepared dataset mismatch")
        model.load_state_dict(previous["model"])
        optimizer.load_state_dict(previous["optimizer"])
        start = previous["epoch"] + 1
        best = previous["best"]
        stale = previous["stale"]
        if "rng" in previous:
            torch.set_rng_state(previous["rng"])
            torch.cuda.set_rng_state_all(previous["cuda_rng"])
    criterion = nn.CTCLoss(blank=0, reduction="none", zero_infinity=False)
    history = (
        json.loads((OUT / "history.json").read_text())
        if (OUT / "history.json").exists()
        else []
    )
    if args.refine:
        start = max(r["epoch"] for r in history) + 1
        stale = 0
        optimizer.param_groups[0]["lr"] = 0.00005
        optimizer.param_groups[1]["lr"] = 0.0005
    write(
        OUT / "active-training-config.json",
        {
            "refine": args.refine,
            "target_weight": args.target_weight,
            "epochs": args.epochs,
            "batch_size": args.batch_size,
            "start_epoch": start,
            "dataset_sha256": sha(OUT / "dataset.json"),
            "encoder_blocks": args.encoder_blocks,
            "learning_rates": [g["lr"] for g in optimizer.param_groups],
        },
    )
    started = time.monotonic()
    print(
        json.dumps(
            {
                "gpu": torch.cuda.get_device_name(),
                "torch": torch.__version__,
                "resume_epoch": start,
                "base_sha256": sha(BASE),
            }
        ),
        flush=True,
    )
    for epoch in range(start, args.epochs + 1):
        model.train()
        epoch_start = time.monotonic()
        frozen = epoch <= 2
        for p in model.encoder.parameters():
            p.requires_grad_(not frozen)
        if frozen:
            model.encoder.eval()
        loss_sum = 0
        n = 0
        for audio, targets, lengths, focus, _ in loader(
            meta, "train", args.batch_size, epoch
        ):
            audio = audio.cuda(non_blocking=True)
            targets = targets.cuda(non_blocking=True)
            # Channel stress preserves every target phoneme and stays on training rows.
            if torch.rand(()) < 0.35:
                rms = (audio.square().mean(1, keepdim=True) + 1e-12).sqrt()
                audio = audio + torch.randn_like(audio) * rms * float(
                    np.random.default_rng(epoch + n).uniform(0.02, 0.1)
                )
            optimizer.zero_grad(set_to_none=True)
            logits = model(audio)
            losses = criterion(
                logits.log_softmax(-1).transpose(0, 1),
                targets,
                torch.full((len(audio),), logits.shape[1], dtype=torch.long),
                lengths,
            ) / lengths.to("cuda")
            weights = 1 + focus.cuda().float() * (args.target_weight - 1)
            loss = (losses * weights).sum() / weights.sum()
            if not torch.isfinite(loss):
                raise FloatingPointError("nonfinite CTC loss")
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 5, error_if_nonfinite=True)
            optimizer.step()
            loss_sum += float(loss.detach()) * len(audio)
            n += len(audio)
        calibration = evaluate(model, meta, "calibration", "cuda")
        score = (
            calibration["target19"]["phoneme_error_rate"] * 0.7
            + calibration["all"]["phoneme_error_rate"] * 0.3
        )
        improved = score < best - 0.0001
        stale = 0 if improved else stale + 1
        if improved:
            best = score
        if stale and stale % 4 == 0:
            for group in optimizer.param_groups:
                group["lr"] = max(group["lr"] * 0.5, 1e-6)
        record = {
            "epoch": epoch,
            "loss": loss_sum / n,
            "seconds": round(time.monotonic() - epoch_start, 2),
            "calibration": calibration,
            "selection_score": score,
            "target_weight": args.target_weight,
            "learning_rates": [g["lr"] for g in optimizer.param_groups],
        }
        history.append(record)
        write(OUT / "history.json", history)
        state = {
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "epoch": epoch,
            "best": best,
            "stale": stale,
            "binding": meta["binding"],
            "rng": torch.get_rng_state(),
            "cuda_rng": torch.cuda.get_rng_state_all(),
            "dataset_sha256": sha(OUT / "dataset.json"),
            "encoder_blocks": args.encoder_blocks,
        }
        save(OUT / "last.pt", state)
        if improved:
            save(OUT / "best.pt", state)
        print(json.dumps(record), flush=True)
        if stale >= 12 or (time.monotonic() - started) > args.max_minutes * 60:
            break
    state = torch.load(OUT / "best.pt", map_location="cpu", weights_only=True)
    model.load_state_dict(state["model"])
    results = {
        "gpu": torch.cuda.get_device_name(),
        "torch": torch.__version__,
        "selected_epoch": state["epoch"],
        "binding": meta["binding"],
        "checkpoint_sha256": sha(OUT / "best.pt"),
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "calibration": evaluate(model, meta, "calibration", "cuda"),
        "evaluation": evaluate(model, meta, "evaluation", "cuda"),
        "approved_for_child_scoring": False,
    }
    write(OUT / "training-results.json", results)
    print(json.dumps(results), flush=True)


def canary(args):
    if not torch.cuda.is_available():
        raise RuntimeError("GPU is not available to this environment")
    torch.set_num_threads(4)
    meta, vocab = load_run()
    model = MobilePhonemeCtc(len(vocab["tokens"]), args.encoder_blocks).cuda()
    model.load_encoder(torch.load(BASE, map_location="cpu", weights_only=True)["model"])
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CTCLoss(blank=0, zero_infinity=False)
    started = time.monotonic()
    losses = []
    for step, (audio, targets, lengths, _, _) in enumerate(
        loader(meta, "train", args.batch_size)
    ):
        optimizer.zero_grad(set_to_none=True)
        logits = model(audio.cuda())
        loss = criterion(
            logits.log_softmax(-1).transpose(0, 1),
            targets.cuda(),
            torch.full((len(audio),), 75, dtype=torch.long),
            lengths,
        )
        if not torch.isfinite(loss):
            raise FloatingPointError("canary loss failed")
        loss.backward()
        nn.utils.clip_grad_norm_(model.parameters(), 5, error_if_nonfinite=True)
        optimizer.step()
        losses.append(float(loss.detach()))
        if step == 9:
            break
    torch.cuda.synchronize()
    result = {
        "gpu": torch.cuda.get_device_name(),
        "torch": torch.__version__,
        "updates": len(losses),
        "losses": losses,
        "seconds": time.monotonic() - started,
        "peak_vram_bytes": torch.cuda.max_memory_allocated(),
        "base_sha256": sha(BASE),
        "cuda_backward_passed": True,
    }
    write(OUT / "gpu-canary.json", result)
    print(json.dumps(result), flush=True)


def read_bound_waveform(row, root=AUDIO):
    root = Path(root).resolve()
    path = (root / row["audio_path"]).resolve()
    if not path.is_relative_to(root) or sha(path) != row["audio_sha256"]:
        raise ValueError("robustness source WAV changed or escaped its root")
    waveform, rate = sf.read(path, dtype="float32")
    if rate != 16000 or waveform.ndim != 1 or not np.isfinite(waveform).all():
        raise ValueError("robustness source PCM contract differs")
    return waveform


def frozen_decoder(root, vocabulary_size):
    """PHN-006 / DEC-035: export the calibration-frozen decoder and checkpoint."""
    root = Path(root)
    path = root / "selection.json"
    report_path = root / "training-results.json"
    report = (
        json.loads(report_path.read_text(encoding="utf8"))
        if report_path.exists()
        else {}
    )
    freeze_path = root / "selection-freeze.json"
    if not path.exists():
        if "decoder" in report or freeze_path.exists():
            raise ValueError("joint decoder selection is missing")
        return {"type": "greedy"}
    selection = json.loads(path.read_text(encoding="utf8"))
    # DEC-040: historical freezes omitted this digest; new ones bind the helper.
    from scripts.model.select_phoneme_improvement import validate_selection_helper

    validate_selection_helper(root, selection)
    joint = "decoder" in report or "decoder" in selection or freeze_path.exists()
    if joint and "decoder" not in selection:
        raise ValueError("joint selection lost its decoder")
    config = validate_decoder(
        selection.get("decoder", {"type": "greedy"}), vocabulary_size
    )
    checkpoint_sha = sha(root / "best.pt")
    if selection["checkpoint_sha256"] != checkpoint_sha:
        raise ValueError("frozen decoder checkpoint changed")
    if joint:
        winner = selection.get("experiments", {}).get(selection.get("winner"), {})
        if (
            report.get("decoder") != config
            or winner.get("decoder") != config
            or report.get("checkpoint_sha256") != checkpoint_sha
            or winner.get("checkpoint_sha256") != checkpoint_sha
            or report.get("calibration") != winner.get("calibration")
        ):
            raise ValueError("decoder differs from the winning experiment or report")
        if freeze_path.exists():
            freeze = json.loads(freeze_path.read_text(encoding="utf8"))
            if (
                freeze.get("selection_sha256") != sha(path)
                or freeze.get("checkpoint_sha256") != checkpoint_sha
            ):
                raise ValueError("independent selection freeze changed")
    if (joint or config["type"] != "greedy") and (
        selection.get("evaluation_accessed") is not False
        or selection.get("selection_split") != "calibration"
        or selection.get("decoder_source_sha256")
        != sha(BACKEND / "app/vaakmitra_word/phoneme_decoder.py")
    ):
        raise ValueError("decoder source or calibration freeze changed")
    return config


def export_and_robustness(args):
    import onnxruntime as ort
    from onnxruntime.quantization import QuantType, quantize_dynamic

    torch.set_num_threads(4)
    meta, vocab = load_run()
    decoder = frozen_decoder(OUT, len(vocab["tokens"]))
    state = torch.load(OUT / "best.pt", map_location="cpu", weights_only=True)
    if state["binding"] != meta["binding"]:
        raise ValueError("export checkpoint binding mismatch")
    if state.get("dataset_sha256", sha(OUT / "dataset.json")) != sha(
        OUT / "dataset.json"
    ):
        raise ValueError("export prepared dataset mismatch")
    frame_shift = checkpoint_frame_shift(state)
    validate_ensemble_dependencies(OUT / "best.pt", state)
    (OUT / "export-entrypoint.py").write_bytes(Path(__file__).read_bytes())
    model = model_from_checkpoint(state, len(vocab["tokens"]))
    model.eval()
    bundle = OUT / "bundle"
    bundle.mkdir(exist_ok=True)
    fp = bundle / "phoneme.fp32.onnx"
    qp = bundle / "phoneme.int8.onnx"
    torch.onnx.export(
        model,
        (torch.zeros(1, SAMPLES),),
        str(fp),
        input_names=["waveform"],
        output_names=["logits"],
        opset_version=17,
        dynamic_axes={"waveform": {0: "batch"}, "logits": {0: "batch"}},
        dynamo=False,
    )
    quantize_dynamic(
        str(fp),
        str(qp),
        weight_type=QuantType.QInt8,
        op_types_to_quantize=["MatMul", "Gemm", "GRU"],
    )
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    sessions = {
        k: ort.InferenceSession(
            str(p), sess_options=options, providers=["CPUExecutionProvider"]
        )
        for k, p in [("fp32", fp), ("int8", qp)]
    }
    audio = np.load(OUT / "audio.npy", mmap_mode="r")
    eval_indices = [i for i, r in enumerate(meta["rows"]) if r["split"] == "evaluation"]
    predictions = {k: [] for k in sessions}
    max_delta = 0.0
    disagreements = Counter()
    pytorch_disagreements = 0
    for offset in range(0, len(eval_indices), 32):
        inds = eval_indices[offset : offset + 32]
        values = np.array(audio[inds])
        raw = {k: s.run(None, {"waveform": values})[0] for k, s in sessions.items()}
        with torch.no_grad():
            native = model(torch.from_numpy(values)).numpy()
        for j in range(len(inds)):
            paths = {k: decode_logits(v[j], decoder) for k, v in raw.items()}
            for k, p in paths.items():
                predictions[k].append(p)
            pytorch_disagreements += decode_logits(native[j], decoder) != paths["fp32"]
            disagreements["int8"] += paths["fp32"] != paths["int8"]
        max_delta = max(max_delta, float(np.max(np.abs(raw["fp32"] - native))))
    rows = [meta["rows"][i] for i in eval_indices]
    reports = {k: metrics(p, rows) for k, p in predictions.items()}
    agreement = 1 - disagreements["int8"] / len(eval_indices)
    # Format selection also uses calibration only; held-out evaluation stays descriptive.
    cal_indices = [i for i, r in enumerate(meta["rows"]) if r["split"] == "calibration"]
    cal_predictions = {k: [] for k in sessions}
    for offset in range(0, len(cal_indices), 32):
        values = np.array(audio[cal_indices[offset : offset + 32]])
        for k, s in sessions.items():
            raw = s.run(None, {"waveform": values})[0]
            cal_predictions[k] += [decode_logits(p, decoder) for p in raw]
    cal_rows = [meta["rows"][i] for i in cal_indices]
    cal_metrics = {k: metrics(p, cal_rows) for k, p in cal_predictions.items()}
    cal_agreement = sum(
        a == b for a, b in zip(cal_predictions["fp32"], cal_predictions["int8"])
    ) / len(cal_indices)
    target_cal = [j for j, r in enumerate(cal_rows) if r["is_target"]]
    target_agreement = sum(
        cal_predictions["fp32"][j] == cal_predictions["int8"][j] for j in target_cal
    ) / len(target_cal)
    chosen = choose_quantization(
        cal_metrics["fp32"]["all"]["phoneme_error_rate"],
        cal_metrics["int8"]["all"]["phoneme_error_rate"],
        cal_agreement,
        cal_metrics["fp32"]["target19"]["phoneme_error_rate"],
        cal_metrics["int8"]["target19"]["phoneme_error_rate"],
        target_agreement,
    )
    if pytorch_disagreements or max_delta > 0.005:
        raise ValueError("FP32 ONNX parity failed")
    session = sessions[chosen]
    robust = {}
    generated = OUT / "robustness-audio"
    generated.mkdir(exist_ok=True)
    targets = [i for i in eval_indices if meta["rows"][i]["is_target"]]
    for kind in ["noise20", "noise10", "echo", "lowpass", "quiet"]:
        preds = []
        stress_rows = []
        for i in targets:
            r = meta["rows"][i]
            x = read_bound_waveform(r)
            wav = stress_waveform(x, kind, i + 1700)
            sf.write(generated / f"{i:05d}-{kind}.wav", wav, 16000, subtype="PCM_16")
            # Test the actual serialized WAV that is delivered, not a different float signal.
            wav, _ = sf.read(generated / f"{i:05d}-{kind}.wav", dtype="float32")
            preds.append(
                decode_logits(
                    session.run(None, {"waveform": prepare_waveform(wav)[None]})[0][0],
                    decoder,
                )
            )
            stress_rows.append(r)
        robust[kind] = metrics(preds, stress_rows)
    write(
        OUT / "robustness-results.json",
        {
            "variants": robust,
            "source_split": "evaluation",
            "generated_wavs": len(targets) * 5,
            "child_speech_simulated": False,
            "transformations_preserve_duration": True,
        },
    )
    write(
        generated / "parent-manifest.json",
        {
            "source_dataset_sha256": sha(OUT / "dataset.json"),
            "rows": [
                {
                    "file": f"{i:05d}-{kind}.wav",
                    "parent_audio_sha256": meta["rows"][i]["audio_sha256"],
                    "split": "evaluation",
                    "kind": kind,
                }
                for i in targets
                for kind in ["noise20", "noise10", "echo", "lowpass", "quiet"]
            ],
        },
    )
    selected = bundle / f"phoneme.{chosen}.onnx"
    export_vocab = dict(vocab, frame_shift_ms=frame_shift)
    write(bundle / "vocabulary.json", export_vocab)
    manifest = {
        "bundle_version": "phoneme-ta19-v2"
        if decoder["type"] != "greedy"
        else "phoneme-ta19-v1",
        "artifact_revision": OUT.name,
        "decoder": decoder,
        "model_file": selected.name,
        "model_sha256": sha(selected),
        "vocabulary_sha256": sha(bundle / "vocabulary.json"),
        "input_samples": SAMPLES,
        "output_frames": SAMPLES // (16 * frame_shift),
        "frame_shift_ms": frame_shift,
        "training_vocabulary_sha256": meta["binding"]["vocabulary_sha256"],
        "tokens": len(vocab["tokens"]),
        "approved_for_child_scoring": False,
        "production_ready": False,
        "base_sha256": sha(BASE),
        "checkpoint_sha256": sha(OUT / "best.pt"),
        "export_entrypoint_sha256": sha(OUT / "export-entrypoint.py"),
        "decoder_source_sha256": sha(BACKEND / "app/vaakmitra_word/phoneme_decoder.py"),
        "dataset_sha256": sha(OUT / "dataset.json"),
        "encoder_blocks": state.get("encoder_blocks", 7),
        "input_name": "waveform",
        "output_name": "logits",
    }
    if state.get("model_kind") == "posterior_mean_2":
        manifest.update(
            model_kind="posterior_mean_2",
            ensemble_members=2,
            model_parameters=sum(parameter.numel() for parameter in model.parameters()),
            architecture_source_sha256=state["architecture_source_sha256"],
        )
    write(bundle / "bundle.json", manifest)
    write(
        OUT / "export-results.json",
        {
            "chosen": chosen,
            "metrics": reports,
            "sequence_agreement": agreement,
            "pytorch_onnx_sequence_disagreements": pytorch_disagreements,
            "max_logit_delta": max_delta,
            "selection_split": "calibration",
            "calibration_metrics": cal_metrics,
            "calibration_sequence_agreement": cal_agreement,
            "calibration_target_sequence_agreement": target_agreement,
            "file_bytes": {
                k: p.stat().st_size for k, p in [("fp32", fp), ("int8", qp)]
            },
        },
    )
    # Ship a public adult fixture for native Android parity and latency measurement.
    fixtures = OUT / "instrumentation-assets"
    fixtures.mkdir(exist_ok=True)
    i = next(
        i
        for i in targets
        if 0.6 <= sf.info(AUDIO / meta["rows"][i]["audio_path"]).duration <= 1.5
    )
    fixture = read_bound_waveform(meta["rows"][i])
    sf.write(fixtures / "adult-test.wav", fixture, 16000, subtype="PCM_16")
    write(
        fixtures / "adult-test.json",
        {
            "expected_prediction": decode_logits(
                session.run(None, {"waveform": prepare_waveform(fixture)[None]})[0][0],
                decoder,
            ),
            "reference_token_ids": meta["rows"][i]["targets"],
            "word_id": meta["rows"][i]["word_id"],
            "tokens": vocab["tokens"],
            "fixture_sha256": sha(fixtures / "adult-test.wav"),
            "source_audio_sha256": meta["rows"][i]["audio_sha256"],
        },
    )
    (fixtures / "ATTRIBUTION.txt").write_text(
        "IISc MILE Tamil ASR Corpus / OpenSLR 127. Source: https://www.openslr.org/127/\nLicense: Creative Commons Attribution 2.0 https://creativecommons.org/licenses/by/2.0/\nThis fixture is a segmented adult recording, converted to PCM16; synthetic variants are separately labelled.\n",
        encoding="utf8",
    )
    variants = []
    for kind in ["noise20", "noise10", "echo", "lowpass", "quiet"]:
        name = f"{kind}.wav"
        sf.write(
            fixtures / name,
            stress_waveform(fixture, kind, 1700),
            16000,
            subtype="PCM_16",
        )
        variants.append({"kind": kind, "file": name, "sha256": sha(fixtures / name)})
    write(fixtures / "variants.json", variants)
    attribution = (fixtures / "ATTRIBUTION.txt").read_text(encoding="utf8")
    (generated / "ATTRIBUTION.txt").write_text(attribution, encoding="utf8")
    (bundle / "MODEL_CARD.txt").write_text(
        "Provisional adult Tamil phoneme CTC transfer model. Audio-derived tokens; no child correctness approval.\nTraining data attribution:\n"
        + attribution,
        encoding="utf8",
    )
    print(
        json.dumps(
            {
                "bundle": str(bundle),
                "chosen": chosen,
                "evaluation": reports[chosen],
                "robustness": robust,
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=["prepare", "canary", "train", "export"])
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--max-minutes", type=float, default=120)
    parser.add_argument("--refine", action="store_true")
    parser.add_argument("--target-weight", type=float, default=3)
    parser.add_argument("--encoder-blocks", type=int, choices=[5, 7], default=7)
    parser.add_argument("--output-root", type=Path, default=OUT)
    args = parser.parse_args()
    OUT = args.output_root.resolve()
    if os.name == "nt":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:
        {
            "prepare": lambda: prepare(),
            "canary": lambda: canary(args),
            "train": lambda: train(args),
            "export": lambda: export_and_robustness(args),
        }[args.phase]()
    finally:
        if os.name == "nt":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
