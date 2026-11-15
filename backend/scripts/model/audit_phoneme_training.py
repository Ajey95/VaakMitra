"""PHN-001/002: deterministic training-only integrity/boundary inventory."""

import json
from collections import Counter
from pathlib import Path

import numpy as np
import soundfile as sf

try:
    from scripts.model import finetune_mobile_phoneme as original
except ModuleNotFoundError:
    import finetune_mobile_phoneme as original


def main():
    root = Path("D:/VaakMitraData")
    source = [json.loads(line) for line in original.SOURCE.open(encoding="utf8")]
    review_file = root / "manifests/openslr127-word-v1-reviewed-machine-review.json"
    review = json.loads(review_file.read_text())
    if review["dataset_manifest_hash"] != original.sha(original.SOURCE):
        raise ValueError("quality/source binding mismatch")
    scores = {r["sample_id"]: r["quality_score"] for r in review["approvals"]}
    counts, issues, targets = Counter(), [], Counter()
    for row in source:
        if row["split"] != "train":
            continue
        path = original.AUDIO / row["audio_path"]
        if original.sha(path) != row["audio_sha256"]:
            raise ValueError("source training audio changed")
        wav, rate = sf.read(path, dtype="float32")
        if rate != 16000 or wav.ndim != 1 or not np.isfinite(wav).all():
            raise ValueError("invalid training audio")
        counts["training_hashes_verified"] += 1
        if abs(len(wav) / rate - row["duration_seconds"]) > 0.001:
            counts["duration_mismatch"] += 1
        rms = np.sqrt(np.mean(wav * wav) + 1e-12)
        edge = max(np.sqrt(np.mean(wav[:320] ** 2)), np.sqrt(np.mean(wav[-320:] ** 2)))
        suspect = edge > 0.5 * rms
        counts["high_edge_energy_flag"] += int(suspect)
        if suspect or scores[row["sample_id"]] < 0.9:
            issues.append(
                {
                    "sample_id": row["sample_id"],
                    "audio_path": row["audio_path"],
                    "quality": scores[row["sample_id"]],
                    "high_edge_energy": bool(suspect),
                }
            )
        if row["canonical_word_id"]:
            targets[row["canonical_word_id"]] += 1
    out = root / "analysis/phoneme-improvement-20261111/training-audit.json"
    original.write(
        out,
        {
            "counts": counts,
            "word_counts": targets,
            "flags": issues,
            "human_reviewed": False,
            "source_sha256": original.sha(original.SOURCE),
            "review_sha256": original.sha(review_file),
            "note": "High edge energy is an inspection flag, not evidence of a cut-off phoneme; no label correction inferred from model predictions.",
        },
    )
    print(json.dumps({"counts": counts, "flagged_records": len(issues)}), flush=True)


if __name__ == "__main__":
    main()
