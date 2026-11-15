"""Inventory and conservatively transcribe owner-provided WAV recordings locally."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.audio import decode_wav_bytes, validate_audio  # noqa: E402
from app.vaakmitra_word.model import (  # noqa: E402
    ModelCapabilityError,
    NeMoIndicConformerAdapter,
)
from app.vaakmitra_word.owned_recordings import classify_recording_name  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--authorization-id", required=True)
    args = parser.parse_args()

    root = args.input_root.resolve()
    audio_paths = sorted(root.rglob("*.wav"), key=lambda path: path.relative_to(root).as_posix())
    if not audio_paths:
        raise RuntimeError("owned_recordings_empty")
    if args.output.exists():
        raise FileExistsError(args.output)

    model = NeMoIndicConformerAdapter(
        model_path=args.model,
        expected_sha256=args.model_sha256,
        device=args.device,
    )
    model.load()
    records: list[dict[str, object]] = []
    for audio_path in audio_paths:
        relative_path = audio_path.relative_to(root).as_posix()
        audio_bytes = audio_path.read_bytes()
        decoded = decode_wav_bytes(audio_bytes)
        quality = validate_audio(decoded.samples, decoded.sample_rate)
        label = classify_recording_name(audio_path.name)
        transcript: str | None = None
        inference_error: str | None = None
        try:
            evidence = model.infer(decoded.samples, decoded.sample_rate, "")
            if evidence.candidates:
                transcript = evidence.candidates[0].word or None
        except ModelCapabilityError as exc:
            inference_error = str(exc).split(":", 1)[0]
        records.append(
            {
                "schema_version": "vaakmitra-owned-recording-label-1",
                "sample_id": "owned-" + hashlib.sha256(relative_path.encode("utf-8")).hexdigest()[:24],
                "relative_path": relative_path,
                "audio_sha256": hashlib.sha256(audio_bytes).hexdigest(),
                "duration_seconds": decoded.duration_s,
                "sample_rate": decoded.sample_rate,
                "quality": quality.model_dump(mode="json"),
                **asdict(label),
                "model_transcript": transcript,
                "model_inference_error": inference_error,
                "authorization_id": args.authorization_id,
                "owner_use_authorized": True,
                "clinical_consent_verified": False,
                "review_status": "machine_assisted_needs_therapist_review",
            }
        )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8") as sink:
        for record in records:
            sink.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    summary = {
        "output": str(args.output),
        "records": len(records),
        "adult_therapist": sum(record["speaker_role"] == "adult_therapist" for record in records),
        "child": sum(record["speaker_role"] == "child" for record in records),
        "environment": sum(record["speaker_role"] == "environment" for record in records),
        "reference_eligible": sum(bool(record["reference_eligible"]) for record in records),
    }
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
