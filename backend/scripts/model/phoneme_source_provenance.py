"""PHN-002/006: distinguish project speaker folds from upstream source folders."""

from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from pathlib import Path


def source_parent(row):
    explicit = row.get("source_utterance_id") or row.get("parent_id")
    return (
        explicit.removeprefix("openslr127:")
        if explicit
        else Path(row["audio_path"]).parent.name
    )


def summarize_sources(expansion, candidates, expected_word_ids):
    origins = {
        r["record"]["utterance_id"]: r["record"]["official_split"] for r in candidates
    }
    if len(origins) != len(candidates) or any(
        p not in {"train", "test"} for p in origins.values()
    ):
        raise ValueError("invalid or duplicated upstream source records")

    def summarize(rows):
        clips = Counter()
        utterances = defaultdict(set)
        for row in rows:
            parent = source_parent(row)
            if parent not in origins:
                raise ValueError("missing upstream source parent")
            role = origins[parent]
            clips[role] += 1
            utterances[role].add(parent)
        return {
            "clips": len(rows),
            "official_source_clip_counts": dict(clips),
            "official_source_utterance_counts": {
                k: len(v) for k, v in utterances.items()
            },
        }

    train = summarize(expansion["training"])
    audit = summarize(expansion["audit"])
    counts = Counter(r["word_id"] for r in expansion["audit"])
    if set(counts) - set(expected_word_ids):
        raise ValueError("audit word outside frozen app vocabulary")
    largest = (
        min(counts.items(), key=lambda item: (-item[1], item[0]))
        if counts
        else (None, 0)
    )
    return {
        "split_definition": "Project-defined speaker-disjoint folds; not the publisher official source split",
        "upstream_official_test_untouched": False
        if train["official_source_clip_counts"].get("test")
        else None,
        "new_training": train,
        "audit": audit,
        "audit_coverage": {
            "app_words": len(expected_word_ids),
            "covered_words": len(counts),
            "word_clip_counts": dict(sorted(counts.items())),
            "largest_word": {"word_id": largest[0], "clips": largest[1]},
        },
    }


def main():
    data = Path("D:/VaakMitraData")
    root = data / "artifacts/phoneme-ta19-extra-r2-v1"
    base = data / "artifacts/phoneme-ta19-v3-improved"
    analysis = data / "analysis/phoneme-round2-20261111"
    read = lambda p: json.loads(p.read_text(encoding="utf8"))
    sha = lambda p: hashlib.file_digest(p.open("rb"), "sha256").hexdigest()
    expansion = read(root / "expansion-manifest.json")
    meta = read(root / "dataset.json")
    candidate_file = analysis / "target-candidates.jsonl"
    assert sha(candidate_file) == expansion["candidate_sha256"]
    assert sha(root / "expansion-manifest.json") == meta["binding"]["expansion_sha256"]
    candidates = [json.loads(l) for l in candidate_file.open(encoding="utf8")]
    vocab = read(root / "vocabulary.json")
    report = summarize_sources(expansion, candidates, set(vocab["expected"]))
    original = read(base / "dataset.json")["rows"]
    assert meta["rows"][: len(original)] == original
    corpus = Path(
        "D:/VaakMitra/modeling/artifacts/corpora/openslr-127/extracted/mile_tamil_asr_corpus"
    )
    old_origins = {}
    for row in original:
        parent = source_parent(row)
        if parent in old_origins:
            continue
        roles = [
            role
            for role in ("train", "test")
            if (corpus / role / "audio_files" / f"{parent}.wav").is_file()
        ]
        if len(roles) != 1:
            raise ValueError("ambiguous original upstream source parent")
        old_origins[parent] = roles[0]
    prepared = defaultdict(Counter)
    for row in original:
        prepared[row["split"]][old_origins[source_parent(row)]] += 1
    for role, count in report["new_training"]["official_source_clip_counts"].items():
        prepared["train"][role] += count
    report["prepared_dataset_official_origins_by_project_fold"] = {
        k: dict(v) for k, v in prepared.items()
    }
    report["original_target_evaluation_official_origins"] = dict(
        Counter(
            old_origins[source_parent(r)]
            for r in original
            if r["split"] == "evaluation" and r["is_target"]
        )
    )
    catalog = read(
        Path(__file__).resolve().parents[2] / "data/vocabulary/ta-v1-intended.json"
    )
    labels = {r["word_id"]: r["canonical_tamil"] for r in catalog["entries"]}
    largest = report["audit_coverage"]["largest_word"]
    largest["tamil"] = labels[largest["word_id"]]
    report["dataset_sha256"] = sha(root / "dataset.json")
    report["expansion_manifest_sha256"] = sha(root / "expansion-manifest.json")
    report["candidate_manifest_sha256"] = sha(candidate_file)
    report["scope_warning"] = (
        "The full upstream official test is not an untouched benchmark for this trained model. Audit aggregate is partial and word-frequency weighted; it is not balanced coverage of all app words."
    )
    path = root / "source-provenance.json"
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf8")
    tmp.replace(path)
    print(json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
