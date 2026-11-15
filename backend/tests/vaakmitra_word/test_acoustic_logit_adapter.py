"""DEC074/PHN015: compact adaptation remains word-independent and preserves unknowns."""
import numpy as np
import pytest
from app.vaakmitra_word.acoustic_logit_adapter import adapt_logits,validate_adapter
TOKENS=['<blank>','a','m','[UNK]']
def model():return {'schema':'vaakmitra.acoustic_logit_adapter.v1','tokens':list(TOKENS),'scale':[1.]*4,'bias':[0.]*4,'mix':[[0.]*4 for _ in range(4)],'approved_for_child_scoring':False}
def test_phn015_identity_preserves_frame_distribution_and_does_not_mutate_input():
    values=np.array([[2.,1.,-1.,0.],[0.,2.,4.,-1.]],dtype=np.float32);before=values.copy()
    adapted=adapt_logits(values,TOKENS,model())
    p=lambda x:np.exp(x-x.max(1,keepdims=True))/np.exp(x-x.max(1,keepdims=True)).sum(1,keepdims=True)
    np.testing.assert_allclose(p(values),p(adapted),rtol=1e-6,atol=1e-7)
    np.testing.assert_array_equal(values,before)
def test_phn015_scale_bias_and_posterior_mix_follow_declared_numeric_order():
    values=np.array([[0.,1.,2.,-1.]],dtype=np.float32);data=model();data['scale'][1]=.8;data['bias'][2]=.2;data['mix'][1][2]=.3
    p=np.exp(values-values.max())/np.exp(values-values.max()).sum();lp=np.log(p)
    expected=lp*np.asarray(data['scale'])+p@np.asarray(data['mix']).T+np.asarray(data['bias'])
    np.testing.assert_allclose(adapt_logits(values,TOKENS,data),expected,atol=1e-6)
def test_phn015_unknown_rows_and_columns_cannot_be_repurposed_as_a_phone():
    for field,index in [('scale',3),('bias',3)]:
        data=model();data[field][index]=.5;assert not validate_adapter(data,TOKENS)
    data=model();data['mix'][1][3]=.1;assert not validate_adapter(data,TOKENS)
    data=model();data['mix'][3][1]=.1;assert not validate_adapter(data,TOKENS)
def test_phn015_bad_schema_order_shapes_and_nonfinite_weights_rejected():
    data=model();data['scale'][0]=float('nan');assert not validate_adapter(data,TOKENS)
    data=model();data['tokens'].reverse();assert not validate_adapter(data,TOKENS)
    data=model();data['bias'].pop();assert not validate_adapter(data,TOKENS)
    with pytest.raises(ValueError):adapt_logits(np.array([[float('nan')]*4]),TOKENS,model())
