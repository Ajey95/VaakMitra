"""DATA-002..006/012: metadata preflight, never a clinical approval authority."""
from collections import Counter, defaultdict


def audit_child_validation(records: list[dict]) -> dict:
    children = [r for r in records if r.get('speaker_role') == 'child']
    blockers = Counter()
    groups, audio_splits = defaultdict(set), defaultdict(set)
    duplicate_splits, household_splits = defaultdict(set), defaultdict(set)
    lineage_parent, lineage_splits = {}, defaultdict(set)

    def root(identifier):
        lineage_parent.setdefault(identifier, identifier)
        if lineage_parent[identifier] != identifier:
            lineage_parent[identifier] = root(lineage_parent[identifier])
        return lineage_parent[identifier]

    valid_labels = {'target', 'other', 'partial', 'capture_invalid', 'uncertain'}
    agreements = paired = 0
    for row in children:
        child, split = row.get('speaker_pseudonym'), row.get('split')
        if not child:
            blockers['child_pseudonym_required'] += 1
        else:
            groups[child].add(split)
        if split not in ('calibration', 'evaluation'):
            blockers['calibration_or_evaluation_split_required'] += 1
        digest = row.get('audio_sha256')
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in '0123456789abcdef' for c in digest):
            blockers['audio_checksum_required'] += 1
        else:
            audio_splits[digest].add(split)
        lineage = [row[key] for key in ('sample_id', 'parent_sample_id', 'parent_id')
                   if isinstance(row.get(key), str) and row[key]]
        if lineage:
            leader = root(lineage[0])
            for identifier in lineage:
                lineage_splits[identifier].add(split)
                lineage_parent[root(identifier)] = leader
        for key in ('deduplication_group', 'near_duplicate_group'):
            if row.get(key):
                duplicate_splits[row[key]].add(split)
        for key in ('household_pseudonym', 'household_group'):
            if row.get(key):
                household_splits[row[key]].add(split)
        if row.get('derivation_review_verified') is not True:
            blockers['derivation_review_unverified'] += 1
        if row.get('near_duplicate_review_verified') is not True:
            blockers['near_duplicate_review_unverified'] += 1
        if row.get('clinical_consent_verified') is not True:
            blockers['clinical_consent_unverified'] += 1
        if not row.get('ethics_approval_id'):
            blockers['ethics_approval_missing'] += 1
        age = row.get('age_years')
        if type(age) not in (int, float) or not 7 <= age <= 14:
            blockers['age_eligibility_unverified'] += 1
        if not row.get('canonical_word_id'):
            blockers['canonical_target_missing'] += 1
        ratings = [r for r in row.get('ratings', []) if r.get('qualified') is True
                   and r.get('provenance') == 'human' and r.get('rater_id')
                   and r.get('label') in valid_labels]
        if len({r['rater_id'] for r in ratings}) < 2:
            blockers['two_qualified_human_raters_required'] += 1
        else:
            paired += 1
            if len({r['label'] for r in ratings}) == 1:
                agreements += 1
            else:
                adjudication = row.get('adjudication') or {}
                if (adjudication.get('provenance') != 'human' or not adjudication.get('reviewer_id')
                        or adjudication.get('qualified') is not True or adjudication.get('label') not in valid_labels):
                    blockers['adjudication_required'] += 1
    linked_splits = defaultdict(set)
    for identifier, splits in lineage_splits.items():
        linked_splits[root(identifier)].update(splits)
    for name, mapping in (('child_split_leakage', groups), ('audio_split_leakage', audio_splits),
                          ('parent_split_leakage', linked_splits),
                          ('deduplication_split_leakage', duplicate_splits),
                          ('household_split_leakage', household_splits)):
        blockers[name] += sum(len(splits) > 1 for splits in mapping.values())
    if not children:
        blockers['child_recordings_missing'] += 1
    if not any('calibration' in s for s in groups.values()) or not any('evaluation' in s for s in groups.values()):
        blockers['independent_calibration_and_evaluation_children_required'] += 1
    if len(groups) < 2:
        blockers['multiple_independent_children_required'] += 1
    blockers = {key: value for key, value in sorted(blockers.items()) if value}
    return {'schema_version': 'vaakmitra-child-validation-preflight-1',
        'child_recordings': len(children), 'distinct_children': len(groups),
        'ready_for_validation': not blockers, 'clinical_approved': False,
        'blocking_counts': blockers, 'human_rated_pairs': paired,
        'raw_inter_rater_agreement': agreements / paired if paired else None,
        'scope': 'metadata_preflight_only_not_accuracy_or_consent_authentication'}


def audit_vocabulary_coverage(entries: list[dict], records: list[dict], *,
                              approvals: dict | None = None, corpus_sha256: str | None = None) -> dict:
    if approvals is not None and (not corpus_sha256
                                  or approvals.get('dataset_manifest_hash') != corpus_sha256):
        raise ValueError('approval_manifest_source_mismatch')
    approved_samples = {}
    if approvals is not None and approvals.get('human_approved') is True:
        for item in approvals.get('approvals', []):
            sample_id = item.get('sample_id')
            if (sample_id and item.get('approved') is True
                    and item.get('review_provenance') == 'qualified_human'
                    and item.get('reviewer_qualified') is True
                    and str(item.get('reviewer_id', '')).strip()
                    and item.get('capture_valid') is True
                    and isinstance(item.get('audio_sha256'), str)
                    and len(item['audio_sha256']) == 64):
                if sample_id in approved_samples:
                    raise ValueError('approval_sample_duplicate')
                approved_samples[sample_id] = item
    grouped = defaultdict(list)
    checksum_splits, checksum_words = defaultdict(set), defaultdict(set)
    for row in records:
        if row.get('canonical_word_id'):
            grouped[row['canonical_word_id']].append(row)
        if row.get('audio_sha256'):
            checksum_splits[row['audio_sha256']].add(row.get('split'))
            checksum_words[row['audio_sha256']].add(row.get('canonical_word_id'))
    words = []
    for entry in entries:
        rows = grouped[entry['word_id']]
        raw_seen, raw_speakers = set(), Counter()
        eligible_seen, eligible_speakers = set(), Counter()
        for row in rows:
            digest, speaker = row.get('audio_sha256'), row.get('speaker_pseudonym')
            if not digest or not speaker:
                continue
            if row.get('split') == 'train' and digest not in raw_seen:
                raw_seen.add(digest)
                raw_speakers[speaker] += 1
            approval = approved_samples.get(row.get('sample_id'))
            # DTW-001/007: corpus flags alone cannot authorize a reference.
            if (row.get('split') in ('train', 'reference') and row.get('label_kind') == 'target'
                    and approval is not None and approval['audio_sha256'] == digest
                    and digest not in eligible_seen
                    and checksum_splits[digest] == {row['split']} and len(checksum_words[digest]) == 1):
                eligible_seen.add(digest)
                eligible_speakers[speaker] += 1
        raw_capped = sum(min(4, n) for n in raw_speakers.values())
        splits = Counter(r.get('split') for r in rows)
        available = splits['calibration'] > 0 and splits['evaluation'] > 0
        raw_ready = raw_capped >= 32 and len(raw_speakers) >= 8 and available
        eligible_count = len(eligible_seen)
        selected_count = min(64, sum(min(4, n) for n in eligible_speakers.values()))
        reference_ready = selected_count >= 32 and len(eligible_speakers) >= 8
        count_ready = reference_ready and available
        words.append({'word_id': entry['word_id'], 'canonical_tamil': entry['canonical_tamil'],
            'available_clips': len(rows), 'split_counts': dict(splits),
            'train_speakers': len(raw_speakers), 'speaker_capped_train_references': min(64, raw_capped),
            'raw_count_prerequisites_met': raw_ready,
            'eligible_reference_clips': eligible_count, 'eligible_reference_speakers': len(eligible_speakers),
            'selected_reference_clips': selected_count,
            'additional_reference_clips_needed': max(0, 32 - selected_count),
            'additional_reference_speakers_needed': max(0, 8 - len(eligible_speakers)),
            'count_coverage_ready': count_ready, 'human_review_verified': reference_ready})
    return {'schema_version': 'vaakmitra-vocabulary-coverage-audit-1', 'words': words,
        'intended_words': len(entries), 'words_with_any_clip': sum(w['available_clips'] > 0 for w in words),
        'raw_count_prerequisite_words': sum(w['raw_count_prerequisites_met'] for w in words),
        'count_ready_words': sum(w['count_coverage_ready'] for w in words),
        'human_reviewed_reference_words': sum(w['human_review_verified'] for w in words),
        'production_active_words': 0, 'other_clips': sum(not r.get('canonical_word_id') for r in records),
        'human_review_verified': False, 'scope': 'inventory_not_audio_or_label_approval'}
