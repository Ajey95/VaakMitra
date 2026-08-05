"""Prepare speaker-disjoint local indices from the public Tamil TTS manifests."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from modeling.data.corpus_manifest import CorpusManifest, CorpusSplit


@dataclass(frozen=True, slots=True)
class _SourceRecord:
    rel_path: str
    phonemes: str
    speaker: str


@dataclass(frozen=True, slots=True)
class ProxyCorpusPreparationResult:
    manifest: CorpusManifest
    manifest_path: Path
    audit_report: Path
    train_index: Path
    validation_index: Path
    test_index: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _read_source_csv(path: Path) -> tuple[_SourceRecord, ...]:
    if not path.is_file():
        raise ValueError(f"source manifest is missing: {path.name}")
    records: list[_SourceRecord] = []
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source, delimiter="|")
        required = {"rel_path", "text", "phonemes", "speaker"}
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path.name} must contain rel_path, text, phonemes, and speaker")
        for line_number, row in enumerate(reader, start=2):
            rel_path = (row.get("rel_path") or "").strip()
            phonemes = (row.get("phonemes") or "").strip()
            speaker = (row.get("speaker") or "").strip()
            if not rel_path:
                raise ValueError(f"{path.name}:{line_number} requires non-empty rel_path")
            parsed_path = PurePosixPath(rel_path)
            if parsed_path.is_absolute() or ".." in parsed_path.parts:
                raise ValueError(f"{path.name}:{line_number} contains unsafe rel_path")
            if not phonemes:
                raise ValueError(f"{path.name}:{line_number} requires non-empty phonemes")
            if not speaker:
                raise ValueError(f"{path.name}:{line_number} requires non-empty speaker")
            records.append(_SourceRecord(rel_path, phonemes, speaker))
    if not records:
        raise ValueError(f"{path.name} must contain at least one record")
    return tuple(records)


def _write_index(
    path: Path,
    records: Sequence[_SourceRecord],
    *,
    dataset_id: str,
    revision: str,
) -> str:
    lines: list[str] = []
    for record in sorted(records, key=lambda item: (item.speaker, item.rel_path)):
        record_id = hashlib.sha256(
            f"{dataset_id}@{revision}:{record.rel_path}".encode()
        ).hexdigest()
        lines.append(
            json.dumps(
                {
                    "audio_rel_path": record.rel_path,
                    "phonemes": record.phonemes,
                    "record_id": record_id,
                    "speaker": record.speaker,
                },
                ensure_ascii=False,
                separators=(",", ":"),
                sort_keys=True,
            )
        )
    path.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))
    return _sha256(path)


def _stable_speaker_order(speakers: set[str], seed: str) -> list[str]:
    return sorted(
        speakers,
        key=lambda speaker: hashlib.sha256(f"{seed}:{speaker}".encode()).hexdigest(),
    )


def prepare_tamil_tts_proxy(
    *,
    source_dir: str | Path,
    output_dir: str | Path,
    dataset_id: str,
    revision: str,
    source_url: str,
    license_spdx: str,
    validation_speaker_fraction: float = 0.2,
    split_seed: str = "vaakmitra-member2-v1",
) -> ProxyCorpusPreparationResult:
    """Build deterministic local indices while preventing speaker leakage."""

    if (
        not math.isfinite(validation_speaker_fraction)
        or not 0.0 < validation_speaker_fraction < 1.0
    ):
        raise ValueError("validation_speaker_fraction must be between zero and one")
    if not split_seed.strip():
        raise ValueError("split_seed must be non-empty")

    source = Path(source_dir)
    source_paths = {
        "train": source / "train.csv",
        "validation": source / "val.csv",
        "test": source / "test.csv",
    }
    source_records = {name: _read_source_csv(path) for name, path in source_paths.items()}
    all_records = tuple(record for records in source_records.values() for record in records)
    rel_paths = [record.rel_path for record in all_records]
    if len(rel_paths) != len(set(rel_paths)):
        raise ValueError("source rel_path values must be unique across all splits")

    development_records = (*source_records["train"], *source_records["validation"])
    development_speakers = {record.speaker for record in development_records}
    test_speakers = {record.speaker for record in source_records["test"]}
    test_overlap = development_speakers.intersection(test_speakers)
    if test_overlap:
        raise ValueError("source test speakers overlap development speakers")
    if len(development_speakers) < 2:
        raise ValueError("at least two development speakers are required for a disjoint split")

    ordered_speakers = _stable_speaker_order(development_speakers, split_seed)
    validation_count = max(
        1,
        min(len(ordered_speakers) - 1, round(len(ordered_speakers) * validation_speaker_fraction)),
    )
    validation_speakers = set(ordered_speakers[:validation_count])
    train_speakers = development_speakers - validation_speakers
    derived_records = {
        "train": tuple(
            record for record in development_records if record.speaker in train_speakers
        ),
        "validation": tuple(
            record for record in development_records if record.speaker in validation_speakers
        ),
        "test": source_records["test"],
    }

    output = Path(output_dir)
    output_paths = {
        "train": output / "train.index.jsonl",
        "validation": output / "validation.index.jsonl",
        "test": output / "test.index.jsonl",
    }
    manifest_path = output / "corpus.manifest.json"
    audit_path = output / "source-audit.json"
    if any(path.exists() for path in (*output_paths.values(), manifest_path, audit_path)):
        raise ValueError("prepared corpus output exists; use a clean output directory")
    output.mkdir(parents=True, exist_ok=True)

    index_hashes = {
        name: _write_index(
            output_paths[name],
            records,
            dataset_id=dataset_id,
            revision=revision,
        )
        for name, records in derived_records.items()
    }
    manifest = CorpusManifest(
        schema_version="1.0",
        dataset_id=dataset_id,
        revision=revision,
        source_url=source_url,
        license_spdx=license_spdx,
        population="adult_tamil_proxy",
        label_origin="dataset_supplied_phonemes",
        evidence_scope="engineering_proxy",
        local_processing_only=True,
        splits=tuple(
            CorpusSplit(
                name=name,  # type: ignore[arg-type]
                speakers=tuple(sorted({record.speaker for record in derived_records[name]})),
                record_count=len(derived_records[name]),
                index_sha256=index_hashes[name],
            )
            for name in ("train", "validation", "test")
        ),
    )
    manifest_path.write_bytes(
        (json.dumps(manifest.model_dump(mode="json"), indent=2) + "\n").encode("utf-8")
    )

    source_train_speakers = {record.speaker for record in source_records["train"]}
    source_validation_speakers = {
        record.speaker for record in source_records["validation"]
    }
    audit = {
        "schema_version": "1.0",
        "dataset_id": dataset_id,
        "revision": revision,
        "source_url": source_url,
        "license_spdx": license_spdx,
        "evidence_scope": "engineering_proxy",
        "source_splits": {
            name: {
                "csv_sha256": _sha256(source_paths[name]),
                "record_count": len(source_records[name]),
                "speaker_count": len({record.speaker for record in source_records[name]}),
            }
            for name in ("train", "validation", "test")
        },
        "source_train_validation_speaker_overlap": len(
            source_train_speakers.intersection(source_validation_speakers)
        ),
        "source_test_development_speaker_overlap": len(test_overlap),
        "split_seed": split_seed,
        "validation_speaker_fraction": validation_speaker_fraction,
        "derived_speaker_disjoint": True,
        "derived_splits": {
            name: {
                "record_count": len(derived_records[name]),
                "speaker_count": len({record.speaker for record in derived_records[name]}),
                "index_sha256": index_hashes[name],
            }
            for name in ("train", "validation", "test")
        },
        "limitations": [
            "adult speech is not target-user child speech",
            "dataset phonemes are not therapist pronunciation ratings",
        ],
    }
    audit_path.write_bytes((json.dumps(audit, indent=2) + "\n").encode("utf-8"))
    return ProxyCorpusPreparationResult(
        manifest=manifest,
        manifest_path=manifest_path,
        audit_report=audit_path,
        train_index=output_paths["train"],
        validation_index=output_paths["validation"],
        test_index=output_paths["test"],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Prepare speaker-disjoint local indices from Tamil TTS CSV manifests."
    )
    parser.add_argument("--source-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--dataset-id", default="asishbala/tamil-tts-dataset")
    parser.add_argument("--revision", required=True)
    parser.add_argument(
        "--source-url",
        default="https://huggingface.co/datasets/asishbala/tamil-tts-dataset",
    )
    parser.add_argument("--license-spdx", default="CC0-1.0")
    parser.add_argument("--validation-speaker-fraction", type=float, default=0.2)
    parser.add_argument("--split-seed", default="vaakmitra-member2-v1")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = prepare_tamil_tts_proxy(
        source_dir=args.source_dir,
        output_dir=args.output_dir,
        dataset_id=args.dataset_id,
        revision=args.revision,
        source_url=args.source_url,
        license_spdx=args.license_spdx,
        validation_speaker_fraction=args.validation_speaker_fraction,
        split_seed=args.split_seed,
    )
    print(
        json.dumps(
            {
                "manifest": str(result.manifest_path),
                "audit_report": str(result.audit_report),
                "manifest_digest": result.manifest.digest(),
                "total_records": result.manifest.total_records,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

