"""GOV-003..005: prepare metadata-only human review batches; never approve them."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.routers.governance import BatchInput, CLINICAL_SECTIONS, ReviewItemInput  # noqa: E402
from app.vaakmitra_word.canary import CanarySuite  # noqa: E402
from app.vaakmitra_word.corpus import CorpusRecord  # noqa: E402
from app.vaakmitra_word.model import sha256_file  # noqa: E402
from app.vaakmitra_word.review_exports import clinical_bundle_hash  # noqa: E402


def reference_batch_from_manifest(path: Path) -> dict:
    rows = []
    seen = set()
    with path.open("r", encoding="utf-8") as source:
        for line in source:
            if not line.strip():
                continue
            row = CorpusRecord.model_validate_json(line)
            if row.sample_id in seen:
                raise ValueError("source_sample_duplicate")
            seen.add(row.sample_id)
            if row.label_kind == "target" and row.split in {"train", "reference"}:
                rows.append(ReviewItemInput(item_id=row.sample_id,
                                            word_id=row.canonical_word_id,
                                            audio_sha256=row.audio_sha256))
    return BatchInput(kind="reference", manifest_sha256=sha256_file(path), items=rows).model_dump()


def canary_batch_from_suite(path: Path, forbidden_manifests: list[Path]) -> dict:
    suite = CanarySuite.model_validate_json(path.read_text(encoding="utf-8"))
    if suite.human_approved:
        raise ValueError("canary_candidate_must_be_unapproved")
    forbidden = set()
    for manifest in forbidden_manifests:
        with manifest.open("r", encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    row = json.loads(line)
                    identifier = row.get("sample_id") or row.get("source_sample_id")
                    if identifier:
                        forbidden.add(str(identifier))
    return BatchInput(
        kind="canary", manifest_sha256=sha256_file(path),
        active_words=list(suite.positive_words), forbidden_sample_ids=sorted(forbidden),
        items=[ReviewItemInput(
            item_id=row.canary_id, word_id=row.word_id,
            audio_sha256=row.audio_sha256, source_sample_id=row.source_sample_id,
            category=row.category, expected_decision=row.expected_decision,
        ) for row in suite.records],
    ).model_dump()


def clinical_batch_from_manifest(path: Path, root: Path, child_id: str) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    sections = payload.get("sections")
    if not isinstance(sections, dict) or set(sections) != CLINICAL_SECTIONS:
        raise ValueError("clinical_sections_incomplete")
    resolved_root = root.resolve()
    hashes = {}
    for name, relative in sections.items():
        if not isinstance(relative, str) or not relative:
            raise ValueError("clinical_section_path_invalid")
        candidate = Path(relative)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ValueError("clinical_section_path_invalid")
        file_path = (resolved_root / candidate).resolve()
        try:
            file_path.relative_to(resolved_root)
        except ValueError as exc:
            raise ValueError("clinical_section_outside_root") from exc
        if not file_path.is_file():
            raise ValueError("clinical_section_missing")
        hashes[name] = sha256_file(file_path)
    content_hash = clinical_bundle_hash(hashes)
    return BatchInput(
        kind="clinical", manifest_sha256=sha256_file(path), child_id=child_id,
        clinical_sections=hashes,
        items=[ReviewItemInput(item_id="content-bundle", content_sha256=content_hash)],
    ).model_dump()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kind", choices=("reference", "canary", "clinical"), required=True)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--forbidden-manifest", type=Path, action="append", default=[])
    parser.add_argument("--clinical-root", type=Path)
    parser.add_argument("--child-id")
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.kind == "reference":
        packet = reference_batch_from_manifest(args.input)
    elif args.kind == "canary":
        packet = canary_batch_from_suite(args.input, args.forbidden_manifest)
    else:
        if not args.clinical_root or not args.child_id:
            parser.error("clinical batches require --clinical-root and --child-id")
        packet = clinical_batch_from_manifest(args.input, args.clinical_root, args.child_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(packet, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"kind": args.kind, "items": len(packet["items"]), "approved": False,
                      "source_sha256": packet["manifest_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
