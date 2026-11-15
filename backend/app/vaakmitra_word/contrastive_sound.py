"""DEC076/PHN017: learned competing hypotheses, never rewritten recognition."""
from __future__ import annotations
import math
import numpy as np
from .adult_sound_evidence import COMPOUNDS,SPECIAL,build_hypotheses,native_sequences,ctc_log_probability
from .real_adult_sound import units,difference_proposal
from .focused_words import distance

FEATURES=['reference_per_phone','alternative_per_phone','reference_per_frame','alternative_per_frame',
          'difference_margin','runner_margin','alternative_vs_free','free_reference_edits','free_alternative_edits',
          'frame_entropy','mean_peak','mean_blank','uncertain_fraction','credible_fraction','mean_phone_peak',
          'minimum_phone_peak','onset_blank','offset_blank','reference_length','alternative_length','frames',
          'phone_density','omission','repeated_group','greedy_beam_agreement']
def contrast_feature_names(tokens):
    known=units(tokens)
    return FEATURES+[f'expected:{p}' for p in known]+[f'alternative:{p}' for p in known]

def propose_contrast(probabilities,tokens,reference,decoded,*,body_id,accepted_variants=(),score_paths=None):
    base={'status':'insufficient_evidence','expected_sounds':[],'alternative_sounds':[],'confirmed':False,
          'clinical_assessment':False,'body_id':body_id}
    p=np.array(probabilities,dtype=np.float64,copy=True);lp=None
    try:
        if (p.ndim!=2 or not 1<=len(p)<=400 or not tokens or tokens[0]!='<blank>' or
            p.shape[1]!=len(tokens) or len(set(tokens))!=len(tokens) or not np.isfinite(p).all() or
            (p<0).any() or (p>1).any() or not np.allclose(p.sum(1),1,atol=1e-4)):return base
        known=units(tokens);refs=list(dict.fromkeys([tuple(reference)]+[tuple(x) for x in accepted_variants]))
        if any(not ref or len(ref)>12 or not set(ref)<=set(known) for ref in refs):return dict(base,status='unsupported_reference')
        if not decoded or len(decoded)>16 or not set(decoded)<=set(known):return base
        if any(np.any(p[:,i]>=.5) for i,t in enumerate(tokens) if t in {'[UNK]','[PAD]','்'}):return base
        maximum=np.argmax(p,1);peaks=p[np.arange(len(p)),maximum]
        credible=sum(tokens[int(i)] not in SPECIAL and v>=.5 for i,v in zip(maximum,peaks))
        if credible<2:return base
        if tuple(decoded) in refs:return dict(base,status='sequence_supported')
        greedy=[];masses={unit:0. for unit in known}
        for index,token in enumerate(tokens):
            if token not in SPECIAL:
                for unit in COMPOUNDS.get(token,(token,)):masses[unit]+=float(p[:,index].sum())
        allowed=set(sorted(known,key=lambda u:(-masses[u],u))[:8])|set(decoded)
        candidates=[]
        for row in build_hypotheses(reference,tokens,accepted_variants):
            if row['kind']=='sequence_supported' or len(set(row['families']))!=1:continue
            family=row['families'][0]
            if not set(family[2])<=allowed:continue
            proposals=[difference_proposal(ref,row['phones']) for ref in refs]
            valid=[v for v in proposals if v is not None and (v['kind'],tuple(v['expected_sounds']),tuple(v['alternative_sounds']))==family]
            if valid:candidates.append((row['phones'],valid[0]))
        if not candidates:return base
        if '|' in tokens:
            sep=tokens.index('|');p[:,0]+=p[:,sep];p[:,sep]=0
        lp=np.log(np.maximum(p,1e-30))
        sequences=list(dict.fromkeys(refs+[r[0] for r in candidates]+[tuple(decoded)]));paths=[];groups=[]
        for sequence in sequences:
            native=native_sequences(sequence,tokens);groups.append((len(paths),len(paths)+len(native)));paths.extend(native)
        if len(paths)>2048:return base
        scores=score_paths(lp,paths,0) if score_paths else [ctc_log_probability(lp,path) for path in paths]
        if len(scores)!=len(paths):return base
        values={seq:float(np.logaddexp.reduce(scores[a:b])) if a<b else -math.inf for seq,(a,b) in zip(sequences,groups)}
        if any(math.isnan(v) or v>1e-3 for v in values.values()):return base
        expected=float(np.logaddexp.reduce([values[ref] for ref in refs]));free=values[tuple(decoded)]
        ranked=sorted([(values[sequence],sequence,proposal) for sequence,proposal in candidates],key=lambda row:-row[0])
        best,sequence,proposal=ranked[0];runner=ranked[1][0] if len(ranked)>1 else -math.inf
        if not all(math.isfinite(v) for v in [expected,free,best]) or best-expected<math.log(2) or best-runner<math.log(2):return base
        for i,index in enumerate(maximum):
            token=tokens[int(index)]
            if token in {'<blank>','|'} or (i and index==maximum[i-1]):continue
            greedy.extend(COMPOUNDS.get(token,(token,)))
        nonblank=[i for i,index in enumerate(maximum) if tokens[int(index)] not in SPECIAL];span_peaks=[];begin=0
        while begin<len(maximum):
            end=begin+1
            while end<len(maximum) and maximum[end]==maximum[begin]:end+=1
            if tokens[int(maximum[begin])] not in SPECIAL:span_peaks.append(float(peaks[begin:end].max()))
            begin=end
        clip=lambda v:max(-100.,min(100.,v));t=len(p);m=len(reference);a=len(sequence)
        values=[clip(expected)/m,clip(best)/a,clip(expected)/t,clip(best)/t,clip(best-expected),clip(best-runner),
                clip(best-free),distance(reference,decoded)/m,distance(sequence,decoded)/a,
                float(-(p*np.log(np.maximum(p,1e-30))).sum(1).mean()/math.log(len(tokens))),float(peaks.mean()),
                float(p[:,0].mean()),float((peaks<.5).mean()),credible/t,float(peaks[nonblank].mean()),min(span_peaks),
                nonblank[0]/t,(t-1-nonblank[-1])/t,m/12,a/12,t/150,t/a/30,
                float(proposal['kind']=='possible_omission'),float(proposal['repeated_group']),float(greedy==list(decoded))]
        values.extend(float(u in proposal['expected_sounds']) for u in known)
        values.extend(float(u in proposal['alternative_sounds']) for u in known)
        return dict(base,status='proposal',**proposal,features=values,feature_names=contrast_feature_names(tokens),tokens=list(tokens))
    except (ValueError,TypeError,IndexError,OverflowError):return base
    finally:
        p.fill(0)
        if lp is not None:lp.fill(0)

def apply_contrast_gate(evidence,model):
    base={'status':evidence['status'] if evidence['status']!='proposal' else 'insufficient_evidence',
          'expected_sounds':[],'alternative_sounds':[],'confirmed':False,'clinical_assessment':False}
    if evidence['status']!='proposal':return base
    try:
        names=contrast_feature_names(evidence['tokens']);size=len(names)
        if (model['schema']!='vaakmitra.contrastive_sound.v1' or model['body_id']!=evidence['body_id'] or
            model['tokens']!=evidence['tokens'] or model['feature_names']!=names or evidence['feature_names']!=names or
            model['approved_for_child_scoring'] is not False or model['clinical_assessment'] is not False):raise ValueError()
        expected={'mean':(size,),'scale':(size,),'w1':(16,size),'b1':(16,),'w2':(16,)}
        arrays={k:np.asarray(model[k],dtype=np.float64) for k in expected}
        if any(v.shape!=expected[k] or not np.isfinite(v).all() for k,v in arrays.items()) or (arrays['scale']<=0).any():raise ValueError()
        bias=float(model['b2']);threshold=float(model['threshold'])
        if not math.isfinite(bias) or not math.isfinite(threshold) or not 0<=threshold<=1:raise ValueError()
        table=model['trained_contrasts'];known=set(units(evidence['tokens']));supported=set()
        if not isinstance(table,list) or len(table)>512:raise ValueError()
        for row in table:
            if not isinstance(row,dict) or set(row)!={'kind','expected_sounds','alternative_sounds'}:raise ValueError()
            kind=row['kind'];a=row['expected_sounds'];b=row['alternative_sounds']
            if (kind not in {'possible_omission','possible_substitution'} or not isinstance(a,list) or not isinstance(b,list) or
                len(a)!=1 or len(b)!=(kind=='possible_substitution') or any(not isinstance(s,str) or s not in known for s in a+b)):raise ValueError()
            signature=(kind,tuple(a),tuple(b))
            if signature in supported:raise ValueError()
            supported.add(signature)
        signature=(evidence['kind'],tuple(evidence['expected_sounds']),tuple(evidence['alternative_sounds']))
        if signature not in supported:return base
        values=np.asarray(evidence['features'],dtype=np.float64)
        if values.shape!=(size,) or not np.isfinite(values).all():raise ValueError()
        hidden=np.maximum(0,arrays['w1']@((values-arrays['mean'])/arrays['scale'])+arrays['b1'])
        score=float(arrays['w2']@hidden)+bias;confidence=1/(1+math.exp(-max(-80.,min(80.,score))))
        if confidence<threshold:return dict(base,engineering_confidence=confidence)
        return dict(base,status=evidence['kind'],expected_sounds=evidence['expected_sounds'],alternative_sounds=evidence['alternative_sounds'],engineering_confidence=confidence)
    except (KeyError,ValueError,TypeError,OverflowError):return dict(base,status='invalid_model')
