"""DEC-032/PHN-002: mine existing Tamil sentences without moving speakers."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import shutil
import subprocess
import time
import unicodedata
import wave
import zipfile
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

DATA = Path(os.environ.get("VAAKMITRA_DATA_ROOT", "D:/VaakMitraData"))
REFERENCE = Path(os.environ.get("VAAKMITRA_REFERENCE_ROOT", "D:/VaakMitra"))
CORPUS = REFERENCE / "modeling/artifacts/corpora/openslr-127/extracted"
ARCHIVE = REFERENCE / "modeling/artifacts/colab/vaakmitra-colab-private-metadata.zip"
ANALYSIS = DATA / "analysis/phoneme-round2-20261111"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf8")
    tmp.replace(path)


def speaker_key(record):
    # Match the conservative numeric grouping used by all existing student splits.
    numeric = record["speaker_id"].rsplit("_", 1)[-1]
    if not numeric.isdigit():
        raise ValueError("invalid source speaker identity")
    return f"openslr127:{numeric}"


def assign_split(record, existing):
    key = speaker_key(record)
    if key in existing:
        return existing[key]
    bucket = int(hashlib.sha256(key.encode()).hexdigest()[:8], 16) % 10
    return "calibration" if bucket == 0 else "evaluation" if bucket == 1 else "train"


def index_candidates(args):
    base = DATA / "artifacts/phoneme-ta19-v3-improved"
    meta = json.loads((base / "dataset.json").read_text(encoding="utf8"))
    vocab = json.loads((base / "vocabulary.json").read_text(encoding="utf8"))
    existing = {r["speaker"]: r["split"] for r in meta["rows"]}
    used = {Path(r["audio_path"]).parent.name for r in meta["rows"]}
    catalog = (
        Path(__file__).resolve().parents[2] / "data/vocabulary/ta-v1-intended.json"
    )
    entries = json.loads(catalog.read_text(encoding="utf8"))["entries"]
    targets = {
        e["canonical_tamil"]: e["word_id"]
        for e in entries
        if e["word_id"] in vocab["expected"]
    }
    cached = {
        r["original_id"]: r["transcript"]
        for r in map(
            json.loads,
            (DATA / "manifests/openslr127-partial-metadata.jsonl").open(
                encoding="utf8"
            ),
        )
    }
    with zipfile.ZipFile(ARCHIVE) as archive:
        records = [json.loads(line) for line in archive.open("records.jsonl")]

    def inspect(record):
        if record["utterance_id"] in used or not 1000 <= record["duration_ms"] <= 20000:
            return None
        text = cached.get(record["utterance_id"])
        verified = False
        if text is None:
            path = (CORPUS / record["transcript_rel_path"]).resolve()
            if not path.is_relative_to(CORPUS.resolve()):
                raise ValueError("transcript escapes reference root")
            raw = path.read_bytes()
            if hashlib.sha256(raw).hexdigest() != record["transcript_sha256"]:
                raise ValueError("source transcript hash mismatch")
            text = raw.decode("utf8")
            verified = True
        text = unicodedata.normalize("NFC", text).strip()
        words = [word.strip('.,!?;:"()[]“”‘’') for word in text.split()]
        focus = sorted({targets[w] for w in words if w in targets})
        if not focus:
            return None
        role = assign_split(record, existing)
        return {
            "record": record,
            "transcript": text,
            "speaker": speaker_key(record),
            "split": role,
            "target_word_ids": focus,
            "new_to_student_speaker": speaker_key(record) not in existing,
            "transcript_hash_verified": verified,
        }

    candidates = []
    with ThreadPoolExecutor(max_workers=12) as executor:
        for i, item in enumerate(executor.map(inspect, records), 1):
            if item:
                candidates.append(item)
            if i % 5000 == 0:
                print(
                    json.dumps(
                        {
                            "stage": "transcript_index",
                            "scanned": i,
                            "records": len(records),
                            "candidate_sentences": len(candidates),
                        }
                    ),
                    flush=True,
                )
    counts = Counter()
    speaker_counts = Counter()
    selected = []
    audits = 0
    for row in sorted(
        candidates,
        key=lambda r: hashlib.sha256(r["record"]["utterance_id"].encode()).hexdigest(),
    ):
        if row["split"] == "train":
            wanted = [
                w
                for w in row["target_word_ids"]
                if counts[w] < args.per_word and speaker_counts[(w, row["speaker"])] < 4
            ]
            if not wanted:
                continue
            row["wanted_word_ids"] = wanted
            counts.update(wanted)
            speaker_counts.update((w, row["speaker"]) for w in wanted)
            selected.append(row)
        elif row["new_to_student_speaker"] and audits < args.audit_limit:
            row["wanted_word_ids"] = row["target_word_ids"]
            selected.append(row)
            audits += 1
    ANALYSIS.mkdir(parents=True, exist_ok=True)
    output = ANALYSIS / "target-candidates.jsonl"
    with output.open("w", encoding="utf8", newline="\n") as f:
        for row in selected:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    report = {
        "source_records": len(records),
        "all_candidate_sentences": len(candidates),
        "selected_sentences": len(selected),
        "selected_splits": dict(Counter(r["split"] for r in selected)),
        "new_train_candidates_by_word": dict(counts),
        "fresh_speaker_audit_sentences": audits,
        "old_parents_excluded": len(used),
        "current_speaker_roles_preserved": True,
        "candidate_manifest_sha256": sha(output),
        "source_metadata_zip_sha256": sha(ARCHIVE),
        "base_dataset_sha256": sha(base / "dataset.json"),
        "catalog_sha256": sha(catalog),
        "note": "Source-only selection; cached transcripts will be hash-checked against original files before alignment.",
    }
    write(ANALYSIS / "target-index-results.json", report)
    print(json.dumps(report), flush=True)


def sample_bounds(start, end, frames, samples, rate, padding=0.06):
    if rate != 16000 or not 0 <= start < end <= frames or samples <= 0:
        raise ValueError("invalid source frame bounds")
    return (
        max(0, math.floor(start * samples / frames) - round(padding * rate)),
        min(samples, math.ceil(end * samples / frames) + round(padding * rate)),
    )


def accept_audio(pcm, rate):
    import numpy as np

    values = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768
    return bool(
        rate == 16000
        and 0.2 <= len(values) / rate <= 3
        and np.isfinite(values).all()
        and np.sqrt(np.mean(values * values)) >= 0.005
        and np.mean(np.abs(values) >= 0.99) <= 0.01
    )


def stored_path(path):
    value = Path(path).as_posix()
    if value.startswith("/mnt/d/"):
        return "D:/" + value[len("/mnt/d/") :]
    return value


def duration_batches(rows, max_items, max_padded_seconds):
    if max_items < 1 or max_padded_seconds <= 0:
        raise ValueError("invalid batch resource limits")
    batch = []
    longest = 0
    for row in rows:
        duration = row["record"]["duration_ms"] / 1000
        if batch and (
            len(batch) >= max_items
            or max(longest, duration) * (len(batch) + 1) > max_padded_seconds
        ):
            yield batch
            batch = []
            longest = 0
        batch.append(row)
        longest = max(longest, duration)
    if batch:
        yield batch


def segment_candidates(args):
    os.environ["WANDB_MODE"] = "disabled"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["HF_DATASETS_OFFLINE"] = "1"
    for variable, leaf in [
        ("TMPDIR", "tmp"),
        ("CUDA_CACHE_PATH", "cuda-cache"),
        ("NUMBA_CACHE_DIR", "numba-cache"),
    ]:
        directory = Path("/opt/vaakmitra-r2") / leaf
        directory.mkdir(parents=True, exist_ok=True)
        os.environ[variable] = str(directory)
    import inspect

    import torch
    import torchaudio
    from nemo.collections.asr.models import ASRModel
    from target_alignment import TokenSpan, group_sentencepiece_words

    candidates_file = ANALYSIS / "target-candidates.jsonl"
    index = json.loads(
        (ANALYSIS / "target-index-results.json").read_text(encoding="utf8")
    )
    if sha(candidates_file) != index["candidate_manifest_sha256"]:
        raise ValueError("candidate index changed")
    output = args.output_root or DATA / "artifacts/phoneme-ta19-extra-r2-v1"
    model_path = (
        args.teacher_model
        or DATA.parent
        / "VaakMitraModels/ta-word-v1/upstream/indicconformer_stt_ta_hybrid_rnnt_large.nemo"
    )
    model_sha = sha(model_path)
    if model_sha != "40a6fce3374ceb67daa2a071e92f0948c51c6a95b734d4881a3bcfe0b1bed32a":
        raise ValueError("teacher weights changed")
    binding = {
        "candidate_sha256": sha(candidates_file),
        "teacher_sha256": model_sha,
        "minimum_alignment_score": args.minimum_score,
        "padding_seconds": 0.06,
        "base_dataset_sha256": index["base_dataset_sha256"],
        "policy": "extra-target-v1",
    }
    if output.exists():
        if not args.resume or not (output / "segmentation-binding.json").is_file():
            raise FileExistsError(
                "fresh segment output or explicit bound resume required"
            )
        if (
            json.loads(
                (output / "segmentation-binding.json").read_text(encoding="utf8")
            )
            != binding
        ):
            raise ValueError("segmentation resume inputs differ")
    else:
        output.mkdir(parents=True)
        write(output / "segmentation-binding.json", binding)
    catalog = (
        Path(__file__).resolve().parents[2] / "data/vocabulary/ta-v1-intended.json"
    )
    if sha(catalog) != index["catalog_sha256"]:
        raise ValueError("target catalog changed")
    entries = json.loads(catalog.read_text(encoding="utf8"))["entries"]
    target_ids = json.loads(
        (DATA / "artifacts/phoneme-ta19-v3-improved/vocabulary.json").read_text(
            encoding="utf8"
        )
    )["expected"]
    targets = {
        e["canonical_tamil"]: e["word_id"]
        for e in entries
        if e["word_id"] in target_ids
    }
    pool = [json.loads(line) for line in candidates_file.open(encoding="utf8")]
    completed_file = output / "completed-utterances.jsonl"
    records_file = output / "segments-incremental.jsonl"
    done = (
        {
            r["utterance_id"]
            for r in map(json.loads, completed_file.open(encoding="utf8"))
        }
        if completed_file.exists()
        else set()
    )
    accepted = (
        [json.loads(line) for line in records_file.open(encoding="utf8")]
        if records_file.exists()
        else []
    )
    baseline = json.loads(
        (DATA / "artifacts/phoneme-ta19-v3-improved/dataset.json").read_text(
            encoding="utf8"
        )
    )
    hashes = {r["audio_sha256"] for r in baseline["rows"]}
    for row in accepted:
        local = (
            Path(row["audio_path"].replace("D:/", "/mnt/d/"))
            if os.name != "nt"
            else Path(row["audio_path"])
        )
        if sha(local) != row["audio_sha256"]:
            raise ValueError("accepted segment changed during resume")
        hashes.add(row["audio_sha256"])
    pending = sorted(
        (r for r in pool if r["record"]["utterance_id"] not in done),
        key=lambda r: (
            r["split"] != "train",
            r["record"]["duration_ms"],
            r["record"]["utterance_id"],
        ),
    )
    if args.limit:
        pending = pending[: args.limit]
    torch.set_num_threads(2)
    started = time.monotonic()
    model = ASRModel.restore_from(str(model_path), map_location="cuda")
    model.eval()
    model.cur_decoder = "ctc"
    print(
        json.dumps(
            {
                "stage": "teacher_restored",
                "seconds": time.monotonic() - started,
                "pending": len(pending),
            }
        ),
        flush=True,
    )
    rejected = Counter()
    if (output / "segmentation-results.json").exists():
        rejected.update(
            json.loads((output / "segmentation-results.json").read_text())["rejected"]
        )

    def summary():
        report = {
            "completed_utterances": len(done),
            "accepted_records": len(accepted),
            "splits": dict(Counter(r["split"] for r in accepted)),
            "train_by_word": dict(
                Counter(r["word_id"] for r in accepted if r["split"] == "train")
            ),
            "rejected": dict(rejected),
            "seconds_this_run": time.monotonic() - started,
            "peak_cuda_bytes": torch.cuda.max_memory_allocated(),
            "human_reviewed": False,
            "teacher_sha256": model_sha,
            "candidate_sha256": binding["candidate_sha256"],
        }
        write(output / "segmentation-results.json", report)
        return report

    for batch in duration_batches(pending, args.batch_size, args.max_padded_seconds):
        paths = []
        for row in batch:
            record = row["record"]
            path = (CORPUS / record["audio_rel_path"]).resolve()
            text_path = (CORPUS / record["transcript_rel_path"]).resolve()
            if not path.is_relative_to(
                CORPUS.resolve()
            ) or not text_path.is_relative_to(CORPUS.resolve()):
                raise ValueError("source outside read-only corpus")
            if (
                sha(path) != record["audio_sha256"]
                or sha(text_path) != record["transcript_sha256"]
            ):
                raise ValueError("source file hash changed")
            if (
                unicodedata.normalize(
                    "NFC", text_path.read_text(encoding="utf8")
                ).strip()
                != row["transcript"]
            ):
                raise ValueError("cached transcript differs from source")
            paths.append(path)
        kwargs = {
            "batch_size": args.batch_size,
            "language_id": "ta",
            "logprobs": True,
            "verbose": False,
        }
        if "num_workers" in inspect.signature(model.transcribe).parameters:
            kwargs["num_workers"] = 0
        with torch.inference_mode():
            logits_batch = model.transcribe([str(p) for p in paths], **kwargs)
        if len(logits_batch) != len(batch):
            raise ValueError("teacher batch count mismatch")
        for row, path, raw_logits in zip(batch, paths, logits_batch):
            record = row["record"]
            status = "ok"
            new = []
            try:
                if isinstance(raw_logits, (tuple, list)):
                    raw_logits = raw_logits[0]
                logits = torch.as_tensor(raw_logits).float()
                ids = model.tokenizer.text_to_ids(row["transcript"], "ta")
                if not ids or max(ids) >= logits.shape[-1] - 1:
                    raise ValueError("invalid target tokens")
                aligned, scores = torchaudio.functional.forced_align(
                    logits[None],
                    torch.tensor([ids], dtype=torch.int32, device=logits.device),
                    blank=logits.shape[-1] - 1,
                )
                spans = torchaudio.functional.merge_tokens(
                    aligned[0], scores[0], blank=logits.shape[-1] - 1
                )
                words = group_sentencepiece_words(
                    tokens=tuple(model.tokenizer.ids_to_tokens(ids, "ta")),
                    spans=tuple(
                        TokenSpan(int(s.start), int(s.end), math.exp(float(s.score)))
                        for s in spans
                    ),
                )
                with wave.open(str(path), "rb") as wav:
                    if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) != (
                        1,
                        2,
                        16000,
                    ):
                        raise ValueError("source PCM contract")
                    source_frames = wav.getnframes()
                    chosen = set()
                    for word in sorted(words, key=lambda w: w.score, reverse=True):
                        word_id = targets.get(word.text)
                        if word_id not in row["wanted_word_ids"] or word_id in chosen:
                            continue
                        if word.score < args.minimum_score:
                            rejected["alignment_score"] += 1
                            continue
                        start, end = sample_bounds(
                            word.start, word.end, len(logits), source_frames, 16000
                        )
                        wav.setpos(start)
                        pcm = wav.readframes(end - start)
                        if not accept_audio(pcm, 16000):
                            rejected["audio_qa"] += 1
                            continue
                        payload = io.BytesIO()
                        with wave.open(payload, "wb") as segment:
                            segment.setnchannels(1)
                            segment.setsampwidth(2)
                            segment.setframerate(16000)
                            segment.writeframes(pcm)
                        raw = payload.getvalue()
                        digest = hashlib.sha256(raw).hexdigest()
                        if digest in hashes:
                            rejected["duplicate_audio"] += 1
                            continue
                        dest = (
                            output
                            / "audio"
                            / row["split"]
                            / record["utterance_id"]
                            / f"{word_id}.wav"
                        )
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        if dest.exists():
                            if sha(dest) != digest:
                                raise FileExistsError("existing segment differs")
                        else:
                            tmp = dest.with_suffix(".tmp")
                            tmp.write_bytes(raw)
                            tmp.replace(dest)
                        entry = {
                            "audio_path": stored_path(dest),
                            "audio_sha256": digest,
                            "speaker": row["speaker"],
                            "split": row["split"],
                            "word_id": word_id,
                            "is_target": True,
                            "transcript": word.text,
                            "parent_id": "openslr127:" + record["utterance_id"],
                            "source_utterance_id": "openslr127:"
                            + record["utterance_id"],
                            "source_audio_sha256": record["audio_sha256"],
                            "source_transcript_sha256": record["transcript_sha256"],
                            "duration_seconds": (end - start) / 16000,
                            "quality_score": word.score,
                            "teacher_sha256": model_sha,
                            "licence_id": "CC-BY-2.0",
                            "human_reviewed": False,
                            "new_to_student_speaker": row["new_to_student_speaker"],
                            "alignment_frames": [word.start, word.end, len(logits)],
                        }
                        hashes.add(digest)
                        chosen.add(word_id)
                        new.append(entry)
            except (RuntimeError, ValueError) as exc:
                status = type(exc).__name__ + ":" + str(exc)[:100]
                rejected["alignment:" + type(exc).__name__] += 1
            with records_file.open("a", encoding="utf8") as f:
                for entry in new:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
                    accepted.append(entry)
            with completed_file.open("a", encoding="utf8") as f:
                f.write(
                    json.dumps(
                        {"utterance_id": record["utterance_id"], "status": status}
                    )
                    + "\n"
                )
            done.add(record["utterance_id"])
        report = summary()
        print(
            json.dumps(
                {
                    "stage": "alignment",
                    "completed": len(done),
                    "accepted": len(accepted),
                    "splits": report["splits"],
                }
            ),
            flush=True,
        )
    print(json.dumps(summary()), flush=True)


def verify_original_prefix(source, rebuilt, chunk_size=128):
    import numpy as np

    if source.shape[1:] != rebuilt.shape[1:] or len(rebuilt) < len(source):
        raise ValueError("original prefix shape changed")
    for start in range(0, len(source), chunk_size):
        end = min(start + chunk_size, len(source))
        if not np.array_equal(source[start:end], rebuilt[start:end]):
            raise ValueError("original waveform prefix changed")


def validate_segment_record(row, pool, binding):
    record = pool["record"]
    expected = {
        "parent_id": "openslr127:" + record["utterance_id"],
        "source_utterance_id": "openslr127:" + record["utterance_id"],
        "speaker": pool["speaker"],
        "split": pool["split"],
        "source_audio_sha256": record["audio_sha256"],
        "source_transcript_sha256": record["transcript_sha256"],
        "teacher_sha256": binding["teacher_sha256"],
        "new_to_student_speaker": pool["new_to_student_speaker"],
    }
    if any(row.get(k) != v for k, v in expected.items()):
        raise ValueError("segment differs from frozen source candidate")
    if (
        row["word_id"] not in pool["wanted_word_ids"]
        or row.get("is_target") is not True
    ):
        raise ValueError("segment word is outside frozen target selection")
    quality = row["quality_score"]
    if (
        not math.isfinite(quality)
        or not binding["minimum_alignment_score"] <= quality <= 1
    ):
        raise ValueError("invalid segment alignment score")
    if (
        row.get("human_reviewed") is not False
        or not 0.2 <= row["duration_seconds"] <= 3
    ):
        raise ValueError("invalid segment provenance/duration")


def validate_cache_headroom(available_bytes, row_count):
    # Writable Windows mappings can need the full logical allocation even when
    # NTFS compression later reduces the closed file; leave OS/log headroom too.
    required = row_count * 48000 * 4 + 128 + 1024**3
    if available_bytes < required:
        raise ValueError(
            f"insufficient cache space: need {required} bytes including headroom"
        )


def prepare_dataset(args):
    if os.name != "nt":
        raise RuntimeError("prepare runs in the existing Windows GPU environment")
    import finetune_mobile_phoneme as original
    import numpy as np
    import soundfile as sf
    from app.vaakmitra_word.phoneme_ctc import prepare_waveform
    from prepare_phoneme_expansion import validate_expansion_rows

    output = args.output_root or DATA / "artifacts/phoneme-ta19-extra-r2-v1"
    base = DATA / "artifacts/phoneme-ta19-v3-improved"
    index = json.loads(
        (ANALYSIS / "target-index-results.json").read_text(encoding="utf8")
    )
    summary = json.loads(
        (output / "segmentation-results.json").read_text(encoding="utf8")
    )
    candidates_path = ANALYSIS / "target-candidates.jsonl"
    if sha(candidates_path) != index["candidate_manifest_sha256"]:
        raise ValueError("candidate source manifest changed")
    candidates = {
        r["record"]["utterance_id"]: r
        for r in map(json.loads, candidates_path.open(encoding="utf8"))
    }
    segment_binding = json.loads(
        (output / "segmentation-binding.json").read_text(encoding="utf8")
    )
    if summary["completed_utterances"] != index["selected_sentences"]:
        raise ValueError("finish all candidate alignment before freezing data")
    if (output / "audio.npy").exists() or (output / "audio.npy.tmp").exists():
        raise FileExistsError("prepared or incomplete cache already exists")
    meta, vocab = original.load_run(base)
    if sha(base / "dataset.json") != index["base_dataset_sha256"]:
        raise ValueError("base input metadata changed")
    accepted = [
        json.loads(line)
        for line in (output / "segments-incremental.jsonl").open(encoding="utf8")
    ]
    token_ids = {t: i for i, t in enumerate(vocab["tokens"])}
    for row in accepted:
        parent_id = row["parent_id"].removeprefix("openslr127:")
        validate_segment_record(row, candidates[parent_id], segment_binding)
        if (
            not Path(row["audio_path"])
            .resolve()
            .is_relative_to((output / "audio").resolve())
        ):
            raise ValueError("segment WAV outside its artifact root")
        row["targets"] = [token_ids[t] for t in vocab["expected"][row["word_id"]]]
        row["source_id"] = "openslr-127-mile-ta"
        if row["quality_score"] < 0.85 or row["human_reviewed"] is not False:
            raise ValueError("unexpected extra-data provenance")
    training = [r for r in accepted if r["split"] == "train"]
    audit = [r for r in accepted if r["split"] != "train"]
    if not training:
        raise ValueError("no additional accepted training clips")
    rows = meta["rows"] + training
    validate_expansion_rows(meta["rows"], rows, audit)
    validate_cache_headroom(shutil.disk_usage(output).free, len(rows))
    write(
        output / "expansion-manifest.json",
        {
            "training": training,
            "audit": audit,
            "segmentation_binding": json.loads(
                (output / "segmentation-binding.json").read_text()
            ),
            "candidate_sha256": index["candidate_manifest_sha256"],
            "human_reviewed": False,
            "supervision": "frozen canonical phoneme candidates; machine-aligned source words",
        },
    )
    binding = dict(
        meta["binding"],
        row_count=len(rows),
        expansion_sha256=sha(output / "expansion-manifest.json"),
    )
    binding.pop("binding_sha256", None)
    binding["binding_sha256"] = hashlib.sha256(
        json.dumps(binding, sort_keys=True).encode()
    ).hexdigest()
    combined = {
        "binding": binding,
        "rows": rows,
        "counts": dict(Counter(r["split"] for r in rows)),
        "parent_binding": meta["binding"],
        "parent_dataset_sha256": sha(base / "dataset.json"),
        "parent_input_root": str(base),
    }
    write(output / "dataset.json", combined)
    write(output / "vocabulary.json", vocab)
    write(
        output / "input-binding.json", {"dataset_sha256": sha(output / "dataset.json")}
    )
    # Transparent NTFS compression preserves exact float32 data without another
    # several-GB allocation; only this new artifact directory is changed.
    subprocess.run(
        ["compact.exe", "/C", "/I", "/Q", str(output)], check=True, capture_output=True
    )
    source = np.load(base / "audio.npy", mmap_mode="r")
    temp = output / "audio.npy.tmp"
    cached = np.lib.format.open_memmap(
        temp, mode="w+", dtype="float32", shape=(len(rows), 48000)
    )
    for offset in range(0, len(meta["rows"]), 128):
        values = source[offset : offset + 128]
        cached[offset : offset + len(values)] = values
        if offset % 4096 == 0:
            print(json.dumps({"stage": "copy_original", "copied": offset}), flush=True)
    for j, row in enumerate(training, len(meta["rows"])):
        path = Path(row["audio_path"])
        if sha(path) != row["audio_sha256"]:
            raise ValueError("new training WAV changed")
        wav, rate = sf.read(path, dtype="float32")
        if rate != 16000 or abs(len(wav) / rate - row["duration_seconds"]) > 1e-6:
            raise ValueError("new WAV duration/rate changed")
        cached[j] = prepare_waveform(wav)
    cached.flush()
    del cached
    temp.replace(output / "audio.npy")
    rebuilt = np.load(output / "audio.npy", mmap_mode="r")
    verify_original_prefix(source, rebuilt)
    write(
        output / "cache-complete.json",
        {
            "binding_sha256": binding["binding_sha256"],
            "shape": [len(rows), 48000],
            "audio_sha256": sha(output / "audio.npy"),
            "original_prefix_verified": True,
            "transparent_ntfs_compression": True,
        },
    )
    original.load_run(output)
    report = {
        "new_target_train": len(training),
        "target_train_total": sum(
            r["is_target"] for r in rows if r["split"] == "train"
        ),
        "original_calibration_and_evaluation_unchanged": True,
        "audit_records": len(audit),
        "new_train_word_counts": dict(Counter(r["word_id"] for r in training)),
        "new_train_speaker_groups": len({r["speaker"] for r in training}),
        "new_to_student_train_speaker_groups": len(
            {r["speaker"] for r in training if r["new_to_student_speaker"]}
        ),
        "fresh_audit_speaker_groups": len({r["speaker"] for r in audit}),
        "dataset_sha256": sha(output / "dataset.json"),
        "human_reviewed": False,
    }
    write(output / "preparation-results.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("phase", choices=["index", "segment", "prepare"])
    parser.add_argument("--per-word", type=int, default=300)
    parser.add_argument("--audit-limit", type=int, default=200)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--teacher-model", type=Path)
    parser.add_argument("--minimum-score", type=float, default=0.85)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--max-padded-seconds", type=float, default=64)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    {
        "index": index_candidates,
        "segment": segment_candidates,
        "prepare": prepare_dataset,
    }[args.phase](args)
