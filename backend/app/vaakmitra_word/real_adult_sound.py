"""DEC073/PHN014: bounded learned sound evidence, separate from free decoding."""
from __future__ import annotations
import math
import numpy as np
from .adult_sound_evidence import COMPOUNDS,SPECIAL,native_sequences,ctc_log_probability

# PHN014/017: only native consonant geminates count as one repeated identity.
CONSONANTS=frozenset({'j','n̪','ɻ','h','n','ʋ','ʈ','p','t͡ʃ','ŋ','l','ɾ','t̪','ʂ','m','d͡ʒ','r','ɳ','k','ɲ','ɭ','s'})

BASE_FEATURES=['observed_logp','reference_logp','log_margin','observed_per_phone','reference_per_phone',
               'observed_per_frame','reference_per_frame','expected_length','observed_length','frame_count',
               'phone_density','frame_entropy','mean_peak','mean_blank','uncertain_fraction','mean_phone_peak',
               'minimum_phone_peak','onset_blank_fraction','offset_blank_fraction','omission','repeated_group']

def units(tokens):return sorted({p for t in tokens if t not in SPECIAL for p in COMPOUNDS.get(t,(t,))})
def feature_names(tokens):
    known=units(tokens)
    return BASE_FEATURES+[f'expected:{p}' for p in known]+[f'alternative:{p}' for p in known]

def difference_proposal(reference,observed):
    ref=tuple(reference);obs=tuple(observed);found={}
    def add(kind,expected,alternative=(),group=False):
        signature=(kind,tuple(dict.fromkeys(expected)),tuple(dict.fromkeys(alternative)))
        found[signature]={'kind':kind,'expected_sounds':list(signature[1]),'alternative_sounds':list(signature[2]),'repeated_group':group}
    if ref==obs or not ref or not obs:return None
    for i in range(len(ref)):
        if ref[:i]+ref[i+1:]==obs:add('possible_omission',(ref[i],))
        if i+1<len(ref) and ref[i] in CONSONANTS and ref[i]==ref[i+1] and ref[:i]+ref[i+2:]==obs:
            add('possible_omission',(ref[i],),group=True)
    if len(ref)==len(obs):
        mismatch=[i for i,(a,b) in enumerate(zip(ref,obs)) if a!=b]
        if len(mismatch)==1:
            i=mismatch[0];add('possible_substitution',(ref[i],),(obs[i],))
        elif len(mismatch)==2:
            i,j=mismatch
            if j==i+1 and ref[i] in CONSONANTS and obs[i] in CONSONANTS and ref[i]==ref[j] and obs[i]==obs[j]:
                add('possible_substitution',(ref[i],),(obs[i],),True)
    return next(iter(found.values())) if len(found)==1 else None

def extract_evidence(probabilities,tokens,reference,decoded,*,accepted_variants=(),score_paths=None):
    """Owned transient features; never an exported recording representation."""
    base={'status':'insufficient_evidence','expected_sounds':[],'alternative_sounds':[],'confirmed':False,
          'clinical_assessment':False,'approved_for_child_scoring':False}
    p=np.array(probabilities,dtype=np.float64,copy=True);lp=None
    try:
        if (p.ndim!=2 or not 1<=len(p)<=400 or not tokens or tokens[0]!='<blank>' or
            len(set(tokens))!=len(tokens) or p.shape[1]!=len(tokens) or not np.isfinite(p).all() or
            (p<0).any() or (p>1).any() or not np.allclose(p.sum(1),1,atol=1e-4)):return base
        known=units(tokens);refs=list(dict.fromkeys([tuple(reference)]+[tuple(x) for x in accepted_variants]))
        if any(not ref or len(ref)>12 or not set(ref)<=set(known) for ref in refs):return dict(base,status='unsupported_reference')
        if not decoded or not set(decoded)<=set(known):return base
        if any(np.any(p[:,i]>=.5) for i,t in enumerate(tokens) if t in {'[UNK]','[PAD]','்'}):return base
        maxima=np.argmax(p,axis=1);peaks=p[np.arange(len(p)),maxima]
        if sum(tokens[int(i)] not in SPECIAL and peak>=.5 for i,peak in zip(maxima,peaks))<2:return base
        if tuple(decoded) in refs:return dict(base,status='sequence_supported')
        greedy=[]
        for i,index in enumerate(maxima):
            token=tokens[int(index)]
            if token in {'<blank>','|'} or (i and index==maxima[i-1]):continue
            greedy.extend(COMPOUNDS.get(token,(token,)))
        if list(decoded)!=greedy:return base
        proposals=[difference_proposal(ref,decoded) for ref in refs]
        if any(x is None for x in proposals):return base
        signatures={(x['kind'],tuple(x['expected_sounds']),tuple(x['alternative_sounds'])) for x in proposals}
        if len(signatures)!=1:return base
        proposal=proposals[0]
        if '|' in tokens:
            index=tokens.index('|');p[:,0]+=p[:,index];p[:,index]=0
        lp=np.log(np.maximum(p,1e-30))
        def probability(target):
            paths=native_sequences(target,tokens)
            scores=score_paths(lp,paths,0) if score_paths else [ctc_log_probability(lp,path) for path in paths]
            return float(np.logaddexp.reduce(scores)) if scores else -math.inf
        observed=probability(decoded);expected=float(np.logaddexp.reduce([probability(ref) for ref in refs]))
        if not math.isfinite(observed) or not math.isfinite(expected):return base
        observed=max(-100.,observed);expected=max(-100.,expected)
        entropy=float(-(p*np.log(np.maximum(p,1e-30))).sum(1).mean()/math.log(len(tokens)))
        nonblank=[float(peak) for index,peak in zip(maxima,peaks) if tokens[int(index)] not in SPECIAL]
        spans=[];start=0
        while start<len(maxima):
            end=start+1
            while end<len(maxima) and maxima[end]==maxima[start]:end+=1
            if tokens[int(maxima[start])] not in SPECIAL:spans.append(float(peaks[start:end].max()))
            start=end
        nonblank_indices=[i for i,index in enumerate(maxima) if tokens[int(index)] not in SPECIAL]
        t=len(p);n=len(decoded);m=len(reference)
        values=[observed,expected,max(-50.,min(50.,observed-expected)),observed/n,expected/m,
                observed/t,expected/t,m/8,n/8,t/150,t/n/30,entropy,float(peaks.mean()),float(p[:,0].mean()),
                float((peaks<.5).mean()),float(np.mean(nonblank)),min(spans),nonblank_indices[0]/t,
                (t-1-nonblank_indices[-1])/t,float(proposal['kind']=='possible_omission'),float(proposal['repeated_group'])]
        values.extend(float(unit in proposal['expected_sounds']) for unit in known)
        values.extend(float(unit in proposal['alternative_sounds']) for unit in known)
        return dict(base,status='proposal',**proposal,features=values,feature_names=feature_names(tokens),tokens=list(tokens))
    except (ValueError,TypeError,IndexError,OverflowError):return base
    finally:
        p.fill(0)
        if lp is not None:lp.fill(0)

def apply_gate(evidence,model):
    base={'status':evidence['status'] if evidence['status']!='proposal' else 'insufficient_evidence',
          'expected_sounds':[],'alternative_sounds':[],'confirmed':False,'clinical_assessment':False,
          'approved_for_child_scoring':False}
    if evidence['status']!='proposal':return base
    try:
        names=feature_names(evidence['tokens']);size=len(names)
        if (model['schema']!='vaakmitra.real_adult_sound.v1' or model['tokens']!=evidence['tokens'] or
            model['feature_names']!=names or evidence['feature_names']!=names or
            model['approved_for_child_scoring'] is not False or model['clinical_assessment'] is not False):raise ValueError()
        mean=np.asarray(model['mean'],dtype=np.float64);scale=np.asarray(model['scale'],dtype=np.float64)
        weights=np.asarray(model['weights'],dtype=np.float64);values=np.asarray(evidence['features'],dtype=np.float64)
        bias=float(model['bias']);threshold=float(model['threshold'])
        if (any(x.shape!=(size,) or not np.isfinite(x).all() for x in [mean,scale,weights,values]) or
            (scale<=0).any() or not math.isfinite(bias) or not math.isfinite(threshold) or not 0<=threshold<=1):raise ValueError()
        if 'pair_thresholds' in model:
            pairs=model['pair_thresholds'];table={};known=set(units(evidence['tokens']))
            if not isinstance(pairs,list) or len(pairs)>256:raise ValueError()
            for row in pairs:
                if not isinstance(row,dict) or set(row)!={'kind','expected_sounds','alternative_sounds','threshold'}:raise ValueError()
                kind=row['kind'];expected=row['expected_sounds'];alternative=row['alternative_sounds'];cutoff=float(row['threshold'])
                if (kind not in {'possible_omission','possible_substitution'} or not isinstance(expected,list) or
                    not isinstance(alternative,list) or len(expected)!=1 or len(alternative)!=(kind=='possible_substitution') or
                    any(not isinstance(s,str) or s not in known for s in expected+alternative) or
                    not math.isfinite(cutoff) or not 0<=cutoff<=1):raise ValueError()
                signature=(kind,tuple(expected),tuple(alternative))
                if signature in table:raise ValueError()
                table[signature]=cutoff
            signature=(evidence['kind'],tuple(evidence['expected_sounds']),tuple(evidence['alternative_sounds']))
            if signature not in table:return base
            threshold=table[signature]
        score=float(np.dot((values-mean)/scale,weights)+bias)
        confidence=1/(1+math.exp(-max(-80.,min(80.,score))))
        if confidence<threshold:return dict(base,engineering_confidence=confidence)
        return dict(base,status=evidence['kind'],expected_sounds=evidence['expected_sounds'],
                    alternative_sounds=evidence['alternative_sounds'],engineering_confidence=confidence)
    except (KeyError,TypeError,ValueError,OverflowError):return dict(base,status='invalid_model')
