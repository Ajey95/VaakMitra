"""DEC071/PHN012/COA001: target-free pause processing and unscored alignment.

Reference alignment never substitutes for unconstrained recognition. Posterior
support thresholds are engineering guards, not calibrated child correctness.
"""
from dataclasses import dataclass
import math
import numpy as np


@dataclass(frozen=True)
class PauseCompaction:
    samples: np.ndarray
    retained_ranges: tuple[tuple[int, int], ...]
    removed_samples: int


def compact_pauses(samples, sample_rate=16000):
    wave=np.asarray(samples,dtype=np.float32)
    if sample_rate!=16000 or wave.ndim!=1 or len(wave)>128000 or not np.isfinite(wave).all():
        raise ValueError('Finite mono16kHz recording up to8s required')
    if not len(wave):return PauseCompaction(wave.copy(),(),0)
    frame=160;count=(len(wave)+frame-1)//frame
    rms=np.array([np.sqrt(np.mean(wave[i*frame:min((i+1)*frame,len(wave))].astype(np.float64)**2)) for i in range(count)])
    # Only near-digital-silence; weak consonants are not equivalent to a pause.
    threshold=min(16/32768,float(rms.max())*.01)
    quiet=rms<=threshold
    cuts=[];i=0
    while i<count:
        if not quiet[i]:i+=1;continue
        start=i
        while i<count and quiet[i]:i+=1
        end=i
        if start>0 and end<count and (end-start)*frame>=4800:
            # Keep60ms acoustic context plus40ms pause per side; never remove edges.
            left=start*frame+1600;right=end*frame-1600
            if right>left:cuts.append((left,right))
    ranges=[];cursor=0
    for left,right in cuts:
        ranges.append((cursor,left));cursor=right
    ranges.append((cursor,len(wave)))
    retained=tuple((a,b) for a,b in ranges if b>a)
    output=np.concatenate([wave[a:b] for a,b in retained]).astype(np.float32,copy=False)
    return PauseCompaction(output,retained,len(wave)-len(output))


def align_posteriors(posteriors,tokens,reference):
    p=np.array(posteriors,dtype=np.float64,copy=True)
    spans=[];costs=None
    base={'status':'diagnostic_only','phones':[],'observed_sequence':[],
          'child_correctness':None,'clinical_assessment':False}
    try:
        if (p.ndim!=2 or p.shape[1]!=len(tokens) or not 1<=len(p)<=400 or
            len(tokens)!=len(set(tokens)) or not tokens or tokens[0]!='<blank>' or
            not np.isfinite(p).all() or (p<0).any() or (p>1).any() or
            not np.allclose(p.sum(axis=1),1,atol=1e-4)):
            raise ValueError('Finite normalized frame posteriors required')
        known=set(tokens)-{'<blank>','|','[UNK]','[PAD]','்'}
        if not reference or len(reference)>64 or any(t not in known for t in reference):
            return dict(base,status='unsupported_reference')
        indices=np.argmax(p,axis=1);i=0
        while i<len(p):
            start=i;chosen=int(indices[i]);i+=1
            while i<len(p) and indices[i]==chosen:i+=1
            if tokens[chosen] in {'<blank>','|'}:continue
            mean=p[start:i].mean(axis=0)
            alternatives=np.delete(mean,chosen)
            margin=float(mean[chosen]-alternatives.max());alternatives.fill(0)
            spans.append({'token':tokens[chosen],'start':start,'end':i,'mean':mean,
                          'peak':float(mean[chosen]),'margin':margin})
        indices.fill(0)
        base['observed_sequence']=[s['token'] for s in spans]
        if (not spans or any(s['token'] not in known or s['token'] in {'aj','aʋ','kʂ'} for s in spans)
            or all(s['peak']<.65 or s['margin']<.2 for s in spans)):
            return dict(base,status='insufficient_evidence')
        n,m=len(reference),len(spans);ids={t:i for i,t in enumerate(tokens)}
        costs=np.full((n+1,m+1),np.inf);costs[0,0]=0.;back={}
        paths=np.zeros((n+1,m+1),dtype=np.int8);paths[0,0]=1
        for a in range(n+1):
            for b in range(m+1):
                if a==b==0:continue
                options=[]
                if a and b:
                    prob=float(spans[b-1]['mean'][ids[reference[a-1]]])
                    cost=min(2.0,-math.log(max(prob,1e-9))/3)
                    options.append((costs[a-1,b-1]+cost,'pair',int(paths[a-1,b-1])))
                if a:options.append((costs[a-1,b]+1.5,'delete',int(paths[a-1,b])))
                if b:options.append((costs[a,b-1]+1.5,'insert',int(paths[a,b-1])))
                value,action,_=min(options,key=lambda row:row[0]);costs[a,b]=value;back[a,b]=action
                paths[a,b]=min(2,sum(count for v,_,count in options if abs(v-value)<=1e-8))
        if paths[n,m]>1:return dict(base,status='ambiguous_alignment')
        aligned=[];a,b=n,m
        while a or b:
            action=back[a,b]
            if action=='pair':
                span=spans[b-1];expected=reference[a-1]
                strong=span['peak']>=.65 and span['margin']>=.2
                kind=('model_support' if span['token']==expected else 'possible_substitution') if strong else 'uncertain'
                aligned.append({'expected':expected,'observed':span['token'],'kind':kind,
                                'start_frame':span['start'],'end_frame':span['end'],'confirmed':False})
                a-=1;b-=1
            elif action=='delete':
                aligned.append({'expected':reference[a-1],'observed':None,'kind':'possible_omission',
                                'start_frame':None,'end_frame':None,'confirmed':False});a-=1
            else:b-=1
        base['phones']=list(reversed(aligned))
        base['unassigned_observed_spans']=m-sum(r['observed'] is not None for r in aligned)
        return base
    finally:
        p.fill(0)
        for span in spans:span['mean'].fill(0)
        if costs is not None:costs.fill(0)


def coaching_tool_result(word_id,alignment,recording_conditions=()):
    """COA001/COA002: neutral local contract; the adult sound gate failed.

The existing local coach consumes it directly. Any future LLM transport must use
this allow-list, never serialize an observation/recording object wholesale.
"""
    targets={f'TA_WORD_{i:04d}' for i in (1,2,12,13,14,15,16,17,49,50,72,82,83,86,90,96,98,99,100,101,102,103,104,84,61)}
    if not isinstance(word_id,str) or word_id not in targets:
        raise ValueError('Only approved canonical target IDs are allowed in coach results')
    permitted={'low_recording_level','clipped_recording','unclear_recording','long_attempt','pause_variation'}
    statuses={'diagnostic_only','insufficient_evidence','unsupported_reference','invalid_evidence','ambiguous_alignment','sequence_agreement'}
    status=alignment.get('status','insufficient_evidence')
    if not isinstance(status,str) or status not in statuses or status=='diagnostic_only':status='insufficient_evidence'
    # Research alignments are retained separately, never promoted into coaching.
    differences=[]
    return {'schema':'vaakmitra.speech_analysis.v1','target_word_id':word_id,
            'evidence_status':status,
            'possible_sound_differences':differences,
            'recording_conditions':sorted(set(recording_conditions)&permitted),
            'child_correctness':None,'clinical_assessment':False,'local_only':True,
            'allowed_actions':['demonstrate_target','offer_sound_practice','ask_rerecord','offer_break'],
            'forbidden_actions':['claim_child_error','diagnose','score','force_retry']}
