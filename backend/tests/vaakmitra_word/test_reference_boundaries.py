"""DEC077/PHN018: partial references never erase raw speech or license edge errors."""
import numpy as np
import pytest
from app.vaakmitra_word.reference_boundaries import build_reference_record,free_unit_spans,word_windows,lexical_neighbors

TOKENS=['<blank>','a','m','p','k','s','j','aj','[UNK]']
def posterior(ids):
    p=np.full((len(ids),len(TOKENS)),.0001)
    for i,j in enumerate(ids):p[i,j]=1-(len(TOKENS)-1)*.0001
    return p

def test_keyword_reference_cannot_train_whole_clip_ctc():
    row={'sample_id':'x','source_id':'mlcommons-mswc-ta','provenance_kind':'original','transcript':'word'}
    result=build_reference_record(row,['a','m'])
    assert result['scope']=='keyword' and not result['eligible_for_whole_clip_ctc']
    assert result['intended_phones']==['a','m']

def test_machine_word_boundary_is_not_verified():
    result=build_reference_record({'sample_id':'x','source_id':'openslr-127-mile-ta','provenance_kind':'segmented','transcript':'word'},['a'])
    assert result['scope']=='keyword' and result['boundary_provenance']=='machine_alignment'
    assert not result['eligible_for_whole_clip_ctc']

def test_review_actual_does_not_replace_intended():
    row={'sample_id':'x','source_id':'mlcommons-mswc-ta','provenance_kind':'original','transcript':'word'}
    review={'source_id':'x','owner_confirmed_free_tokens':True,'owner_confirmed_spoken_phones':['a','p']}
    result=build_reference_record(row,['a','m'],review)
    assert result['intended_phones']==['a','m'] and result['owner_reviewed_actual_phones']==['a','p']
    assert result['actual_provenance']=='owner_confirmed_existing_model_draft'
    assert row['sample_id']=='x'

def test_unknown_source_and_mismatched_review_fail_closed():
    result=build_reference_record({'sample_id':'x','transcript':'word'},['a'])
    assert result['scope']=='unverified' and not result['eligible_for_whole_clip_ctc']
    with pytest.raises(ValueError):
        build_reference_record({'sample_id':'x'},['a'],{'source_id':'other','owner_confirmed_free_tokens':True,'owner_confirmed_spoken_phones':['a']})

def test_keyword_extra_speech_is_neutral_supported():
    raw=['k','a','m','a','s']
    result=word_windows(['a','m','a'],raw,'keyword')
    assert result['status']=='sequence_supported' and result['raw_phones']==raw
    assert raw==['k','a','m','a','s']

def test_complete_scope_cannot_discard_context():
    result=word_windows(['a','m','a'],['k','a','m','a','s'],'complete_utterance')
    assert result['status']=='insufficient_evidence'

def test_interior_substitution_keeps_both_observed_context_sides():
    result=word_windows(['a','m','a'],['k','a','p','a','s'],'keyword')
    assert result['status']=='candidates'
    candidate=next(c for c in result['candidates'] if c['start']==1 and c['end']==4)
    assert candidate['expected_full']==['k','a','m','a','s']
    assert candidate['alternative_sounds']==['p'] and candidate['expected_sounds']==['m']

def test_interior_missing_consonant_does_not_become_two_different_sounds():
    result=word_windows(['a','m','m','a'],['k','a','m','a','s'],'keyword')
    assert result['status']=='candidates'
    assert any(c['kind']=='possible_omission' and c['expected_sounds']==['m'] for c in result['candidates'])

def test_keyword_edges_abstain_but_complete_reference_can_compare():
    assert word_windows(['m','a','p'],['a','p'],'keyword')['status']=='boundary_uncertain'
    assert word_windows(['m','a','p'],['a','p'],'complete_utterance')['status']=='candidates'
    assert word_windows(['a','m'],['a','p'],'keyword')['status']=='boundary_uncertain'

def test_repeated_vowels_not_one_geminate():
    assert word_windows(['a','a','m'],['m'],'complete_utterance')['status']=='insufficient_evidence'

def test_variant_exact_sequence_and_invalid_scope():
    assert word_windows(['a','m'],['a','p'],'keyword',accepted_variants=[['a','p']])['status']=='sequence_supported'
    assert word_windows(['a'],['a'],'unknown')['status']=='unsupported_scope'

def test_invalid_reference_and_variant_inputs_abstain_without_raising():
    assert word_windows(['a'],None,'keyword')['status']=='insufficient_evidence'
    assert word_windows(['a'],['a'],'keyword',accepted_variants=[None])['status']=='insufficient_evidence'

def test_complete_sentence_reference_limit_can_exceed_keyword_core_limit():
    ref=['a','m']*8
    assert word_windows(ref,ref,'complete_utterance')['status']=='sequence_supported'
    assert word_windows(ref,ref,'keyword')['status']=='insufficient_evidence'

def test_native_compound_has_shared_atomic_span():
    p=posterior([4,4,0,7,7])
    spans=free_unit_spans(p,TOKENS,['k','a','j'])
    assert spans is not None and len(spans)==3
    assert spans[1]['native_group']==spans[2]['native_group']
    assert spans[1]['start']==spans[2]['start'] and spans[1]['end']==spans[2]['end']

def test_free_alignment_preserves_buffer_and_repeated_native_events():
    p=posterior([1,1,0,2,2,0,2,2,0,1,1]);copy=p.copy()
    spans=free_unit_spans(p,TOKENS,['a','m','m','a'])
    assert spans[1]['end']<spans[2]['start'] and spans[1]['native_group']!=spans[2]['native_group']
    np.testing.assert_array_equal(p,copy)

def test_unknown_silence_and_nonfinite_inputs_have_no_spans():
    for p in [posterior([8,8]),posterior([0,0]),np.full((2,len(TOKENS)),np.nan)]:
        assert free_unit_spans(p,TOKENS,['a']) is None

def test_bounded_lexical_neighbors_find_only_real_one_sound_changes():
    lex={('a','m','a'),('a','p','a'),('a','m','m','a'),('a','k','p','a'),('a','a','a','a')}
    result=lexical_neighbors(['a','p','a'],lex,{'a','m','p','k'})
    pairs={tuple(r) for r in result}
    assert ('a','m','a') in pairs and ('a','k','p','a') in pairs
    assert ('a','m','m','a') not in pairs and ('a','a','a','a') not in pairs

def test_bounded_neighbor_lookup_keeps_double_consonant_exception_only():
    lex={('a','m','m','a'),('a','a','a','a')}
    assert lexical_neighbors(['a','a'],lex,{'a','m'})==[('a','m','m','a')]

