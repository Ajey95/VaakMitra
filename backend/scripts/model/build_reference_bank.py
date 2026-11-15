"""Build a balanced adult reference bank from approved embedding records."""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.corpus import CorpusRecord  # noqa: E402
from app.vaakmitra_word.embedding_store import load_embedding_shard  # noqa: E402
from app.vaakmitra_word.model import sha256_file  # noqa: E402
from app.vaakmitra_word.reference_builder import (  # noqa: E402
    ReferenceCandidate,
    save_reference_bank_artifact,
    select_balanced_references,
)
from app.vaakmitra_word.review_exports import verify_review_export  # noqa: E402


def validate_approval_manifest(
    payload: dict,
    source_records: dict[str, CorpusRecord],
    source_hash: str,
) -> dict[str, dict]:
    """GOV-003/DATA-008: accept only exact-source, qualified human approvals."""
    signing_key = os.environ.get("VAAKMITRA_REVIEW_SIGNING_KEY", "")
    if not signing_key:
        raise RuntimeError("approval_signing_key_missing")
    if not verify_review_export(payload, signing_key):
        raise RuntimeError("approval_manifest_signature_invalid")
    if payload.get("schema_version") != "vaakmitra-reference-approvals-1":
        raise RuntimeError("approval_manifest_schema_invalid")
    if payload.get("dataset_manifest_hash") != source_hash:
        raise RuntimeError("approval_manifest_source_mismatch")
    if payload.get("human_approved") is not True:
        raise RuntimeError("approval_manifest_human_review_required")
    rows = payload.get("approvals")
    if not isinstance(rows, list):
        raise RuntimeError("approval_manifest_rows_invalid")
    seen: set[str] = set()
    approved_audio: set[str] = set()
    audio_splits: dict[str, set[str]] = defaultdict(set)
    audio_words: dict[str, set[str | None]] = defaultdict(set)
    for row in source_records.values():
        audio_splits[row.audio_sha256].add(row.split)
        audio_words[row.audio_sha256].add(row.canonical_word_id)
    approved: dict[str, dict] = {}
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("sample_id"), str):
            raise RuntimeError("approval_manifest_row_invalid")
        sample_id = item["sample_id"]
        if sample_id in seen:
            raise RuntimeError("approval_sample_duplicate")
        seen.add(sample_id)
        source = source_records.get(sample_id)
        if source is None:
            raise RuntimeError("approval_sample_unknown")
        if item.get("approved") is not True:
            continue
        if source.label_kind != "target" or source.split not in {"train", "reference"}:
            raise RuntimeError("approval_source_ineligible")
        if item.get("audio_sha256") != source.audio_sha256:
            raise RuntimeError("approval_audio_hash_mismatch")
        if len(audio_splits[source.audio_sha256]) != 1 or "evaluation" in audio_splits[source.audio_sha256] or "calibration" in audio_splits[source.audio_sha256] or "canary" in audio_splits[source.audio_sha256]:
            raise RuntimeError("approval_audio_cross_split")
        if len(audio_words[source.audio_sha256]) != 1:
            raise RuntimeError("approval_audio_cross_word")
        if source.audio_sha256 in approved_audio:
            raise RuntimeError("approval_audio_duplicate")
        approved_audio.add(source.audio_sha256)
        if item.get("canonical_word_id") != source.canonical_word_id:
            raise RuntimeError("approval_word_mismatch")
        if item.get("capture_valid") is not True:
            raise RuntimeError("approval_capture_invalid")
        if (item.get("review_provenance") != "qualified_human"
                or item.get("reviewer_qualified") is not True
                or not str(item.get("reviewer_id", "")).strip()):
            raise RuntimeError("approval_qualified_human_required")
        quality = item.get("quality_score")
        if type(quality) not in (int, float) or not math.isfinite(quality) or not 0 <= quality <= 1:
            raise RuntimeError("approval_quality_invalid")
        approved[sample_id] = item
    return approved


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--embedding-root", type=Path, required=True)
    parser.add_argument("--source-manifest", type=Path, required=True)
    parser.add_argument("--approval-manifest", type=Path, required=True)
    parser.add_argument("--model-sha256", required=True)
    parser.add_argument("--vocabulary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--version", default="adult-reference-v1")
    args = parser.parse_args()

    source_hash = sha256_file(args.source_manifest)
    vocabulary_hash = sha256_file(args.vocabulary)
    approvals_payload = json.loads(args.approval_manifest.read_text(encoding="utf-8"))
    sources: dict[str, CorpusRecord] = {}
    with args.source_manifest.open("r", encoding="utf-8") as source:
        for line in source:
            if line.strip():
                record = CorpusRecord.model_validate_json(line)
                if record.sample_id in sources:
                    raise RuntimeError("source_sample_duplicate")
                sources[record.sample_id] = record
    approvals = validate_approval_manifest(approvals_payload, sources, source_hash)

    grouped: dict[str, list[ReferenceCandidate]] = defaultdict(list)
    for shard_path in sorted(args.embedding_root.glob("shard-*.npz")):
        shard = load_embedding_shard(
            shard_path,
            model_hash=args.model_sha256.lower(),
            vocabulary_hash=vocabulary_hash,
            source_manifest_hash=source_hash,
        )
        for item in shard.items:
            if item.canonical_word_id is None or item.split not in {"train", "reference"}:
                continue
            approval = approvals.get(item.sample_id)
            grouped[item.canonical_word_id].append(
                ReferenceCandidate(
                    sample_id=item.sample_id,
                    word_id=item.canonical_word_id,
                    speaker_pseudonym=item.speaker_pseudonym,
                    source_id=sources[item.sample_id].source_id if item.sample_id in sources else "unknown",
                    quality_score=float(approval.get("quality_score", 0.0)) if approval else 0.0,
                    approved=approval is not None,
                    embedding=item.embedding,
                )
            )

    selections = {
        word_id: select_balanced_references(candidates)
        for word_id, candidates in sorted(grouped.items())
    }
    report = {
        "schema_version": "vaakmitra-reference-bank-report-1",
        "model_hash": args.model_sha256.lower(),
        "vocabulary_hash": vocabulary_hash,
        "dataset_manifest_hash": source_hash,
        "approval_manifest_hash": sha256_file(args.approval_manifest),
        "active_words": [word_id for word_id, selection in selections.items() if selection.active],
        "words": {
            word_id: {
                "active": selection.active,
                "selected_references": len(selection.selected),
                "distinct_speakers": len(
                    {candidate.speaker_pseudonym for candidate in selection.selected}
                ),
                "sources": sorted({candidate.source_id for candidate in selection.selected}),
                "reasons": list(selection.reasons),
            }
            for word_id, selection in selections.items()
        },
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if not report["active_words"]:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
        return 2
    save_reference_bank_artifact(
        args.output,
        selections=selections,
        version=args.version,
        model_hash=args.model_sha256.lower(),
        vocabulary_hash=vocabulary_hash,
        dataset_manifest_hash=source_hash,
    )
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
