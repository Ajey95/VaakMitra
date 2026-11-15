"""Fit a non-clinical adult-only engineering evidence calibrator."""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.calibration_training import (  # noqa: E402
    CalibrationExample,
    CalibrationTrainingError,
    train_adult_engineering_calibration,
)
from app.vaakmitra_word.model import sha256_file  # noqa: E402


def _read_examples(path: Path) -> list[CalibrationExample]:
    examples: list[CalibrationExample] = []
    with path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            if not line.strip():
                continue
            payload = json.loads(line)
            if payload.get("population") != "adult":
                raise CalibrationTrainingError(f"non_adult_record:{line_number}")
            if type(payload.get("target_match")) is not bool:
                raise CalibrationTrainingError(f"target_match_not_boolean:{line_number}")
            examples.append(
                CalibrationExample(
                    sample_id=str(payload["sample_id"]),
                    speaker_pseudonym=str(payload["speaker_pseudonym"]),
                    word_id=str(payload["word_id"]),
                    split=str(payload["split"]),
                    target_match=payload["target_match"],
                    features=dict(payload["features"]),
                )
            )
    return examples


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--evidence-manifest", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--reference-bank", type=Path, required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--vad-config", type=Path)
    parser.add_argument("--live-pipeline-hash", type=str, default="")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)

    artifact, report = train_adult_engineering_calibration(
        _read_examples(args.evidence_manifest),
        model_hash=sha256_file(args.model),
        classifier_hash=sha256_file(args.classifier),
        reference_bank_hash=sha256_file(args.reference_bank),
        vocabulary_hash=sha256_file(args.vocabulary),
        dataset_manifest_hash=sha256_file(args.evidence_manifest),
        vad_config_hash=sha256_file(args.vad_config) if args.vad_config else "",
        live_pipeline_hash=args.live_pipeline_hash,
        seed=args.seed,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(artifact.model_dump_json(indent=2) + "\n", encoding="utf-8")
    payload = {
        "schema_version": "vaakmitra-adult-engineering-calibration-report-1",
        "non_clinical": True,
        "artifact_approved": False,
        "artifact_hashes": {
            "model": artifact.model_hash,
            "classifier": artifact.classifier_hash,
            "reference_bank": artifact.reference_bank_hash,
            "vocabulary": artifact.vocabulary_hash,
            "dataset_manifest": artifact.dataset_manifest_hash,
            "vad_config": artifact.vad_config_hash,
            "live_pipeline": artifact.live_pipeline_hash,
        },
        "seed": args.seed,
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
