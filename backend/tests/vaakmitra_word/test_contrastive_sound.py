"""DEC076/PHN017: reference hypotheses are never substituted for decoded phones."""
import numpy as np
from app.vaakmitra_word.contrastive_sound import propose_contrast,contrast_feature_names,apply_contrast_gate
TOKENS=['<blank>','a','m','p','s','[UNK]']
def frames(ids):
    p=np.full((len(ids),len(TOKENS)),.0001)
    for i,j in enumerate(ids):p[i,j]=1-(len(TOKENS)-1)*.0001
    return p
def evidence():return propose_contrast(frames([1,1,0,4,4,0,1,1]),TOKENS,['a','m','a'],['a','s','a'],body_id='test')
def model():
    size=len(contrast_feature_names(TOKENS));hidden=16
    return {'schema':'vaakmitra.contrastive_sound.v1','body_id':'test','tokens':list(TOKENS),'feature_names':contrast_feature_names(TOKENS),
            'mean':[0.]*size,'scale':[1.]*size,'w1':[[0.]*size for _ in range(hidden)],'b1':[0.]*hidden,'w2':[0.]*hidden,'b2':2.,'threshold':.8,
            'trained_contrasts':[{'kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['s']}],
            'approved_for_child_scoring':False,'clinical_assessment':False}
def test_phn017_supported_substitution_is_a_hypothesis_and_free_input_stays_unchanged():
    p=frames([1,1,0,4,4,0,1,1]);copy=p.copy();raw=['a','s','a'];result=propose_contrast(p,TOKENS,['a','m','a'],raw,body_id='test')
    assert result['status']=='proposal' and result['kind']=='possible_substitution'
    assert result['expected_sounds']==['m'] and result['alternative_sounds']==['s']
    assert raw==['a','s','a'];np.testing.assert_array_equal(p,copy)
def test_phn017_omitted_sound_has_no_invented_observed_sound():
    result=propose_contrast(frames([1,1,0,0,1,1]),TOKENS,['a','m','a'],['a','a'],body_id='test')
    assert result['status']=='proposal' and result['kind']=='possible_omission' and result['alternative_sounds']==[]
def test_phn017_silence_unknown_tie_and_unsupported_sh_abstain():
    p=np.zeros((3,6));p[:,1]=.5;p[:,5]=.5
    assert propose_contrast(p,TOKENS,['m'],['a'],body_id='test')['status']=='insufficient_evidence'
    assert propose_contrast(frames([0]*6),TOKENS,['m'],['a'],body_id='test')['status']=='insufficient_evidence'
    assert propose_contrast(frames([4]*6),TOKENS,['ʃ'],['s'],body_id='test')['status']=='unsupported_reference'
def test_phn017_accepted_variants_never_become_correction_hypotheses():
    result=propose_contrast(frames([4,4,0,1,1]),TOKENS,['m','a'],['s','a'],accepted_variants=[['s','a']],body_id='test')
    assert result['status']=='sequence_supported'
def test_phn017_competing_sound_tie_cannot_name_an_error():
    p=frames([1,1,0,4,4,0,1,1]);p[3:5,4]=.4998;p[3:5,3]=.4998;p/=p.sum(1,keepdims=True)
    assert propose_contrast(p,TOKENS,['a','m','a'],['a','s','a'],body_id='test')['status']!='proposal'
def test_phn017_network_is_closed_body_bound_and_thresholded():
    result=apply_contrast_gate(evidence(),model())
    assert result['status']=='possible_substitution' and result['confirmed'] is False
    data=model();data['threshold']=.99;assert apply_contrast_gate(evidence(),data)['status']=='insufficient_evidence'
    data=model();data['body_id']='other';assert apply_contrast_gate(evidence(),data)['status']=='invalid_model'
def test_phn017_untrained_contrast_and_nonfinite_network_fail_closed():
    data=model();data['trained_contrasts']=[];assert apply_contrast_gate(evidence(),data)['status']=='insufficient_evidence'
    data=model();data['b2']=float('nan');assert apply_contrast_gate(evidence(),data)['status']=='invalid_model'
    data=model();data['w1'][0].pop();assert apply_contrast_gate(evidence(),data)['status']=='invalid_model'
