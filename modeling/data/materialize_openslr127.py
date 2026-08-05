"""Safely materialize OpenSLR-127 and emit privacy-safe frozen evidence."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Sequence
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from modeling.data.archive_safety import extract_validated_archive, inspect_tar_archive
from modeling.data.corpus_index import (
    CorpusSource,
    SplitName,
    freeze_corpus_index,
    write_frozen_corpus_index,
)
from modeling.data.openslr127 import (
    assign_speakers,
    deduplicate_audio_records,
    inspect_extracted_corpus,
)

_SPLIT_NAMES: tuple[SplitName, ...] = ("train", "validation", "test")


def _validate_retrieval_time(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("retrieved_at must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError("retrieved_at must be expressed in UTC")
    return parsed.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _refuse_existing_outputs(
    *,
    extraction_root: Path,
    private_output_dir: Path,
    public_paths: Sequence[Path],
    allow_nonempty_extraction: bool = False,
) -> None:
    if (
        not allow_nonempty_extraction
        and extraction_root.exists()
        and any(extraction_root.iterdir())
    ):
        raise ValueError("extraction destination must be empty")
    if private_output_dir.exists() and any(private_output_dir.iterdir()):
        raise ValueError("private output directory must be empty")
    existing = [path for path in public_paths if path.exists()]
    if existing:
        raise FileExistsError("one or more materialization outputs already exist")


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8", newline="\n") as output:
        json.dump(payload, output, ensure_ascii=False, indent=2)
        output.write("\n")


def run_materialization(
    *,
    archive_path: Path,
    extraction_root: Path,
    private_output_dir: Path,
    aggregate_report_path: Path,
    frozen_index_path: Path,
    source_manifest_path: Path,
    source_url: str,
    retrieved_at: str,
    reuse_complete_extraction: bool = False,
    expected_record_count: int | None = None,
    hash_workers: int = 1,
) -> dict[str, Any]:
    """Inspect, safely extract, validate, split, and freeze one archive snapshot."""

    if not archive_path.is_file():
        raise ValueError("archive_path must be a complete local file")
    if expected_record_count is not None and expected_record_count <= 0:
        raise ValueError("expected_record_count must be positive")
    retrieval_time = _validate_retrieval_time(retrieved_at)
    _refuse_existing_outputs(
        extraction_root=extraction_root,
        private_output_dir=private_output_dir,
        public_paths=(aggregate_report_path, frozen_index_path, source_manifest_path),
        allow_nonempty_extraction=reuse_complete_extraction,
    )
    archive = inspect_tar_archive(archive_path, extraction_root)
    if reuse_complete_extraction:
        if not extraction_root.is_dir() or not any(extraction_root.iterdir()):
            raise ValueError("reused extraction destination must be non-empty")
    else:
        extract_validated_archive(archive_path, extraction_root, archive)
    inspection = inspect_extracted_corpus(
        extraction_root,
        archive_sha256=archive.archive_sha256,
        hash_workers=hash_workers,
    )
    if not inspection.records:
        raise ValueError("corpus contains no accepted records")
    if expected_record_count is not None:
        if inspection.report.accepted_count != expected_record_count:
            raise ValueError(
                f"expected exactly {expected_record_count} accepted records"
            )
        if inspection.report.rejections:
            raise ValueError("expected zero corpus-record rejections")
    deduplication = deduplicate_audio_records(inspection.records)
    training_records = deduplication.eligible_records
    if not training_records:
        raise ValueError("corpus contains no leakage-safe training records")
    assignments = assign_speakers(
        tuple((record.speaker_id, record.official_split) for record in training_records)
    )
    source = CorpusSource.model_validate(
        {
            "dataset_id": "openslr-127-iisc-mile-tamil",
            "revision": archive.archive_sha256,
            "revision_basis": "archive_sha256",
            "source_url": source_url,
            "license_spdx": "CC-BY-2.0",
            "population": "adult_tamil_proxy",
            "local_processing_only": True,
        }
    )
    frozen = freeze_corpus_index(
        tuple(record.corpus_record() for record in training_records),
        assignments.assignments,
        source,
    )
    split_counts = Counter(
        assignments.assignments[record.speaker_id] for record in training_records
    )
    aggregate: dict[str, Any] = {
        "schema_version": "1.0",
        "dataset_id": source.dataset_id,
        "source_url": str(source.source_url),
        "license_spdx": source.license_spdx,
        "retrieved_at": retrieval_time,
        "archive_sha256": archive.archive_sha256,
        "archive_size_bytes": archive_path.stat().st_size,
        "archive_member_count": archive.member_count,
        "archive_file_count": archive.file_count,
        "archive_uncompressed_file_bytes": archive.total_file_bytes,
        "tar_integrity_and_path_safety": "passed",
        "accepted_count": inspection.report.accepted_count,
        "accepted_speaker_count": inspection.report.accepted_speaker_count,
        "training_eligible_count": len(training_records),
        "training_eligible_speaker_count": len(
            {record.speaker_id for record in training_records}
        ),
        "exact_audio_duplicate_group_count": deduplication.duplicate_group_count,
        "exact_audio_duplicate_record_count": deduplication.duplicate_record_count,
        "safe_duplicate_group_count": deduplication.safe_collapsed_group_count,
        "cross_speaker_duplicate_group_count": (
            deduplication.cross_speaker_group_count
        ),
        "conflicting_transcript_duplicate_group_count": (
            deduplication.conflicting_transcript_group_count
        ),
        "excluded_duplicate_record_count": deduplication.excluded_record_count,
        "total_duration_ms": inspection.report.total_duration_ms,
        "official_train_count": inspection.report.official_train_count,
        "official_test_count": inspection.report.official_test_count,
        "rejections": inspection.report.rejections,
        "split_policy": assignments.policy_version,
        "official_speaker_overlap_count": assignments.official_overlap_count,
        "split_record_counts": {
            split: split_counts.get(split, 0)
            for split in _SPLIT_NAMES
        },
        "split_speaker_counts": assignments.model_dump()["split_speaker_counts"],
        "corpus_index_sha256": frozen.digest(),
        "contains_paths": False,
        "contains_transcripts": False,
        "contains_identifiers": False,
        "local_archive_checksum_is_publisher_supplied": False,
        "evidence_scope": "engineering_proxy",
    }

    private_output_dir.mkdir(parents=True, exist_ok=True)
    records_path = private_output_dir / "records.jsonl"
    with records_path.open("x", encoding="utf-8", newline="\n") as output:
        for record in training_records:
            private_row = {
                **record.corpus_record().model_dump(mode="json"),
                "official_split": record.official_split,
                "audio_rel_path": record.audio_path.relative_to(extraction_root).as_posix(),
                "transcript_rel_path": record.transcript_path.relative_to(
                    extraction_root
                ).as_posix(),
            }
            output.write(json.dumps(private_row, ensure_ascii=False, sort_keys=True) + "\n")
    _write_json(
        private_output_dir / "speaker-assignments.json", assignments.assignments
    )
    _write_json(source_manifest_path, source.model_dump(mode="json"))
    write_frozen_corpus_index(frozen_index_path, frozen)
    _write_json(aggregate_report_path, aggregate)
    return aggregate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Safely materialize and freeze OpenSLR-127 Tamil corpus evidence."
    )
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--extract-root", required=True, type=Path)
    parser.add_argument("--private-output-dir", required=True, type=Path)
    parser.add_argument("--aggregate-report", required=True, type=Path)
    parser.add_argument("--frozen-index", required=True, type=Path)
    parser.add_argument("--source-manifest", required=True, type=Path)
    parser.add_argument("--source-url", required=True)
    parser.add_argument("--retrieved-at", required=True)
    parser.add_argument("--reuse-complete-extraction", action="store_true")
    parser.add_argument("--expected-record-count", type=int)
    parser.add_argument("--hash-workers", type=int, default=1)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    result = run_materialization(
        archive_path=args.archive,
        extraction_root=args.extract_root,
        private_output_dir=args.private_output_dir,
        aggregate_report_path=args.aggregate_report,
        frozen_index_path=args.frozen_index,
        source_manifest_path=args.source_manifest,
        source_url=args.source_url,
        retrieved_at=args.retrieved_at,
        reuse_complete_extraction=args.reuse_complete_extraction,
        expected_record_count=args.expected_record_count,
        hash_workers=args.hash_workers,
    )
    print(json.dumps(result, ensure_ascii=True, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
