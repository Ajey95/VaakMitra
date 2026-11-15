"""PHN-001/002/003: recover independent MSWC word audio without truncation."""

from __future__ import annotations

import hashlib
import io
import json
import math
import re
import tarfile
import zipfile
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

try:
    from scripts.model import finetune_mobile_phoneme as original
except ModuleNotFoundError:
    import finetune_mobile_phoneme as original

from app.vaakmitra_word.phoneme_ctc import prepare_waveform, validate_splits

ROOT = Path("D:/VaakMitraData")
BASE = ROOT / "artifacts/phoneme-ta19-v2-early"
OUT = ROOT / "artifacts/phoneme-expanded-data-v1"


def parent(row):
    explicit = row.get("source_utterance_id") or row.get("parent_id")
    if explicit:
        return explicit
    folder = Path(row.get("audio_path", "")).parent.name
    if not folder:
        raise ValueError("missing source parent identity")
    return f"openslr127:{folder}"


def source_utterance_id(row):
    stem = Path(row["original_id"]).stem
    # Conservatively merge MSWC duplicate-crop suffixes for leakage guarding.
    match = re.fullmatch(r"(common_voice_ta_[0-9]+)(?:__[0-9]+)?", stem)
    if not match:
        raise ValueError("unknown MSWC source utterance naming")
    return f"commonvoice:ta:{match.group(1)}"


def validate_expansion_rows(base, expanded, audit_rows=()):
    if expanded[: len(base)] != base:
        raise ValueError("original rows/splits must remain unchanged")
    blocked_speakers = {r["speaker"] for r in base if r["split"] != "train"}
    blocked_parents = {parent(r) for r in base if r["split"] != "train"}
    hashes = {r["audio_sha256"] for r in base}
    for row in expanded[len(base) :]:
        if row["split"] != "train" or row["speaker"] in blocked_speakers:
            raise ValueError("expanded training leaks held-out split/speaker")
        if parent(row) in blocked_parents or row["audio_sha256"] in hashes:
            raise ValueError("expanded training leaks parent or duplicate")
        hashes.add(row["audio_sha256"])
    all_rows = expanded + list(audit_rows)
    parents = {}
    for row in all_rows:
        identity = parent(row)
        if identity in parents and parents[identity] != row["split"]:
            raise ValueError("source parent leakage across splits")
        parents[identity] = row["split"]
    validate_splits(all_rows)


def main():
    if OUT.exists():
        raise FileExistsError("use a fresh data output")
    meta, vocab = original.load_run(BASE)
    OUT.mkdir(parents=True)
    source = [
        json.loads(line)
        for line in (ROOT / "manifests/mswc-ta-other.jsonl").open(encoding="utf8")
    ]
    by_name = {r["audio_path"]: r for r in source}
    lexicon = zipfile.ZipFile(original.ZIP)
    lex = {
        e["word"]: e["units"]
        for e in json.load(lexicon.open("full-lexicon.json"))["entries"]
    }
    token_ids = {t: i for i, t in enumerate(vocab["tokens"])}
    extra_rows, extra_audio, audit_rows, rejected = [], [], [], Counter()
    existing_hashes = {r["audio_sha256"] for r in meta["rows"]}
    archives = []
    for split in ("train", "dev", "test"):
        archive = ROOT / f"raw/ml_spoken_words/data/opus/ta/{split}/audio/0.tar.gz"
        archives.append({"path": str(archive), "sha256": original.sha(archive)})
        with tarfile.open(archive) as tar:
            for member in tar:
                if not member.isfile():
                    continue
                row = by_name.get(member.name)
                if row is None:
                    rejected["not_in_source_manifest"] += 1
                    continue
                units = lex.get(row["transcript"])
                if not units or any(t not in token_ids for t in units):
                    rejected["no_frozen_phones"] += 1
                    continue
                raw = tar.extractfile(member).read()
                if hashlib.sha256(raw).hexdigest() != row["audio_sha256"]:
                    raise ValueError("archive/source audio hash mismatch")
                wav, rate = sf.read(io.BytesIO(raw), dtype="float32")
                if wav.ndim != 1 or not np.isfinite(wav).all():
                    rejected["audio_shape_or_nonfinite"] += 1
                    continue
                duration = len(wav) / rate
                if not 0.2 <= duration <= 3 or len(units) > 40:
                    rejected["duration_or_phone_length"] += 1
                    continue
                if (
                    np.sqrt(np.mean(wav * wav)) < 0.005
                    or np.mean(np.abs(wav) >= 0.99) > 0.01
                ):
                    rejected["quiet_or_clipped"] += 1
                    continue
                if rate != 16000:
                    factor = math.gcd(rate, 16000)
                    wav = resample_poly(wav, 16000 // factor, rate // factor).astype(
                        np.float32
                    )
                # Never stretch or crop a word; preserve its complete source duration.
                padded = prepare_waveform(wav)
                file = OUT / "audio" / f"{row['sample_id']}.wav"
                file.parent.mkdir(exist_ok=True)
                sf.write(file, wav, 16000, subtype="PCM_16")
                audio_hash = original.sha(file)
                if audio_hash in existing_hashes:
                    rejected["duplicate_audio"] += 1
                    continue
                existing_hashes.add(audio_hash)
                entry = {
                    "audio_path": str(file),
                    "audio_sha256": audio_hash,
                    "speaker": row["speaker_pseudonym"],
                    "split": row["split"],
                    "targets": [token_ids[t] for t in units],
                    "word_id": None,
                    "is_target": False,
                    "parent_id": source_utterance_id(row),
                    "source_utterance_id": source_utterance_id(row),
                    "source_crop_id": row["sample_id"],
                    "source_id": row["source_id"],
                    "source_audio_sha256": row["audio_sha256"],
                    "licence_id": row["licence_id"],
                    "transcript": row["transcript"],
                    "duration_seconds": duration,
                }
                if row["split"] == "train":
                    extra_rows.append(entry)
                    extra_audio.append(padded)
                else:
                    audit_rows.append(entry)
    rows = meta["rows"] + extra_rows
    validate_expansion_rows(meta["rows"], rows, audit_rows)
    original.write(
        OUT / "expansion-manifest.json",
        {
            "training": extra_rows,
            "audit": audit_rows,
            "archives": archives,
            "source_manifest_sha256": original.sha(
                ROOT / "manifests/mswc-ta-other.jsonl"
            ),
            "label_lexicon_sha256": original.sha(original.ZIP),
            "human_reviewed": False,
        },
    )
    binding = dict(
        meta["binding"],
        row_count=len(rows),
        expansion_sha256=original.sha(OUT / "expansion-manifest.json"),
    )
    binding.pop("binding_sha256", None)
    binding["binding_sha256"] = hashlib.sha256(
        json.dumps(binding, sort_keys=True).encode()
    ).hexdigest()
    new_meta = {
        "binding": binding,
        "rows": rows,
        "counts": dict(Counter(r["split"] for r in rows)),
        "parent_binding": meta["binding"],
        "parent_dataset_sha256": original.sha(BASE / "dataset.json"),
    }
    original.write(OUT / "dataset.json", new_meta)
    original.write(OUT / "vocabulary.json", vocab)
    original.write(
        OUT / "input-binding.json",
        {"dataset_sha256": original.sha(OUT / "dataset.json")},
    )
    source_audio = np.load(BASE / "audio.npy", mmap_mode="r")
    output = np.lib.format.open_memmap(
        OUT / "audio.npy", mode="w+", dtype="float32", shape=(len(rows), 48000)
    )
    for i in range(0, len(meta["rows"]), 128):
        output[i : i + len(source_audio[i : i + 128])] = source_audio[i : i + 128]
    output[len(meta["rows"]) :] = np.stack(extra_audio)
    output.flush()
    del output
    original.write(
        OUT / "cache-complete.json",
        {
            "binding_sha256": binding["binding_sha256"],
            "shape": [len(rows), 48000],
            "audio_sha256": original.sha(OUT / "audio.npy"),
        },
    )
    report = {
        "added_training": len(extra_rows),
        "reserved_audit": len(audit_rows),
        "rejected": dict(rejected),
        "original_rows_unchanged": True,
        "original_test_unchanged": True,
        "speakers_added": len({r["speaker"] for r in extra_rows}),
        "training_phone_units": len(
            {p for r in rows if r["split"] == "train" for p in r["targets"]}
        ),
        "note": "Additional adult word/sound diversity, not new app-word examples or child recordings.",
    }
    original.write(OUT / "preparation-results.json", report)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
