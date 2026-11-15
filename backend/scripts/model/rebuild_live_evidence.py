"""DEC-015/DATA-008: immutable, adult-only evidence through the actual live service.

The original adult evaluation partition is explicitly repurposed here because
the installed classifier already used the original calibration speakers to fit
temperature. Old adult evaluation metrics are no longer untouched holdout claims.
Child recordings are never accepted or read by this tool.
"""
import argparse
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from app.vaakmitra_word.assessment import AssessmentContext
from app.vaakmitra_word.calibration_training import CalibrationExample, train_adult_engineering_calibration
from app.vaakmitra_word.corpus import CorpusRecord, SourceRegistry, validate_jsonl_manifest
from app.vaakmitra_word.diagnostic_runtime import EngineeringConfig, load_engineering
from app.vaakmitra_word.live_evidence import extract_attempt, partition_calibration_speakers, pipeline_fingerprint
from app.vaakmitra_word.model import sha256_file
from app.vaakmitra_word.policy import TherapistConstraints


def build_context(identity, target, canonical):
    return AssessmentContext(session_id='ADULT-BUILD', attempt_id=identity, word_id=target,
        target_word=canonical, attempt_count=0,
        therapist_constraints=TherapistConstraints(allowed_actions=('safe_end',), next_exercise_id=target))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--source-manifest', type=Path, required=True)
    parser.add_argument('--audio-root', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError('output_must_be_new')
    config = EngineeringConfig.model_validate_json(args.config.read_text())
    if config.vad_config is None:
        raise ValueError('executable_vad_config_required')
    source_registry = SourceRegistry.from_json(ROOT / 'data/corpus/source_registry.json')
    validate_jsonl_manifest(args.source_manifest)
    records = [CorpusRecord.model_validate_json(line).model_dump() for line in
               args.source_manifest.read_text(encoding='utf-8').splitlines() if line.strip()]
    # This build is deliberately narrow: only the already authorized adult corpus.
    for row in records:
        if row['source_id'] != 'openslr-127-mile-ta':
            raise ValueError('authorized_adult_source_required')
        source = source_registry.require_ingestible(row['source_id'])
        if row['licence_id'] != source.licence_id or row['source_revision'] != source.source_revision:
            raise ValueError('source_provenance_mismatch')
    partitions = partition_calibration_speakers(records, source_split='evaluation')
    selected = [r for r in records if r['speaker_pseudonym'] in partitions]
    root = args.audio_root.resolve()
    forbidden_hashes = {r['audio_sha256'] for r in records if r['split'] != 'evaluation'}
    seen_hashes = set()
    for row in selected:
        path = (root / row['audio_path']).resolve()
        if not path.is_relative_to(root):
            raise ValueError('audio_path_outside_root')
        if row['audio_sha256'] in forbidden_hashes or row['audio_sha256'] in seen_hashes:
            raise ValueError('duplicate_or_cross_split_audio')
        seen_hashes.add(row['audio_sha256'])
        if sha256_file(path) != row['audio_sha256']:
            raise ValueError('audio_integrity_mismatch')
    os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_DATASETS_OFFLINE='1')
    service, words, versions = load_engineering(args.config)
    fingerprint = pipeline_fingerprint()
    args.output.mkdir(parents=True)
    provenance = {'schema_version': 'vaakmitra-live-evidence-build-1', 'approved': False,
        'population': 'adult_only_engineering', 'source_manifest_hash': sha256_file(args.source_manifest),
        'live_pipeline_hash': fingerprint, 'runtime_config_hash': sha256_file(args.config),
        'source_partition': 'evaluation_repurposed_not_untouched_final_test',
        'label_provenance': 'machine_assisted_not_human_approved',
        'speaker_partitions': partitions, 'runtime_versions': versions,
        'artifacts': config.model_dump(mode='json'),
        'scoring_ready': False}
    (args.output / 'provenance.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    labels = sorted(words)
    examples, failures = [], []
    with (args.output / 'evidence.jsonl').open('x', encoding='utf-8') as out:
        for index, row in enumerate(sorted(selected, key=lambda r: r['sample_id'])):
            correct = row.get('canonical_word_id')
            target_ids = [correct] if correct in words else []
            wrong = [w for w in labels if w != correct]
            target_ids.append(wrong[int(sha256(row['sample_id'].encode()).hexdigest(), 16) % len(wrong)])
            audio = (root / row['audio_path']).read_bytes()
            for target in target_ids:
                identity = f"{row['sample_id']}:{target}"
                result = extract_attempt(service, audio, build_context(identity, target, words[target]),
                    expected_sha256=row['audio_sha256'])
                payload = {'sample_id': identity, 'source_sample_id': row['sample_id'],
                    'audio_sha256': row['audio_sha256'], 'speaker_pseudonym': row['speaker_pseudonym'],
                    'word_id': target, 'split': partitions[row['speaker_pseudonym']],
                    'target_match': target == correct, 'population': 'adult', **result}
                out.write(json.dumps(payload, sort_keys=True) + '\n')
                out.flush()
                if result['quality_valid'] and result['evidence_available']:
                    examples.append(CalibrationExample(identity, row['speaker_pseudonym'], target,
                        payload['split'], payload['target_match'], result['features']))
                else:
                    failures.append({'sample_id': identity, 'reason': result['reason_code']})
            if index % 25 == 0:
                print(json.dumps({'processed_audio': index + 1, 'total_audio': len(selected),
                    'usable_attempts': len(examples), 'rejected_attempts': len(failures)}), flush=True)
    if pipeline_fingerprint() != fingerprint:
        raise ValueError('pipeline_changed_during_build')
    artifact, report = train_adult_engineering_calibration(examples,
        model_hash=config.model.sha256, classifier_hash=config.classifier.sha256,
        reference_bank_hash=config.reference_bank.sha256, vocabulary_hash=config.vocabulary.sha256,
        dataset_manifest_hash=sha256_file(args.output / 'evidence.jsonl'),
        vad_config_hash=config.vad_config.sha256, live_pipeline_hash=fingerprint)
    (args.output / 'calibration.json').write_text(artifact.model_dump_json(indent=2), encoding='utf-8')
    final = {**asdict(report), 'live_pipeline_hash': fingerprint, 'rejected_attempts': failures,
        'metric_scope': 'adult_engineering_ungated_operating_point_not_child_or_release_performance',
        'calibration_hash': sha256_file(args.output / 'calibration.json'),
        'source_audio_count': len(selected), 'usable_attempt_count': len(examples),
        'scoring_ready': False, 'human_approved': False}
    (args.output / 'report.json').write_text(json.dumps(final, indent=2), encoding='utf-8')
    print(json.dumps({'completed': True, 'usable_attempts': len(examples),
        'calibration_hash': final['calibration_hash'], 'approved': False}), flush=True)


if __name__ == '__main__':
    main()
