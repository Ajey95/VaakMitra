"""Train an immutable balanced word classifier from governed embedding shards."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.classifier_training import (  # noqa: E402
    ClassifierTrainingError,
    TrainingExample,
    save_classifier_artifact,
    train_classifier,
)
from app.vaakmitra_word.embedding_store import load_embedding_shard  # noqa: E402
from app.vaakmitra_word.model import sha256_file  # noqa: E402


def _active_labels(vocabulary_path: Path) -> tuple[str, ...]:
    payload = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    words = payload.get("words")
    entries = payload.get("entries")
    if isinstance(entries, list):
        labels = [
            str(item["word_id"])
            for item in entries
            if item.get("state") == "active" and item.get("scoreable") is True
        ]
    elif isinstance(words, dict):
        labels = list(words)
    elif isinstance(words, list):
        labels = [
            str(item["word_id"])
            for item in words
            if item.get("state", "active") == "active"
        ]
    else:
        raise ClassifierTrainingError("vocabulary_words_invalid")
    if not labels:
        raise ClassifierTrainingError("no_active_target_words")
    return tuple(sorted(labels)) + ("OTHER",)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--minimum-other", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    if args.minimum_other < 1:
        parser.error("--minimum-other must be positive")

    model_hash = args.model_sha256.lower()
    vocabulary_hash = sha256_file(args.vocabulary)
    source_hash = sha256_file(args.source_manifest)
    labels = _active_labels(args.vocabulary)
    examples: list[TrainingExample] = []
    for shard_path in sorted(args.embedding_root.glob("shard-*.npz")):
        shard = load_embedding_shard(
            shard_path,
            model_hash=model_hash,
            vocabulary_hash=vocabulary_hash,
            source_manifest_hash=source_hash,
        )
        for item in shard.items:
            label = item.canonical_word_id or "OTHER"
            if label in labels and item.split in {"train", "calibration", "evaluation"}:
                examples.append(
                    TrainingExample(
                        sample_id=item.sample_id,
                        speaker_pseudonym=item.speaker_pseudonym,
                        label=label,
                        split=item.split,
                        embedding=item.embedding,
                    )
                )
    other_count = sum(example.label == "OTHER" for example in examples)
    if other_count < args.minimum_other:
        raise ClassifierTrainingError(
            f"other_examples_below_minimum:{other_count}<{args.minimum_other}"
        )

    artifact, report = train_classifier(
        examples,
        labels=labels,
        model_hash=model_hash,
        vocabulary_hash=vocabulary_hash,
        seed=args.seed,
    )
    save_classifier_artifact(args.output, artifact)
    payload = {
        "schema_version": "vaakmitra-classifier-training-report-1",
        "model_hash": model_hash,
        "vocabulary_hash": vocabulary_hash,
        "dataset_manifest_hash": source_hash,
        "seed": args.seed,
        "minimum_other": args.minimum_other,
        **asdict(report),
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
