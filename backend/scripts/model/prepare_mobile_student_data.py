"""Inventory the frozen DEC-028 adult/public mobile-student inputs."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path
import sys


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.mobile_student_data import MOBILE_LABELS, TeacherTargetIndex, load_mobile_samples  # noqa: E402


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--embedding-root", type=Path, required=True)
    parser.add_argument("--teacher", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--teacher-targets", type=Path)
    parser.add_argument("--verify-audio-hashes", action="store_true")
    args = parser.parse_args()

    samples = load_mobile_samples(args.manifest, args.audio_root, verify_hashes=args.verify_audio_hashes)
    teacher = TeacherTargetIndex.from_artifacts(args.classifier, sorted(args.embedding_root.glob("shard-*.npz")))
    if teacher.labels != MOBILE_LABELS:
        raise RuntimeError("teacher_label_order_mismatch")
    missing_teacher = sorted(sample.sample_id for sample in samples if teacher.probabilities_for(sample.sample_id) is None)
    if args.teacher_targets is not None:
        teacher.save(args.teacher_targets)

    counts: dict[str, Counter[str]] = defaultdict(Counter)
    speakers: dict[str, dict[str, set[str]]] = defaultdict(lambda: defaultdict(set))
    for sample in samples:
        counts[sample.split][sample.label] += 1
        speakers[sample.split][sample.label].add(sample.speaker_pseudonym)
    payload = {
        "schema_version": "vaakmitra-mobile-student-inventory-1",
        "requirements": ["DEC-028", "MST-001", "MST-002", "MST-003", "MST-004"],
        "labels": list(MOBILE_LABELS),
        "sample_count": len(samples),
        "split_counts": {split: dict(sorted(value.items())) for split, value in sorted(counts.items())},
        "speaker_counts": {
            split: {label: len(values) for label, values in sorted(by_label.items())}
            for split, by_label in sorted(speakers.items())
        },
        "missing_teacher_targets": missing_teacher,
        "hashes": {
            "teacher_nemo": _hash(args.teacher),
            "teacher_classifier": _hash(args.classifier),
            "source_manifest": _hash(args.manifest),
        },
        "child_data_used": False,
        "teacher_targets_path": str(args.teacher_targets) if args.teacher_targets is not None else None,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
