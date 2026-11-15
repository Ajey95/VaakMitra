"""Export, statically quantize and gate the frozen DEC-028 student checkpoint."""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

import numpy as np
import torch


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.mobile_student_data import MOBILE_LABELS, load_mobile_samples, preprocess_pcm16, read_pcm16_wav  # noqa: E402
from app.vaakmitra_word.mobile_student_export import (  # noqa: E402
    ArrayCalibrationReader,
    assess_quantization_parity,
    export_fp32_onnx,
    quantize_int8_onnx,
    require_mobile_candidate_gate,
    run_onnx,
)
from app.vaakmitra_word.mobile_student_model import MobileWordStudent  # noqa: E402


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _waveform(path: Path) -> np.ndarray:
    return preprocess_pcm16(read_pcm16_wav(path))


def _batched_logits(model_path: Path, paths: list[Path], batch_size: int) -> np.ndarray:
    outputs: list[np.ndarray] = []
    for start in range(0, len(paths), batch_size):
        batch = np.stack([_waveform(path) for path in paths[start : start + batch_size]])
        outputs.append(run_onnx(model_path, batch)[1])
    return np.vstack(outputs)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--calibration-limit", type=int, default=512)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    if tuple(checkpoint.get("labels", ())) != MOBILE_LABELS:
        raise RuntimeError("checkpoint_label_order_mismatch")
    model = MobileWordStudent()
    model.load_state_dict(checkpoint["model"])
    model.eval()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    fp32_path = args.output_dir / "mobile_word_student.fp32.onnx"
    int8_path = args.output_dir / "mobile_word_student.int8.onnx"
    export_fp32_onnx(model, fp32_path)

    samples = load_mobile_samples(args.manifest, args.audio_root, verify_hashes=False, verify_files=False)
    calibration = [sample for sample in samples if sample.split == "calibration"]
    evaluation = [sample for sample in samples if sample.split == "evaluation"]
    if args.calibration_limit < 20:
        raise RuntimeError("calibration_limit_too_small")
    indices = np.linspace(0, len(calibration) - 1, min(args.calibration_limit, len(calibration)), dtype=int)
    calibration_batches = [
        np.stack([_waveform(calibration[index].audio_path) for index in indices[start : start + args.batch_size]])
        for start in range(0, len(indices), args.batch_size)
    ]
    # MST-005/011: keep the channel-sensitive convolution stack in FP32 and
    # statically quantize the large temporal embedding plus classifier heads.
    quantize_int8_onnx(
        fp32_path,
        int8_path,
        ArrayCalibrationReader(calibration_batches),
        nodes_to_quantize=("/embedding/Gemm", "/classifier/Gemm"),
    )

    evaluation_paths = [sample.audio_path for sample in evaluation]
    actual = np.asarray([MOBILE_LABELS.index(sample.label) for sample in evaluation], dtype=np.int64)
    fp32_logits = _batched_logits(fp32_path, evaluation_paths, args.batch_size)
    int8_logits = _batched_logits(int8_path, evaluation_paths, args.batch_size)
    parity = assess_quantization_parity(fp32_logits, int8_logits, actual)
    require_mobile_candidate_gate(parity)
    report = {
        "schema_version": "vaakmitra-mobile-student-quantization-2",
        "requirements": ["DEC-028", "DEC-029", "MST-005", "MST-011", "MST-012", "MST-014"],
        "architecture_version": "raw-wave-temporal8-dc-rms-v1",
        "int8_nodes": ["/embedding/Gemm", "/classifier/Gemm"],
        "evaluation_kind": "adult_public_engineering_only",
        "evaluation_samples": len(evaluation),
        "calibration_samples_used": int(len(indices)),
        "fp32": {"sha256": _hash(fp32_path), "bytes": fp32_path.stat().st_size},
        "int8": {"sha256": _hash(int8_path), "bytes": int8_path.stat().st_size},
        **parity.to_dict(),
        "accepted_for_android_engineering_integration": True,
        "approved_for_child_scoring": False,
    }
    (args.output_dir / "quantization-parity.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
