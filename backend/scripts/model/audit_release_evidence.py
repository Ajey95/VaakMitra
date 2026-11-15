"""Read local metadata only and emit explicit coverage and validation blockers."""
import argparse
import csv
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.vaakmitra_word.release_evidence import audit_child_validation, audit_vocabulary_coverage
from app.vaakmitra_word.corpus import CorpusRecord
from app.vaakmitra_word.model import sha256_file


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--corpus', type=Path, required=True)
    parser.add_argument('--owned-labels', type=Path, required=True)
    parser.add_argument('--approval-manifest', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('output_must_be_new')
    vocabulary = ROOT / 'data/vocabulary/ta-v1-intended.json'
    entries = json.loads(vocabulary.read_text(encoding='utf-8'))['entries']
    corpus = [CorpusRecord.model_validate_json(line).model_dump() for line in
              args.corpus.read_text(encoding='utf-8').splitlines() if line.strip()]
    owned = [json.loads(line) for line in args.owned_labels.read_text(encoding='utf-8').splitlines() if line]
    approvals = json.loads(args.approval_manifest.read_text(encoding='utf-8')) if args.approval_manifest else None
    coverage = audit_vocabulary_coverage(entries, corpus, approvals=approvals,
        corpus_sha256=sha256_file(args.corpus))
    child = audit_child_validation(owned)
    args.output.mkdir(parents=True)
    for name, report in (('vocabulary-coverage.json', coverage), ('child-validation-preflight.json', child)):
        (args.output / name).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with (args.output / 'adult-recording-requirements.csv').open('x', encoding='utf-8-sig', newline='') as file:
        fields = ['word_id', 'canonical_tamil', 'available_clips', 'train_speakers',
            'speaker_capped_train_references', 'additional_reference_clips_needed',
            'additional_reference_speakers_needed', 'raw_count_prerequisites_met',
            'eligible_reference_clips', 'eligible_reference_speakers',
            'count_coverage_ready', 'human_review_verified']
        writer = csv.DictWriter(file, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(coverage['words'])
    provenance = {'corpus_sha256': sha256_file(args.corpus), 'owned_labels_sha256': sha256_file(args.owned_labels),
                  'approval_manifest_sha256': sha256_file(args.approval_manifest) if args.approval_manifest else None,
                  'vocabulary_sha256': sha256_file(vocabulary), 'child_audio_read': False, 'clinical_approved': False}
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print(json.dumps({'coverage': {k: v for k, v in coverage.items() if k != 'words'}, 'child_validation': child}))


if __name__ == '__main__':
    main()
