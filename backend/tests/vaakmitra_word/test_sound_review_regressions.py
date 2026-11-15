"""DEC077/PHN018: final-review regressions, witnessed before the fix pass."""
import numpy as np
import pytest
from app.vaakmitra_word.contextual_sound import extract_contextual_evidence,feature_names,apply_contextual_gate
from app.vaakmitra_word.local_lattice_sound import extract_lattice_evidence,lattice_feature_names,apply_lattice_gate
from app.vaakmitra_word import local_lattice_sound as lattice_module
TOKENS=['<blank>','a','m','p','k','s','j','aj','[UNK]'];BODY='b'*64
def frames(ids):
    p=np.full((len(ids),len(TOKENS)),.0001)
    for i,j in enumerate(ids):p[i,j]=1-(len(TOKENS)-1)*.0001
    return p
def setup(mode):
    extract,names,gate,schema=(extract_contextual_evidence,feature_names,apply_contextual_gate,'vaakmitra.contextual_sound.v1') if mode=='context' else (extract_lattice_evidence,lattice_feature_names,apply_lattice_gate,getattr(lattice_module,'MODEL_SCHEMA','vaakmitra.local_lattice.v1'))
    e=extract(frames([1,1,0,3,3,0,1,1]),TOKENS,['a','m','a'],['a','p','a'],'complete_utterance',body_id=BODY)
    n=len(names(TOKENS))
    m={'schema':schema,'reference_policy':'partial_keyword_v2','body_id':BODY,'tokens':TOKENS,'feature_names':names(TOKENS),
       'mean':[0.]*n,'scale':[1.]*n,'w1':np.zeros((16,n)).tolist(),'b1':[0.]*16,'w2':[0.]*16,'b2':10.,'threshold':.5,
       'trained_scopes':['complete_utterance'],'trained_contrasts':[{'scope':'complete_utterance','kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['p']}],
       'approved_for_child_scoring':False,'clinical_assessment':False}
    return extract,gate,e,m

@pytest.mark.parametrize('mode',['context','lattice'])
def test_exact_keyword_cannot_match_only_half_a_native_compound(mode):
    extract,*_=setup(mode)
    result=extract(frames([7,7]),TOKENS,['a'],['a','j'],'keyword',body_id=BODY)
    assert result['status']=='compound_boundary_uncertain'
    assert extract(frames([7,7]),TOKENS,['a','j'],['a','j'],'keyword',body_id=BODY)['status']=='sequence_supported'

@pytest.mark.parametrize('mode',['context','lattice'])
def test_unvalidated_positive_status_never_passes_through_gate(mode):
    _,gate,_,_=setup(mode)
    assert gate({'status':'possible_substitution'},None)['status']=='invalid_evidence'
    assert gate({'status':'PASS'},None)['status']=='invalid_evidence'

@pytest.mark.parametrize('mode',['context','lattice'])
@pytest.mark.parametrize('location',['standardization','first_affine','last_affine'])
def test_finite_parameters_that_overflow_cannot_create_confidence(mode,location):
    _,gate,e,m=setup(mode);n=len(e['features'])
    e['features']=[2.]*n
    if location=='standardization':m['mean']=[-1e308]*n;m['scale']=[1e-308]*n
    elif location=='first_affine':m['w1']=np.full((16,n),1e308).tolist()
    else:m['b1']=[1e308]*16;m['w2']=[1e308]*16
    assert gate(e,m)['status']=='invalid_model'

def test_distinct_equal_reference_strings_keep_their_placements():
    from app.vaakmitra_word.local_lattice_sound import select_reference_placements
    seq=('a','m','a','m','a')
    rows=[{'start':0,'end':2,'reference':('a','m','a'),'expected_full':seq},
          {'start':2,'end':4,'reference':('a','m','a'),'expected_full':seq}]
    assert len(select_reference_placements(rows,{seq:-4.})['placements'])==2
    rows.append({'start':1,'end':3,'reference':('a','m','a'),'expected_full':seq})
    assert select_reference_placements(rows,{seq:-4.})['status']=='boundary_uncertain'

def test_pair_features_use_winning_alternative_reference_and_export_global_guard_separately():
    raw=['a','p','a','k','a','p','a'];ref=['a','m','a']
    p=frames([1,1,0,3,3,0,1,1,0,4,4,0,1,1,0,3,3,0,1,1])
    first=('a','m','a','k','a','p','a');second=('a','p','a','k','a','m','a');alternative=('a','p','a','k','a','j','a')
    table={first:-4.,second:-4.5,alternative:-1.,tuple(raw):-2.}
    def score(lp,paths,blank):
        result=[]
        for path in paths:
            if 7 in path:result.append(-1000.);continue
            result.append(table.get(tuple(TOKENS[i] for i in path),-30.))
        return result
    e=extract_lattice_evidence(p,TOKENS,ref,raw,'keyword',body_id=BODY,score_paths=score)
    assert e['status']=='proposal' and tuple(e['expected_full'])==second
    assert e['reference_log_probability']==-4.5 and e['global_reference_log_probability']==-4.
    assert tuple(e['global_reference_full'])==first
    assert e['features'][lattice_feature_names(TOKENS).index('reference_per_phone')]==-4.5/len(second)

def test_interior_metadata_is_independent_of_keyword_length_cap():
    from app.vaakmitra_word.reference_boundaries import is_interior_difference
    actual=['a','m']*8;reference=actual.copy();reference[7]='p'
    assert is_interior_difference(reference,actual)
    reference=actual.copy();reference[0]='p'
    assert not is_interior_difference(reference,actual)

