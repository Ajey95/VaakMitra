"""DEC072/PHN013: acoustic hypotheses never manufacture the expected recognition."""
import itertools
import numpy as np
from app.vaakmitra_word.adult_sound_evidence import (
    ctc_log_probability, native_sequences, assess_sound_evidence, build_hypotheses,
)

TOKENS=['<blank>','a','i','m','p','s','[UNK]']


def frames(ids,tokens=TOKENS):
    p=np.full((len(ids),len(tokens)),.0001,dtype=np.float64)
    for i,j in enumerate(ids):p[i,j]=1-(len(tokens)-1)*.0001
    return p


def test_phn013_ctc_matches_exhaustive_path_probability():
    p=np.array([[.4,.4,.2],[.5,.2,.3],[.2,.4,.4]])
    probability=0.
    for path in itertools.product(range(3),repeat=3):
        collapsed=[x for i,x in enumerate(path) if x!=0 and (i==0 or x!=path[i-1])]
        if collapsed==[1,2]:probability+=np.prod([p[i,j] for i,j in enumerate(path)])
    assert abs(np.exp(ctc_log_probability(np.log(p),[1,2]))-probability)<1e-12
    assert abs(np.exp(ctc_log_probability(np.log(p),[]))-np.prod(p[:,0]))<1e-12


def test_phn013_compound_native_paths_are_equivalent_without_collapsing_geminates():
    units=['<blank>','k','a','j','aj','m']
    assert set(native_sequences(['k','a','j'],units))=={(1,2,3),(1,4)}
    assert native_sequences(['m','m'],units)==[(5,5)]


def test_phn013_hypotheses_include_group_substitution_and_deduplicate_deletions():
    rows=build_hypotheses(['a','m','m','a'],TOKENS)
    assert any(r['phones']==('a','p','p','a') and r['kind']=='possible_substitution' for r in rows)
    assert len([r for r in rows if r['phones']==('a','m','a')])==1


def test_phn013_clear_expected_sequence_has_support():
    result=assess_sound_evidence(frames([1,1,0,3,3,0,2,2]),TOKENS,['a','m','i'])
    assert result['status']=='sequence_supported'
    assert result['expected_sounds']==[]
    assert result['confirmed'] is False


def test_phn013_supported_omission_names_expected_sound_as_hypothesis():
    result=assess_sound_evidence(frames([1,1,0,0,2,2]),TOKENS,['a','m','i'])
    assert result['status']=='possible_omission'
    assert result['expected_sounds']==['m'] and result['confirmed'] is False


def test_phn013_supported_substitution_distinguishes_competing_sound():
    result=assess_sound_evidence(frames([1,1,0,5,5,0,2,2]),TOKENS,['a','m','i'])
    assert result['status']=='possible_substitution'
    assert result['expected_sounds']==['m'] and result['alternative_sounds']==['s']


def test_phn013_silence_unknown_and_uncertain_frames_abstain():
    assert assess_sound_evidence(frames([0]*8),TOKENS,['m'])['status']=='insufficient_evidence'
    assert assess_sound_evidence(frames([6]*8),TOKENS,['m'])['status']=='insufficient_evidence'
    assert assess_sound_evidence(np.full((8,7),1/7),TOKENS,['m'])['status']=='insufficient_evidence'


def test_phn013_unknown_probability_tie_abstains_regardless_of_vocabulary_order():
    for tokens in (['<blank>','a','m','[UNK]'],['<blank>','[UNK]','m','a']):
        p=np.zeros((2,4));p[:,tokens.index('a')]=.5;p[:,tokens.index('[UNK]')]=.5
        result=assess_sound_evidence(p,tokens,['m'],policy='strict')
        assert result['status']=='insufficient_evidence'
        assert result['expected_sounds']==[]


def test_phn013_unsupported_sh_is_not_relabelled():
    assert assess_sound_evidence(frames([5]*8),TOKENS,['ʃ'])['status']=='unsupported_reference'


def test_phn013_accepted_variant_is_not_a_substitution():
    result=assess_sound_evidence(frames([5,5,0,1,1]),TOKENS,['m','a'],accepted_variants=[['s','a']])
    assert result['status']=='sequence_supported'


def test_phn013_compound_mass_is_considered_for_correct_support():
    units=['<blank>','k','a','j','aj','m','[UNK]']
    result=assess_sound_evidence(frames([1,1,0,4,4],units),units,['k','a','j'])
    assert result['status']=='sequence_supported'


def test_phn013_input_probabilities_are_not_mutated():
    p=frames([1,1,0,3,3,0,2,2]);copy=p.copy()
    assess_sound_evidence(p,TOKENS,['a','m','i'])
    np.testing.assert_array_equal(p,copy)
