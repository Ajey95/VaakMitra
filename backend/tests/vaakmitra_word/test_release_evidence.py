"""DATA-002..006/012: missing provenance must block validation and coverage."""
import json
import subprocess
import sys
from pathlib import Path

import pytest


def approved(rows, *, human_approved=True, source_hash='a' * 64):
    return {'dataset_manifest_hash': source_hash, 'human_approved': human_approved,
        'approvals': [{'sample_id': row['sample_id'], 'audio_sha256': row['audio_sha256'],
                       'approved': True, 'reviewer_id': 'qualified-human-1',
                       'review_provenance': 'qualified_human', 'reviewer_qualified': True,
                       'capture_valid': True,
                       'quality_score': 0.9} for row in rows if 'sample_id' in row]}


def child(identifier, split):
    return {'speaker_role': 'child', 'speaker_pseudonym': identifier, 'split': split,
        'clinical_consent_verified': True, 'ethics_approval_id': 'synthetic-ethics',
        'age_years': 9, 'canonical_word_id': 'TA_WORD_0001', 'audio_sha256': identifier * 64,
        'derivation_review_verified': True, 'near_duplicate_review_verified': True,
        'ratings': [{'rater_id': 'R1', 'qualified': True, 'provenance': 'human', 'label': 'target'},
                    {'rater_id': 'R2', 'qualified': True, 'provenance': 'human', 'label': 'target'}]}


def test_data006_ai_labels_are_not_qualified_human_validation():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    rows = [child('a', 'calibration'), child('b', 'evaluation')]
    rows[0]['ratings'][0]['provenance'] = 'ai'
    result = audit_child_validation(rows)
    assert result['ready_for_validation'] is False
    assert result['blocking_counts']['two_qualified_human_raters_required'] == 1


def test_data004_child_cannot_cross_splits_even_with_different_files():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    result = audit_child_validation([child('a', 'calibration'), child('a', 'evaluation')])
    assert result['ready_for_validation'] is False
    assert result['blocking_counts']['child_split_leakage'] == 1


def test_data002_missing_consent_and_adjudication_block():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    rows = [child('a', 'calibration'), child('b', 'evaluation')]
    rows[0]['clinical_consent_verified'] = False
    rows[1]['ratings'][1]['label'] = 'other'
    result = audit_child_validation(rows)
    assert result['blocking_counts']['clinical_consent_unverified'] == 1
    assert result['blocking_counts']['adjudication_required'] == 1


def test_preflight_does_not_claim_clinical_approval_when_metadata_complete():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    result = audit_child_validation([child('a', 'calibration'), child('b', 'evaluation')])
    assert result['ready_for_validation'] is True
    assert result['clinical_approved'] is False


def test_dtw005_coverage_counts_distinct_speakers_not_repeated_clips():
    from app.vaakmitra_word.release_evidence import audit_vocabulary_coverage
    rows = [{'canonical_word_id': 'TA_WORD_0001', 'split': 'train',
             'speaker_pseudonym': 'adult1', 'audio_sha256': str(i)} for i in range(64)]
    report = audit_vocabulary_coverage([{'word_id': 'TA_WORD_0001', 'canonical_tamil': 'அம்மா'},
                                       {'word_id': 'TA_WORD_0002', 'canonical_tamil': 'அப்பா'}], rows)
    assert report['words'][0]['speaker_capped_train_references'] == 4
    assert report['words'][0]['count_coverage_ready'] is False
    assert report['words'][1]['available_clips'] == 0
    assert report['production_active_words'] == 0


def test_data012_train_inventory_is_not_an_accepted_reference_bank():
    from app.vaakmitra_word.release_evidence import audit_vocabulary_coverage
    rows = [{'canonical_word_id': 'W', 'label_kind': 'target', 'split': 'train',
             'speaker_pseudonym': f'adult{i // 4}', 'audio_sha256': f'{i:064x}'} for i in range(32)]
    report = audit_vocabulary_coverage([{'word_id': 'W', 'canonical_tamil': 'அம்மா'}], rows)
    word = report['words'][0]
    assert word['available_clips'] == 32
    assert word['raw_count_prerequisites_met'] is False
    assert word['eligible_reference_clips'] == 0
    assert word['count_coverage_ready'] is False
    assert report['production_active_words'] == 0


def test_dtw007_reference_count_requires_target_valid_capture_and_human_approval():
    from app.vaakmitra_word.release_evidence import audit_vocabulary_coverage
    rows = [{'sample_id': f's{i}', 'canonical_word_id': 'W', 'label_kind': 'target',
             'split': 'reference', 'speaker_pseudonym': f'adult{i // 4}',
             'audio_sha256': f'{i:064x}'} for i in range(32)]
    approvals = approved(rows)
    approvals['approvals'][0]['capture_valid'] = False
    rows[1]['label_kind'] = 'other'
    approvals['approvals'][2]['review_provenance'] = 'machine_assisted'
    report = audit_vocabulary_coverage([{'word_id': 'W', 'canonical_tamil': 'அம்மா'}], rows,
        approvals=approvals, corpus_sha256='a' * 64)
    assert report['words'][0]['eligible_reference_clips'] == 29
    assert report['words'][0]['count_coverage_ready'] is False
    assert report['words'][0]['human_review_verified'] is False


def test_dtw007_reference_checksum_leaking_into_training_is_not_eligible():
    from app.vaakmitra_word.release_evidence import audit_vocabulary_coverage
    rows = [{'sample_id': f's{i}', 'canonical_word_id': 'W', 'label_kind': 'target',
             'split': 'reference', 'speaker_pseudonym': f'adult{i // 4}',
             'audio_sha256': f'{i:064x}'} for i in range(32)]
    approvals = approved(rows)
    rows += [{'canonical_word_id': 'W', 'split': 'train',
              'speaker_pseudonym': 'other', 'audio_sha256': rows[0]['audio_sha256']},
             {'canonical_word_id': 'W', 'split': 'calibration'},
             {'canonical_word_id': 'W', 'split': 'evaluation'}]
    word = audit_vocabulary_coverage([{'word_id': 'W', 'canonical_tamil': 'அம்மா'}], rows,
        approvals=approvals, corpus_sha256='a' * 64)['words'][0]
    assert word['eligible_reference_clips'] == 31
    assert word['count_coverage_ready'] is False


def test_data012_explicitly_approved_train_references_can_meet_balanced_coverage():
    from app.vaakmitra_word.release_evidence import audit_vocabulary_coverage
    rows = [{'sample_id': f's{i}', 'canonical_word_id': 'W', 'label_kind': 'target',
             'split': 'train', 'speaker_pseudonym': f'adult{i // 4}',
             'audio_sha256': f'{i:064x}'} for i in range(32)]
    approvals = approved(rows)
    rows += [{'canonical_word_id': 'W', 'split': 'calibration'},
             {'canonical_word_id': 'W', 'split': 'evaluation'}]
    word = audit_vocabulary_coverage([{'word_id': 'W', 'canonical_tamil': 'அம்மா'}], rows,
        approvals=approvals, corpus_sha256='a' * 64)['words'][0]
    assert word['eligible_reference_clips'] == 32
    assert word['count_coverage_ready'] is True
    assert word['human_review_verified'] is True


def test_data012_reference_human_review_is_separate_from_heldout_availability():
    from app.vaakmitra_word.release_evidence import audit_vocabulary_coverage
    rows = [{'sample_id': f's{i}', 'canonical_word_id': 'W', 'label_kind': 'target',
             'split': 'reference', 'speaker_pseudonym': f'adult{i // 4}',
             'audio_sha256': f'{i:064x}'} for i in range(32)]
    word = audit_vocabulary_coverage([{'word_id': 'W', 'canonical_tamil': 'அம்மா'}], rows,
        approvals=approved(rows), corpus_sha256='a' * 64)['words'][0]
    assert word['human_review_verified'] is True
    assert word['count_coverage_ready'] is False


def test_data012_machine_approval_and_unbound_approval_do_not_count():
    from app.vaakmitra_word.release_evidence import audit_vocabulary_coverage
    rows = [{'sample_id': 's1', 'canonical_word_id': 'W', 'label_kind': 'target',
             'split': 'reference', 'speaker_pseudonym': 'adult1', 'audio_sha256': '1' * 64}]
    entries = [{'word_id': 'W', 'canonical_tamil': 'அம்மா'}]
    machine = approved(rows, human_approved=False)
    assert audit_vocabulary_coverage(entries, rows, approvals=machine,
        corpus_sha256='a' * 64)['words'][0]['eligible_reference_clips'] == 0
    machine['human_approved'] = True
    machine['approvals'][0]['audio_sha256'] = '2' * 64
    assert audit_vocabulary_coverage(entries, rows, approvals=machine,
        corpus_sha256='a' * 64)['words'][0]['eligible_reference_clips'] == 0
    with pytest.raises(ValueError, match='approval_manifest_source_mismatch'):
        audit_vocabulary_coverage(entries, rows, approvals=approved(rows),
            corpus_sha256='b' * 64)


def test_data012_audit_cli_rejects_approval_manifest_for_other_corpus(tmp_path):
    backend_root = Path(__file__).resolve().parents[2]
    corpus = tmp_path / 'corpus.jsonl'
    corpus.write_text(json.dumps({'schema_version': 'vaakmitra-corpus-record-1',
        'sample_id': 'adult-1', 'source_id': 'synthetic-source', 'source_revision': 'v1',
        'original_id': 'source-1', 'speaker_pseudonym': 'adult-1',
        'canonical_word_id': 'TA_WORD_0001', 'label_kind': 'target',
        'audio_path': 'synthetic.wav', 'audio_sha256': '1' * 64,
        'duration_seconds': 1.0, 'split': 'train', 'licence_id': 'synthetic'}), encoding='utf-8')
    owned = tmp_path / 'owned.jsonl'
    owned.write_text('', encoding='utf-8')
    approvals_path = tmp_path / 'approvals.json'
    approvals_path.write_text(json.dumps({'dataset_manifest_hash': '0' * 64,
        'human_approved': False, 'approvals': []}), encoding='utf-8')
    output = tmp_path / 'audit'
    result = subprocess.run([sys.executable, 'scripts/model/audit_release_evidence.py',
        '--corpus', str(corpus), '--owned-labels', str(owned),
        '--approval-manifest', str(approvals_path), '--output', str(output)],
        cwd=backend_root, capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert 'approval_manifest_source_mismatch' in result.stderr
    assert not output.exists()


@pytest.mark.parametrize('group_field,reason', [
    ('parent_sample_id', 'parent_split_leakage'),
    ('parent_id', 'parent_split_leakage'),
    ('deduplication_group', 'deduplication_split_leakage'),
    ('near_duplicate_group', 'deduplication_split_leakage'),
    ('household_group', 'household_split_leakage'),
])
def test_data003_independent_children_sharing_derived_or_duplicate_group_are_not_ready(group_field, reason):
    from app.vaakmitra_word.release_evidence import audit_child_validation
    rows = [child('a', 'calibration'), child('b', 'evaluation')]
    for row in rows:
        row[group_field] = 'shared'
    result = audit_child_validation(rows)
    assert result['ready_for_validation'] is False
    assert result['blocking_counts'][reason] == 1


def test_data003_missing_derivation_and_near_duplicate_review_is_unverified():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    rows = [child('a', 'calibration'), child('b', 'evaluation')]
    for row in rows:
        del row['derivation_review_verified']
        del row['near_duplicate_review_verified']
    result = audit_child_validation(rows)
    assert result['ready_for_validation'] is False
    assert result['blocking_counts']['derivation_review_unverified'] == 2
    assert result['blocking_counts']['near_duplicate_review_unverified'] == 2
    assert result['clinical_approved'] is False


def test_data003_original_sample_and_derived_parent_cannot_cross_splits():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    rows = [child('a', 'calibration'), child('b', 'evaluation')]
    rows[0]['sample_id'] = 'original'
    rows[1]['sample_id'] = 'derived'
    rows[1]['parent_sample_id'] = 'original'
    result = audit_child_validation(rows)
    assert result['ready_for_validation'] is False
    assert result['blocking_counts']['parent_split_leakage'] == 1


def test_data003_multi_hop_and_parent_aliases_share_one_split_lineage():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    rows = [child('a', 'calibration'), child('b', 'calibration'), child('c', 'evaluation')]
    rows[0]['sample_id'] = 'original'
    rows[1]['sample_id'] = 'derived-1'
    rows[1]['parent_id'] = 'original'
    rows[2]['sample_id'] = 'derived-2'
    rows[2]['parent_sample_id'] = 'derived-1'
    result = audit_child_validation(rows)
    assert result['blocking_counts']['parent_split_leakage'] == 1


def test_data003_distinct_complete_lineages_are_not_split_leakage():
    from app.vaakmitra_word.release_evidence import audit_child_validation
    rows = [child('a', 'calibration'), child('b', 'evaluation')]
    rows[0].update(sample_id='first-derived', parent_id='first-original')
    rows[1].update(sample_id='second-derived', parent_sample_id='second-original')
    result = audit_child_validation(rows)
    assert result['ready_for_validation'] is True
    assert 'parent_split_leakage' not in result['blocking_counts']
