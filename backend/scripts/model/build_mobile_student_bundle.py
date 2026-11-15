"""Build the immutable DEC-028/MST-006..007 Android runtime bundle."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sys

import numpy as np
import onnxruntime as ort


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.mobile_student_bundle import ReferenceExample, build_reference_centroids, verify_bundle  # noqa: E402
from app.vaakmitra_word.mobile_student_data import MOBILE_LABELS, load_mobile_samples, preprocess_pcm16, read_pcm16_wav  # noqa: E402


DISPLAY = {
    "TA_WORD_0001": ("அம்மா", "Amma", "Mother"),
    "TA_WORD_0002": ("அப்பா", "Appa", "Father"),
    "TA_WORD_0012": ("உணவு", "Unavu", "Food"),
    "TA_WORD_0013": ("வேண்டும்", "Vendum", "Want / need"),
    "TA_WORD_0014": ("வேண்டாம்", "Vendaam", "Do not want"),
    "TA_WORD_0015": ("இன்னும்", "Innum", "More"),
    "TA_WORD_0016": ("போதும்", "Podhum", "Enough"),
    "TA_WORD_0017": ("உதவி", "Udhavi", "Help"),
    "TA_WORD_0049": ("சொல்", "Sol", "Say / tell"),
    "TA_WORD_0050": ("படி", "Padi", "Read"),
    "TA_WORD_0072": ("படம்", "Padam", "Picture"),
    "TA_WORD_0082": ("இல்லை", "Illai", "No / not"),
    "TA_WORD_0083": ("ஆம்", "Aam", "Yes"),
    "TA_WORD_0086": ("தலை", "Thalai", "Head"),
    "TA_WORD_0090": ("பாதுகாப்பு", "Paadhukaappu", "Safety"),
    "TA_WORD_0096": ("மீண்டும்", "Meendum", "Again"),
    "TA_WORD_0098": ("இங்கே", "Inge", "Here"),
    "TA_WORD_0099": ("அங்கே", "Ange", "There"),
    "TA_WORD_0100": ("சேர்ந்து", "Serndhu", "Together"),
}


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _infer(session: ort.InferenceSession, paths: list[Path], batch_size: int = 128) -> tuple[np.ndarray, np.ndarray]:
    embeddings: list[np.ndarray] = []
    logits: list[np.ndarray] = []
    for start in range(0, len(paths), batch_size):
        waveforms = np.stack([preprocess_pcm16(read_pcm16_wav(path)) for path in paths[start : start + batch_size]])
        embedding, values = session.run(["embedding", "logits"], {"waveform": waveforms})
        embeddings.append(np.asarray(embedding))
        logits.append(np.asarray(values))
    return np.vstack(embeddings), np.vstack(logits)


def _softmax(logits: np.ndarray) -> np.ndarray:
    shifted = logits - logits.max(axis=1, keepdims=True)
    values = np.exp(shifted)
    return values / values.sum(axis=1, keepdims=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--vad", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--quantization-report", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bundle-version", default="vm-mobile-student-ta19-v0")
    parser.add_argument("--architecture-version", default="raw-wave-global-pool-v0")
    args = parser.parse_args()
    if args.bundle_version == "vm-mobile-student-ta19-v1" and args.architecture_version != "raw-wave-temporal8-dc-rms-v1":
        raise RuntimeError("bundle_architecture_mismatch")

    samples = load_mobile_samples(args.manifest, args.audio_root, verify_hashes=False, verify_files=False)
    train = [sample for sample in samples if sample.split == "train" and sample.label != "OTHER"]
    calibration = [sample for sample in samples if sample.split == "calibration"]
    chosen = []
    seen: dict[str, set[str]] = {label: set() for label in MOBILE_LABELS[:-1]}
    for sample in sorted(train, key=lambda item: (item.label, item.sample_id)):
        if sample.speaker_pseudonym not in seen[sample.label] and len(seen[sample.label]) < 32:
            chosen.append(sample)
            seen[sample.label].add(sample.speaker_pseudonym)

    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    reference_embeddings, _ = _infer(session, [sample.audio_path for sample in chosen])
    references = build_reference_centroids(
        [
            ReferenceExample(sample.sample_id, sample.speaker_pseudonym, sample.label, reference_embeddings[index])
            for index, sample in enumerate(chosen)
        ],
        labels=MOBILE_LABELS,
    )
    calibration_embeddings, calibration_logits = _infer(session, [sample.audio_path for sample in calibration])
    probabilities = _softmax(calibration_logits)
    target_duration_samples = {
        label: int(np.median([read_pcm16_wav(sample.audio_path).size for sample in train if sample.label == label]))
        for label in MOBILE_LABELS[:-1]
    }

    low_thresholds: dict[str, float] = {}
    high_thresholds: dict[str, float] = {}
    target_reports: dict[str, object] = {}
    for target_index, target in enumerate(MOBILE_LABELS[:-1]):
        reference = references[target].centroid
        similarities = calibration_embeddings @ reference
        scores = 0.7 * probabilities[:, target_index] + 0.3 * ((similarities + 1.0) / 2.0)
        positive = np.asarray([sample.label == target for sample in calibration])
        negative_scores = scores[~positive]
        positive_scores = scores[positive]
        low = float(min(0.35, np.quantile(negative_scores, 0.75)))
        high = float(max(0.65, np.quantile(negative_scores, 0.99)))
        if len(positive_scores):
            high = min(high, float(np.max(positive_scores)))
        high = max(high, low + 0.05)
        low_thresholds[target] = low
        high_thresholds[target] = high
        target_reports[target] = {
            "positive_samples": int(positive.sum()),
            "negative_samples": int((~positive).sum()),
            "low_threshold": low,
            "high_threshold": high,
            "positive_at_or_above_high": int(np.sum(positive_scores >= high)),
            "negative_at_or_above_high": int(np.sum(negative_scores >= high)),
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(args.model, args.output_dir / "mobile_word_student.int8.onnx")
    shutil.copyfile(args.vad, args.output_dir / "silero_vad.onnx")
    _write_json(
        args.output_dir / "labels.json",
        {
            "schema_version": "vaakmitra-mobile-labels-1",
            "labels": [
                {"id": label, "index": index, "tamil": DISPLAY[label][0], "transliteration": DISPLAY[label][1], "meaning": DISPLAY[label][2]}
                if label != "OTHER" else {"id": "OTHER", "index": index}
                for index, label in enumerate(MOBILE_LABELS)
            ],
        },
    )
    _write_json(
        args.output_dir / "reference_bank.json",
        {
            "schema_version": "vaakmitra-mobile-reference-bank-1",
            "bundle_version": args.bundle_version,
            "architecture_version": args.architecture_version,
            "model_sha256": _hash(args.model),
            "references": {
                label: {
                    "centroid": [round(float(value), 9) for value in item.centroid],
                    "sample_ids": list(item.sample_ids),
                    "speaker_count": item.speaker_count,
                }
                for label, item in sorted(references.items())
            },
        },
    )
    _write_json(
        args.output_dir / "adult_engineering_calibration.json",
        {
            "schema_version": "vaakmitra-mobile-adult-engineering-calibration-1",
            "bundle_version": args.bundle_version,
            "architecture_version": args.architecture_version,
            "model_sha256": _hash(args.model),
            "minimum_margin": 0.10,
            "minimum_similarity": 0.60,
            "target_duration_samples": target_duration_samples,
            "low_thresholds": low_thresholds,
            "high_thresholds": high_thresholds,
            "target_reports": target_reports,
            "approved_for_child_scoring": False,
        },
    )
    runtime_files = [
        "mobile_word_student.int8.onnx", "labels.json", "reference_bank.json",
        "adult_engineering_calibration.json", "silero_vad.onnx",
    ]
    quantization = json.loads(args.quantization_report.read_text(encoding="utf-8"))
    inventory = json.loads(args.inventory.read_text(encoding="utf-8"))
    manifest = {
        "schema_version": "vaakmitra-mobile-bundle-1",
        "bundle_version": args.bundle_version,
        "architecture_version": args.architecture_version,
        "requirements": [
            "DEC-028", "DEC-029", "MST-001", "MST-002", "MST-006", "MST-007",
            "MST-011", "MST-012", "MST-015", "MST-016", "MST-017",
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "labels": list(MOBILE_LABELS),
        "input": {"name": "waveform", "shape": [1, 32000], "dtype": "float32", "sample_rate": 16000},
        "outputs": {"embedding": [1, 64], "logits": [1, 20]},
        "preprocessing_version": "vad-energy-target-duration-pad-graph-dc-rms-v3",
        "vad": {"threshold": 0.5, "minimum_speech_ms": 200, "merge_tolerance_ms": 700},
        "quantization_summary": quantization,
        "source_hashes": inventory["hashes"],
        "files": {name: _hash(args.output_dir / name) for name in runtime_files},
        "approved_for_child_scoring": False,
        "release_build_enabled": False,
        "child_data_used": False,
    }
    _write_json(args.output_dir / "bundle.json", manifest)
    verify_bundle(args.output_dir)
    print(json.dumps(manifest, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
