"""Extract governed IndicConformer embeddings into resumable immutable shards."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy.io import wavfile


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.corpus import CorpusRecord  # noqa: E402
from app.vaakmitra_word.embedding_store import (  # noqa: E402
    EmbeddingItem,
    completed_sample_ids,
    write_embedding_shard,
)
from app.vaakmitra_word.model import NeMoIndicConformerAdapter, sha256_file  # noqa: E402


def _read_manifest(path: Path) -> list[CorpusRecord]:
    records = []
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                records.append(CorpusRecord.model_validate_json(line))
    return records


def _load_pcm(path: Path) -> tuple[int, np.ndarray]:
    sample_rate, raw = wavfile.read(path)
    samples = np.asarray(raw)
    if samples.dtype.kind in "iu":
        limit = max(abs(np.iinfo(samples.dtype).min), np.iinfo(samples.dtype).max)
        samples = samples.astype(np.float32) / float(limit)
    else:
        samples = samples.astype(np.float32)
    if samples.ndim == 2:
        samples = samples.mean(axis=1)
    return int(sample_rate), samples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--shard-size", type=int, default=64)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--device", default="cuda")
    args = parser.parse_args()
    if args.shard_size <= 0 or (args.limit is not None and args.limit <= 0):
        parser.error("--shard-size and --limit must be positive")

    source_manifest_hash = sha256_file(args.source_manifest)
    vocabulary_hash = sha256_file(args.vocabulary)
    actual_model_hash = sha256_file(args.model)
    if actual_model_hash != args.model_sha256.lower():
        raise RuntimeError("model_integrity_mismatch")
    args.output_root.mkdir(parents=True, exist_ok=True)
    completed = completed_sample_ids(
        args.output_root,
        model_hash=actual_model_hash,
        vocabulary_hash=vocabulary_hash,
        source_manifest_hash=source_manifest_hash,
    )
    records = [record for record in _read_manifest(args.source_manifest) if record.sample_id not in completed]
    if args.limit is not None:
        records = records[: args.limit]

    model = NeMoIndicConformerAdapter(
        model_path=args.model,
        expected_sha256=actual_model_hash,
        device=args.device,
    )
    started = time.perf_counter()
    model.load()
    load_seconds = time.perf_counter() - started
    shard_number = len(list(args.output_root.glob("shard-*.npz"))) + 1
    pending: list[EmbeddingItem] = []
    written = 0

    def flush() -> None:
        nonlocal shard_number, written
        if not pending:
            return
        shard_id = f"shard-{shard_number:05d}"
        write_embedding_shard(
            args.output_root / f"{shard_id}.npz",
            shard_id=shard_id,
            items=tuple(pending),
            model_hash=actual_model_hash,
            vocabulary_hash=vocabulary_hash,
            source_manifest_hash=source_manifest_hash,
        )
        written += len(pending)
        pending.clear()
        shard_number += 1

    inference_started = time.perf_counter()
    for record in records:
        audio_path = (args.audio_root / record.audio_path).resolve()
        sample_rate, samples = _load_pcm(audio_path)
        evidence = model.infer(samples, sample_rate, record.transcript or "OTHER")
        pending.append(
            EmbeddingItem(
                sample_id=record.sample_id,
                canonical_word_id=record.canonical_word_id,
                speaker_pseudonym=record.speaker_pseudonym,
                split=record.split,
                embedding=evidence.embeddings,
            )
        )
        if len(pending) >= args.shard_size:
            flush()
    flush()
    inference_seconds = time.perf_counter() - inference_started

    peak_allocated = None
    peak_reserved = None
    try:
        import torch

        if torch.cuda.is_available():
            peak_allocated = int(torch.cuda.max_memory_allocated())
            peak_reserved = int(torch.cuda.max_memory_reserved())
    except ImportError:
        pass
    report = {
        "schema_version": "vaakmitra-embedding-extraction-report-1",
        "model_hash": actual_model_hash,
        "vocabulary_hash": vocabulary_hash,
        "source_manifest_hash": source_manifest_hash,
        "source_records": len(records) + len(completed),
        "already_completed": len(completed),
        "written_this_run": written,
        "model_load_seconds": load_seconds,
        "inference_seconds": inference_seconds,
        "peak_cuda_allocated_bytes": peak_allocated,
        "peak_cuda_reserved_bytes": peak_reserved,
        "run_fingerprint": hashlib.sha256(
            f"{actual_model_hash}:{vocabulary_hash}:{source_manifest_hash}".encode("ascii")
        ).hexdigest(),
    }
    (args.output_root / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
