"""PHN-002/006: frozen-model edit diagnostics and derived legacy-parent audit."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import onnxruntime as ort

try:
    from scripts.model import finetune_mobile_phoneme as original
    from scripts.model.prepare_phoneme_expansion import source_utterance_id
except ModuleNotFoundError:
    import finetune_mobile_phoneme as original
    from prepare_phoneme_expansion import source_utterance_id


def edit_counts(reference, prediction):
    table = [[0] * (len(prediction) + 1) for _ in range(len(reference) + 1)]
    for i in range(len(reference) + 1):
        table[i][0] = i
    for j in range(len(prediction) + 1):
        table[0][j] = j
    for i, a in enumerate(reference, 1):
        for j, b in enumerate(prediction, 1):
            table[i][j] = min(
                table[i - 1][j] + 1, table[i][j - 1] + 1, table[i - 1][j - 1] + (a != b)
            )
    counts = {"substitution": 0, "deletion": 0, "insertion": 0}
    i, j = len(reference), len(prediction)
    # Minimum-edit backtrace ties: diagonal (match/substitution), deletion, insertion.
    # These allocations are diagnostic, not independently observed acoustic causes.
    while i or j:
        if (
            i
            and j
            and table[i][j]
            == table[i - 1][j - 1] + (reference[i - 1] != prediction[j - 1])
        ):
            counts["substitution"] += reference[i - 1] != prediction[j - 1]
            i, j = i - 1, j - 1
        elif i and table[i][j] == table[i - 1][j] + 1:
            counts["deletion"] += 1
            i -= 1
        else:
            counts["insertion"] += 1
            j -= 1
    assert sum(counts.values()) == table[-1][-1]
    return counts


def main():
    root = Path("D:/VaakMitraData")
    previous = root / "artifacts/phoneme-ta19-v2-early"
    current = root / "artifacts/phoneme-ta19-v3-improved"
    delivery = root / "deliveries/phoneme-improvement-20261111"
    meta = json.loads((previous / "dataset.json").read_text(encoding="utf8"))
    audio = np.load(previous / "audio.npy", mmap_mode="r")
    intended = json.loads(
        (original.BACKEND / "data/vocabulary/ta-v1-intended.json").read_text(
            encoding="utf8"
        )
    )
    labels = {r["word_id"]: r["canonical_tamil"] for r in intended["entries"]}
    options = ort.SessionOptions()
    options.intra_op_num_threads = 2
    options.inter_op_num_threads = 1
    sessions = {}
    for name, path in [("previous", previous), ("improved", current)]:
        manifest = json.loads((path / "bundle/bundle.json").read_text(encoding="utf8"))
        sessions[name] = ort.InferenceSession(
            str(path / "bundle" / manifest["model_file"]),
            options,
            providers=["CPUExecutionProvider"],
        )
    report = {
        "tie_rule": "minimum Levenshtein cost; backtrace diagonal match/substitution, then deletion, then insertion",
        "phonetic_labels": "provisional canonical lexicon, not expert acoustic transcription",
        "splits": {},
    }
    text = [
        "# Frozen-model phoneme error breakdown",
        "",
        "Minimum-edit alignment ties prefer diagonal (match/substitution), then deletion, then insertion. Counts can change under another optimal alignment; totals/PER do not. Labels are provisional canonical phone sequences. No model was updated from these diagnostics.",
        "",
    ]
    for split in ["calibration", "evaluation"]:
        indices = [
            i
            for i, r in enumerate(meta["rows"])
            if r["split"] == split and r["is_target"]
        ]
        split_report = {}
        for name, session in sessions.items():
            records = []
            for offset in range(0, len(indices), 16):
                chunk = indices[offset : offset + 16]
                logits = session.run(None, {"waveform": np.array(audio[chunk])})[0]
                for index, raw in zip(chunk, logits):
                    row = meta["rows"][index]
                    pred = original.ctc_decode(raw.argmax(-1))
                    counts = edit_counts(row["targets"], pred)
                    records.append(
                        {
                            "word_id": row["word_id"],
                            "word": labels[row["word_id"]],
                            "speaker": row["speaker"],
                            "reference_phones": len(row["targets"]),
                            "edits": sum(counts.values()),
                            "exact": pred == row["targets"],
                            **counts,
                        }
                    )

            def summarize(values):
                total = Counter()
                for r in values:
                    for key in [
                        "reference_phones",
                        "edits",
                        "exact",
                        "substitution",
                        "deletion",
                        "insertion",
                    ]:
                        total[key] += r[key]
                return dict(
                    total,
                    records=len(values),
                    speakers=len({r["speaker"] for r in values}),
                    per=total["edits"] / total["reference_phones"],
                )

            byword = defaultdict(list)
            byspeaker = defaultdict(list)
            for r in records:
                byword[r["word_id"]].append(r)
                byspeaker[r["speaker"]].append(r)
            split_report[name] = {
                "total": summarize(records),
                "by_word": {
                    k: dict(word=labels[k], **summarize(v))
                    for k, v in sorted(byword.items())
                },
                "by_speaker": {k: summarize(v) for k, v in sorted(byspeaker.items())},
            }
        report["splits"][split] = split_report
        text += [
            f"## {split.capitalize()} target words",
            "",
            "| Model | Clips | Reference phones | Substitutions | Deletions | Insertions | PER | Exact |",
            "|---|---:|---:|---:|---:|---:|---:|---:|",
        ]
        for name, metrics in split_report.items():
            t = metrics["total"]
            text.append(
                f"| {name} | {t['records']} | {t['reference_phones']} | {t['substitution']} | {t['deletion']} | {t['insertion']} | {t['per'] * 100:.2f}% | {t['exact']} |"
            )
        text += [
            "",
            "| Word | Clips / speakers | Previous S/D/I | Improved S/D/I | Previous PER | Improved PER |",
            "|---|---:|---:|---:|---:|---:|",
        ]
        for key, a in split_report["previous"]["by_word"].items():
            b = split_report["improved"]["by_word"][key]
            text.append(
                f"| {a['word']} ({key}) | {a['records']} / {a['speakers']} | {a['substitution']}/{a['deletion']}/{a['insertion']} | {b['substitution']}/{b['deletion']}/{b['insertion']} | {a['per'] * 100:.2f}% | {b['per'] * 100:.2f}% |"
            )
        text.append("")
    original.write(delivery / "error-analysis.json", report)
    (delivery / "error-analysis.md").write_text("\n".join(text), encoding="utf8")

    # Already-produced expansion is immutable. Recover true parents into a new audit;
    # never silently rewrite its bound legacy crop-parent metadata or cache.
    expansion_path = root / "artifacts/phoneme-expanded-data-v1/expansion-manifest.json"
    expansion = json.loads(expansion_path.read_text(encoding="utf8"))
    source = {
        r["sample_id"]: r
        for r in map(
            json.loads, (root / "manifests/mswc-ta-other.jsonl").open(encoding="utf8")
        )
    }
    sets = defaultdict(set)
    raw_stems = defaultdict(set)
    mapping = []
    for row in expansion["training"] + expansion["audit"]:
        identity = source_utterance_id(source[row["parent_id"]])
        sets[row["split"]].add(identity)
        raw_stems[row["split"]].add(Path(source[row["parent_id"]]["original_id"]).stem)
        mapping.append(
            {
                "source_crop_id": row["parent_id"],
                "source_utterance_id": identity,
                "split": row["split"],
            }
        )
    overlaps = {f"{a}:{b}": len(sets[a] & sets[b]) for a in sets for b in sets if a < b}
    if any(overlaps.values()):
        raise ValueError("actual source utterance overlap")
    train_words = {
        r["transcript"]
        for r in map(json.loads, original.SOURCE.open(encoding="utf8"))
        if r["split"] == "train"
    }
    audit_words = {r["transcript"] for r in expansion["audit"]}
    parent_audit = {
        "legacy_expansion_manifest_sha256": original.sha(expansion_path),
        "legacy_parent_field": "crop sample_id; corrected source identities derived here without modifying immutable inputs",
        "identity_normalization": "Common Voice numeric clip ID; optional MSWC __N crop suffix ignored conservatively",
        "raw_source_file_stems": {k: len(v) for k, v in raw_stems.items()},
        "unique_source_utterances": {k: len(v) for k, v in sets.items()},
        "train_vs_all_audit_overlap": len(
            sets["train"] & (sets["calibration"] | sets["evaluation"])
        ),
        "cross_split_parent_overlaps": overlaps,
        "audit_seen_word_clips": sum(
            r["transcript"] in train_words for r in expansion["audit"]
        ),
        "audit_unseen_word_clips": sum(
            r["transcript"] not in train_words for r in expansion["audit"]
        ),
        "audit_seen_word_types": len(audit_words & train_words),
        "audit_unseen_word_types": len(audit_words - train_words),
        "mapping": mapping,
    }
    original.write(delivery / "source-parent-audit.json", parent_audit)
    print(
        json.dumps(
            {
                "totals": {
                    s: {m: r["total"] for m, r in v.items()}
                    for s, v in report["splits"].items()
                },
                "parent_audit": {
                    k: v for k, v in parent_audit.items() if k != "mapping"
                },
            },
            ensure_ascii=True,
        ),
        flush=True,
    )


if __name__ == "__main__":
    main()
