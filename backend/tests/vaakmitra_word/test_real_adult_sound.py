"""DEC073/PHN014: learned evidence never changes raw recognition or grants scoring."""
import copy
import numpy as np
from app.vaakmitra_word.real_adult_sound import difference_proposal,extract_evidence,feature_names,apply_gate

TOKENS=['<blank>','a','aː','m','p','s','[UNK]']
def frames(ids,tokens=TOKENS):
    p=np.full((len(ids),len(tokens)),.0001)
    for i,j in enumerate(ids):p[i,j]=1-(len(tokens)-1)*.0001
    return p
def model():
    n=len(feature_names(TOKENS))
    return {'schema':'vaakmitra.real_adult_sound.v1','feature_names':feature_names(TOKENS),
            'tokens':TOKENS,'mean':[0.]*n,'scale':[1.]*n,'weights':[0.]*n,'bias':2.,'threshold':.8,
            'approved_for_child_scoring':False,'clinical_assessment':False}

def test_phn014_single_missing_sound_and_ambiguous_geminate_positions_keep_identity():
    result=difference_proposal(['a','m','m','aː'],['a','m','aː'])
    assert result['kind']=='possible_omission' and result['expected_sounds']==['m']
    assert result['alternative_sounds']==[]

def test_phn014_doubled_vowels_are_not_consonant_omissions():
    for vowel in ['a','aː','e','eː','i','iː','o','oː','u','uː']:
        assert difference_proposal([vowel,vowel,'m'],['m']) is None

def test_phn014_repeated_substitution_requires_consonants_on_both_sides():
    for expected,alternative in [('a','i'),('m','a'),('a','m'),('[UNK]','m'),('m','unknown')]:
        assert difference_proposal([expected,expected,'p'],[alternative,alternative,'p']) is None

def test_phn014_single_vowel_difference_remains_available():
    assert difference_proposal(['a','m'],['i','m'])['kind']=='possible_substitution'
    assert difference_proposal(['a','m'],['m'])['kind']=='possible_omission'

def test_phn014_supported_double_consonant_omission_remains_one_identity():
    value=difference_proposal(['t̪','t̪','a'],['a'])
    assert value['expected_sounds']==['t̪'] and value['repeated_group']


def test_phn014_two_distinct_missing_sounds_cannot_be_a_specific_single_sound():
    assert difference_proposal(['m','a','p','aː'],['p','aː']) is None

def test_phn014_repeated_consonant_substitution_is_one_sound_identity():
    result=difference_proposal(['a','m','m','aː'],['a','p','p','aː'])
    assert result['kind']=='possible_substitution' and result['expected_sounds']==['m']
    assert result['alternative_sounds']==['p']

def test_phn014_insertion_and_multiple_distinct_substitutions_abstain():
    assert difference_proposal(['m','a'],['m','a','s']) is None
    assert difference_proposal(['m','a'],['s','aː']) is None

def test_phn014_accepted_variant_is_never_a_sound_difference():
    p=frames([5,5,0,1,1])
    result=extract_evidence(p,TOKENS,['m','a'],['s','a'],accepted_variants=[['s','a']])
    assert result['status']=='sequence_supported'

def test_phn014_compound_greedy_path_matches_canonical_free_output():
    tokens=['<blank>','k','a','j','aj','m','[UNK]']
    result=extract_evidence(frames([1,1,0,4,4],tokens),tokens,['m','a','j'],['k','a','j'])
    assert result['status']=='proposal' and result['expected_sounds']==['m']

def test_phn014_unknown_probability_tie_abstains():
    p=np.zeros((2,7));p[:,1]=.5;p[:,6]=.5
    assert extract_evidence(p,TOKENS,['m'],['a'])['status']=='insufficient_evidence'

def test_phn014_greedy_beam_disagreement_abstains_instead_of_forcing_reference():
    result=extract_evidence(frames([1,1,0,3,3,0,1,1]),TOKENS,['a','p','a'],['a','s','a'])
    assert result['status']=='insufficient_evidence'

def test_phn014_features_finite_and_owned_probability_buffer_unchanged():
    p=frames([1,1,0,5,5,0,1,1]);before=p.copy()
    result=extract_evidence(p,TOKENS,['a','m','a'],['a','s','a'])
    assert result['status']=='proposal' and len(result['features'])==len(feature_names(TOKENS))
    assert np.isfinite(result['features']).all()
    np.testing.assert_array_equal(p,before)

def test_phn014_learned_threshold_keeps_unconfirmed_kind_and_sound_identity():
    evidence=extract_evidence(frames([1,1,0,5,5,0,1,1]),TOKENS,['a','m','a'],['a','s','a'])
    result=apply_gate(evidence,model())
    assert result['status']=='possible_substitution' and result['expected_sounds']==['m']
    assert result['alternative_sounds']==['s'] and result['confirmed'] is False
    data=model();data['threshold']=.99
    assert apply_gate(evidence,data)['status']=='insufficient_evidence'

def test_phn014_bad_learned_schema_numbers_and_feature_order_fail_closed():
    evidence=extract_evidence(frames([1,1,0,5,5,0,1,1]),TOKENS,['a','m','a'],['a','s','a'])
    for key,value in [('schema','unknown'),('bias',float('nan')),('threshold',-1),('approved_for_child_scoring',True)]:
        data=model();data[key]=value;assert apply_gate(evidence,data)['status']=='invalid_model'
    data=model();data['scale'][0]=0;assert apply_gate(evidence,data)['status']=='invalid_model'
    data=model();data['feature_names'].reverse();assert apply_gate(evidence,data)['status']=='invalid_model'

def test_phn014_equal_sequence_has_no_inferred_sound_even_with_positive_model():
    evidence=extract_evidence(frames([3,3,0,1,1]),TOKENS,['m','a'],['m','a'])
    assert apply_gate(evidence,model())['status']=='sequence_supported'

def test_phn014_invalid_silence_and_unsupported_sh_never_become_omission():
    for p in [np.zeros((2,7)),np.full((2,7),float('nan')),frames([0]*6)]:
        assert extract_evidence(p,TOKENS,['m'],['a'])['status']=='insufficient_evidence'
    assert extract_evidence(frames([5]*6),TOKENS,['ʃ'],['s'])['status']=='unsupported_reference'

def test_phn014_unqualified_sound_pair_abstains_even_with_high_global_confidence():
    evidence=extract_evidence(frames([1,1,0,5,5,0,1,1]),TOKENS,['a','m','a'],['a','s','a'])
    data=model();data['pair_thresholds']=[{'kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['p'],'threshold':.5}]
    assert apply_gate(evidence,data)['status']=='insufficient_evidence'

def test_phn014_pair_cutoff_overrides_global_and_malformed_pair_table_fails_closed():
    evidence=extract_evidence(frames([1,1,0,5,5,0,1,1]),TOKENS,['a','m','a'],['a','s','a'])
    data=model();pair={'kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['s'],'threshold':.95}
    data['pair_thresholds']=[pair]
    assert apply_gate(evidence,data)['status']=='insufficient_evidence'
    pair['threshold']=.85;assert apply_gate(evidence,data)['status']=='possible_substitution'
    data['pair_thresholds']=[pair,pair];assert apply_gate(evidence,data)['status']=='invalid_model'
