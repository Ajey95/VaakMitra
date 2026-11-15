"""DEC074/PHN015: bounded, target-independent acoustic output fine-tuning."""
from __future__ import annotations
import numpy as np

def validate_adapter(model,tokens):
    try:
        n=len(tokens)
        if (model['schema']!='vaakmitra.acoustic_logit_adapter.v1' or model['tokens']!=list(tokens) or
            not tokens or tokens[0]!='<blank>' or len(set(tokens))!=n or model['approved_for_child_scoring'] is not False):return False
        scale=np.asarray(model['scale'],dtype=np.float64);bias=np.asarray(model['bias'],dtype=np.float64);mix=np.asarray(model['mix'],dtype=np.float64)
        if scale.shape!=(n,) or bias.shape!=(n,) or mix.shape!=(n,n):return False
        if not all(np.isfinite(v).all() for v in [scale,bias,mix]):return False
        if (scale<.5).any() or (scale>2).any() or (np.abs(bias)>3).any() or (np.abs(mix)>3).any():return False
        for i,t in enumerate(tokens):
            if t in {'[UNK]','்'} and (scale[i]!=1 or bias[i]!=0 or np.any(mix[i]) or np.any(mix[:,i])):return False
        return True
    except (KeyError,TypeError,ValueError):return False

def adapt_logits(logits,tokens,model):
    if not validate_adapter(model,tokens):raise ValueError('Invalid acoustic adapter')
    values=np.array(logits,dtype=np.float64,copy=True);p=None;lp=None
    try:
        if values.ndim!=2 or not 1<=len(values)<=400 or values.shape[1]!=len(tokens) or not np.isfinite(values).all():
            raise ValueError('Invalid native logits')
        values-=values.max(1,keepdims=True);p=np.exp(values);p/=p.sum(1,keepdims=True);lp=np.log(np.maximum(p,1e-30))
        result=lp*np.asarray(model['scale'])+p@np.asarray(model['mix']).T+np.asarray(model['bias'])
        # A strong unknown stays unknown even if other classes gain a new bias.
        unknown=[i for i,t in enumerate(tokens) if t in {'[UNK]','்'}]
        if unknown:
            uncertain=(p[:,unknown]>=.5).any(1);result[uncertain]=lp[uncertain]
        return result.astype(np.float32)
    finally:
        values.fill(0)
        if p is not None:p.fill(0)
        if lp is not None:lp.fill(0)
