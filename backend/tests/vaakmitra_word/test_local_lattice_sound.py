"""DEC077/PHN018: alternative acoustic hypotheses remain distinct from raw tokens."""
import numpy as np
from app.vaakmitra_word.local_lattice_sound import extract_lattice_evidence,lattice_feature_names,apply_lattice_gate,MODEL_SCHEMA
TOKENS=['<blank>','a','m','p','k','s','j','aj','[UNK]'];BODY='b'*64
def frames(ids):
    p=np.full((len(ids),len(TOKENS)),.0001)
    for i,j in enumerate(ids):p[i,j]=1-(len(TOKENS)-1)*.0001
    return p
def evidence():
    p=frames([1,1,0,3,3,0,1,1,0,4,4,0,1,1])
    return extract_lattice_evidence(p,TOKENS,['a','m','a','k','a'],['a','p','a','s','a'],'complete_utterance',body_id=BODY)

def test_lattice_can_resolve_sound_without_raw_core_being_one_edit():
    e=evidence()
    assert e['status']=='proposal' and e['kind']=='possible_substitution'
    assert e['expected_sounds']==['m'] and e['alternative_sounds']==['p']
    assert e['raw_phones']==['a','p','a','s','a']
    assert e['alternative_hypothesis']==['a','p','a','k','a']
    assert len(e['features'])==len(lattice_feature_names(TOKENS)) and np.isfinite(e['features']).all()

def test_exact_keyword_with_context_remains_neutral():
    p=frames([4,4,0,1,1,0,2,2,0,1,1,0,5,5])
    assert extract_lattice_evidence(p,TOKENS,['a','m','a'],['k','a','m','a','s'],'keyword',body_id=BODY)['status']=='sequence_supported'

def test_complete_reference_detects_missing_interior_sound():
    p=frames([1,1,0,1,1])
    e=extract_lattice_evidence(p,TOKENS,['a','m','a'],['a','a'],'complete_utterance',body_id=BODY)
    assert e['status']=='proposal' and e['kind']=='possible_omission' and e['expected_sounds']==['m']

def test_keyword_edges_not_diagnosed():
    e=extract_lattice_evidence(frames([1,1,0,3,3]),TOKENS,['a','m'],['a','p'],'keyword',body_id=BODY)
    assert e['status']!='proposal'

def test_equal_alternative_sound_scores_abstain():
    p=frames([1,1,0,3,3,0,1,1])
    for i in [3,4]:p[i,:]=.0001;p[i,3]=p[i,5]=(1-.0001*(len(TOKENS)-2))/2
    e=extract_lattice_evidence(p,TOKENS,['a','m','a'],['a','p','a'],'complete_utterance',body_id=BODY)
    assert e['status']!='proposal' and not e['expected_sounds']

def test_unknowns_and_owned_buffers_are_preserved():
    p=frames([1,1,0,3,3,0,1,1]);copy=p.copy()
    extract_lattice_evidence(p,TOKENS,['a','m','a'],['a','p','a'],'complete_utterance',body_id=BODY)
    np.testing.assert_array_equal(p,copy)
    p[:]=0;p[:,1]=.5;p[:,-1]=.5
    assert extract_lattice_evidence(p,TOKENS,['a','m','a'],['a','p','a'],'complete_utterance',body_id=BODY)['status']=='insufficient_evidence'

def test_lattice_model_cannot_accept_previous_scoring_schema():
    e=evidence();n=len(lattice_feature_names(TOKENS))
    m={'schema':MODEL_SCHEMA,'reference_policy':'partial_keyword_v2','body_id':BODY,'tokens':TOKENS,
       'feature_names':lattice_feature_names(TOKENS),'mean':[0.]*n,'scale':[1.]*n,'w1':np.zeros((16,n)).tolist(),
       'b1':[0.]*16,'w2':[0.]*16,'b2':10.,'threshold':.5,'trained_scopes':['complete_utterance'],
       'trained_contrasts':[{'scope':'complete_utterance','kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['p']}],
       'approved_for_child_scoring':False,'clinical_assessment':False}
    assert apply_lattice_gate(e,m)['status']=='possible_substitution'
    m['schema']='vaakmitra.contextual_sound.v1'
    assert apply_lattice_gate(e,m)['status']=='invalid_model'

