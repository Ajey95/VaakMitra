"""DEC077/PHN018: contextual sound evidence cannot alter unrestricted recognition."""
import copy
import numpy as np
from app.vaakmitra_word.contextual_sound import extract_contextual_evidence,feature_names,apply_contextual_gate

TOKENS=['<blank>','a','m','p','k','s','j','aj','[UNK]']
BODY='b'*64
def pframes(ids):
    p=np.full((len(ids),len(TOKENS)),.0001)
    for i,j in enumerate(ids):p[i,j]=1-(len(TOKENS)-1)*.0001
    return p
def evidence():
    p=pframes([4,4,0,1,1,0,3,3,0,1,1,0,5,5])
    return extract_contextual_evidence(p,TOKENS,['a','m','a'],['k','a','p','a','s'],'keyword',body_id=BODY)
def model():
    n=len(feature_names(TOKENS))
    return {'schema':'vaakmitra.contextual_sound.v1','body_id':BODY,'reference_policy':'partial_keyword_v2','tokens':TOKENS,
        'feature_names':feature_names(TOKENS),'mean':[0.]*n,'scale':[1.]*n,'w1':np.zeros((16,n)).tolist(),
        'b1':[0.]*16,'w2':[0.]*16,'b2':10.,'threshold':.5,'trained_scopes':['keyword','complete_utterance'],
        'trained_contrasts':[{'scope':'keyword','kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['p']}],
        'approved_for_child_scoring':False,'clinical_assessment':False}

def test_context_comparison_preserves_raw_and_both_contexts():
    e=evidence()
    assert e['status']=='proposal' and e['expected_sounds']==['m'] and e['alternative_sounds']==['p']
    assert e['raw_phones']==['k','a','p','a','s'] and e['expected_full']==['k','a','m','a','s']
    assert e['core']==['a','p','a'] and np.isfinite(e['features']).all()
    assert len(e['features'])==len(feature_names(TOKENS))

def test_target_inside_extra_speech_is_not_an_omission():
    p=pframes([4,4,0,1,1,0,2,2,0,1,1,0,5,5])
    e=extract_contextual_evidence(p,TOKENS,['a','m','a'],['k','a','m','a','s'],'keyword',body_id=BODY)
    assert e['status']=='sequence_supported' and not e['expected_sounds']

def test_keyword_edges_remain_uncertain():
    p=pframes([1,1,0,3,3])
    e=extract_contextual_evidence(p,TOKENS,['a','m'],['a','p'],'keyword',body_id=BODY)
    assert e['status']=='boundary_uncertain'

def test_compound_cannot_be_split_to_invent_a_word_boundary():
    p=pframes([4,4,0,7,7,0,3,3,0,1,1,0,5,5])
    e=extract_contextual_evidence(p,TOKENS,['j','m','a'],['k','a','j','p','a','s'],'keyword',body_id=BODY)
    assert e['status']=='compound_boundary_uncertain'

def test_two_plausible_different_sound_attributions_abstain():
    ids=[1,1,0,3,3,0,1,1,0,4,4,0,1,1,0,5,5,0,1,1]
    e=extract_contextual_evidence(pframes(ids),TOKENS,['a','m','a'],['a','p','a','k','a','s','a'],'keyword',body_id=BODY)
    assert e['status']=='ambiguous_placement' and not e['expected_sounds']

def test_highest_likelihood_reference_prevents_worst_placement_cherry_pick():
    ids=[1,1,0,3,3,0,1,1,0,4,4,0,1,1,0,5,5,0,1,1];p=pframes(ids)
    for i in [3,4]:
        p[i,:]=.0001;p[i,3]=.51;p[i,2]=1-.51-.0001*(len(TOKENS)-2)
    e=extract_contextual_evidence(p,TOKENS,['a','m','a'],['a','p','a','k','a','s','a'],'keyword',body_id=BODY)
    assert e['status']=='insufficient_evidence'

def test_unknown_ties_nan_scores_and_owned_buffer_are_safe():
    p=pframes([1,1,0,3,3,0,1,1]);before=p.copy()
    extract_contextual_evidence(p,TOKENS,['a','m','a'],['a','p','a'],'complete_utterance',body_id=BODY)
    np.testing.assert_array_equal(p,before)
    p[:]=0;p[:,1]=.5;p[:,-1]=.5
    assert extract_contextual_evidence(p,TOKENS,['a','m','a'],['a','p','a'],'complete_utterance',body_id=BODY)['status']=='insufficient_evidence'
    p=before
    e=extract_contextual_evidence(p,TOKENS,['a','m','a'],['a','p','a'],'complete_utterance',body_id=BODY,score_paths=lambda lp,paths,blank:[float('nan')]*len(paths))
    assert e['status']=='insufficient_evidence'

def test_gate_keeps_scope_identity_and_unsupported_pair_limits():
    e=evidence();m=model();out=apply_contextual_gate(e,m)
    assert out['status']=='possible_substitution' and out['confirmed'] is False and out['approved_for_child_scoring'] is False
    m['trained_scopes']=['complete_utterance']
    m['trained_contrasts'][0]['scope']='complete_utterance'
    assert apply_contextual_gate(e,m)['status']=='insufficient_evidence'
    m=model();m['trained_contrasts']=[]
    assert apply_contextual_gate(e,m)['status']=='insufficient_evidence'

def test_bad_model_body_schema_and_nonfinite_fail_closed():
    e=evidence()
    for key,value in [('body_id','other'),('schema','other'),('reference_policy','other'),('b2',float('nan')),('clinical_assessment',True)]:
        m=model();m[key]=value
        assert apply_contextual_gate(e,m)['status']=='invalid_model'
    m=model();m['scale'][0]=0
    assert apply_contextual_gate(e,m)['status']=='invalid_model'

