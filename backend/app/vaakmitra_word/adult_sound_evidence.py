"""DEC072/PHN013: bounded CTC event evidence; never forced recognition or grading."""
from __future__ import annotations
import math
import numpy as np

COMPOUNDS={'aj':('a','j'),'aʋ':('a','ʋ'),'kʂ':('k','ʂ')}
SPECIAL={'<blank>','|','[UNK]','[PAD]','்'}
MIN_EVENT_PROBABILITY=.005
DIFFERENCE_LOG_RATIO=math.log(20)
RUNNER_LOG_RATIO=math.log(4)


def ctc_log_probability(log_probabilities,target,blank=0):
    lp=np.asarray(log_probabilities,dtype=np.float64)
    if lp.ndim!=2 or not len(lp) or any(type(i) not in (int,np.int64,np.int32) or i==blank or not 0<=i<lp.shape[1] for i in target):
        raise ValueError('Nonblank integer CTC targets required')
    if not target:return float(lp[:,blank].sum())
    states=np.full(2*len(target)+1,blank,dtype=np.int64);states[1::2]=target
    previous=np.full(len(states),-np.inf);previous[0]=lp[0,blank];previous[1]=lp[0,target[0]]
    skip=np.zeros(len(states),dtype=bool)
    skip[2:]=(states[2:]!=blank)&(states[2:]!=states[:-2])
    for frame in lp[1:]:
        step=np.concatenate(([-np.inf],previous[:-1]))
        jump=np.concatenate(([-np.inf,-np.inf],previous[:-2]));jump[~skip]=-np.inf
        current=np.logaddexp(np.logaddexp(previous,step),jump)+frame[states]
        previous.fill(0);previous=current
    result=float(np.logaddexp(previous[-1],previous[-2]));previous.fill(0)
    return result


def native_sequences(phones,tokens):
    """All disjoint native CTC strings that expand to this canonical sequence."""
    source=tuple(phones);choices=[(i,COMPOUNDS.get(t,(t,))) for i,t in enumerate(tokens) if t not in SPECIAL]
    memo={len(source):[()]}
    def paths(position):
        if position in memo:return memo[position]
        result=[]
        for index,units in choices:
            if source[position:position+len(units)]==units:
                result.extend((index,)+tail for tail in paths(position+len(units)))
                if len(result)>64:raise ValueError('Native tokenization budget exceeded')
        memo[position]=result
        return result
    return paths(0)


def build_hypotheses(reference,tokens,accepted_variants=()):
    accepted=list(dict.fromkeys([tuple(reference)]+[tuple(x) for x in accepted_variants]))
    known=sorted({p for t in tokens if t not in SPECIAL for p in COMPOUNDS.get(t,(t,))})
    rows={}
    def add(phones,kind,expected=(),alternative=()):
        phones=tuple(phones)
        if not phones:return
        if phones in accepted:kind='sequence_supported';expected=();alternative=()
        signature=(kind,tuple(dict.fromkeys(expected)),tuple(dict.fromkeys(alternative)))
        if phones not in rows:
            rows[phones]={'phones':phones,'kind':kind,'families':[]}
        if signature not in rows[phones]['families']:rows[phones]['families'].append(signature)
    for ref in accepted:
        add(ref,'sequence_supported')
        for a in range(len(ref)):
            for width in (1,2):
                if a+width<=len(ref):add(ref[:a]+ref[a+width:],'possible_omission',ref[a:a+width])
            for sound in known:
                if sound!=ref[a]:add(ref[:a]+(sound,)+ref[a+1:],'possible_substitution',(ref[a],),(sound,))
                if a+1<len(ref) and ref[a]==ref[a+1] and sound!=ref[a]:
                    add(ref[:a]+(sound,sound)+ref[a+2:],'possible_substitution',(ref[a],),(sound,))
    if len(rows)>512:raise ValueError('Hypothesis budget exceeded')
    return list(rows.values())


def assess_sound_evidence(probabilities,tokens,reference,*,accepted_variants=(),score_paths=None,policy='default'):
    """Compare frozen acoustic hypotheses; thresholds are not clinical calibration.

    score_paths optionally supplies batched GPU CTC log probabilities. It receives
    local log probabilities and native ID strings, never a request to an LLM.
    """
    if policy not in {'default','strict'}:raise ValueError('Unknown fixed policy')
    minimum_event,minimum_difference,minimum_runner=(MIN_EVENT_PROBABILITY,DIFFERENCE_LOG_RATIO,RUNNER_LOG_RATIO) if policy=='default' else (.1,math.log(100),math.log(10))
    base={'status':'insufficient_evidence','expected_sounds':[],'alternative_sounds':[],
          'confirmed':False,'clinical_assessment':False}
    p=np.array(probabilities,dtype=np.float64,copy=True);lp=None
    try:
        if (p.ndim!=2 or p.shape[1]!=len(tokens) or not 1<=len(p)<=400 or not tokens or tokens[0]!='<blank>' or
            len(tokens)!=len(set(tokens)) or not np.isfinite(p).all() or (p<0).any() or (p>1).any() or
            not np.allclose(p.sum(axis=1),1,atol=1e-4)):
            return dict(base,status='invalid_evidence')
        known={unit for t in tokens if t not in SPECIAL for unit in COMPOUNDS.get(t,(t,))}
        refs=[reference]+list(accepted_variants)
        if any(not ref or len(ref)>12 or any(t not in known for t in ref) for ref in refs):
            return dict(base,status='unsupported_reference')
        maxima=np.argmax(p,axis=1);peaks=p[np.arange(len(p)),maxima]
        credible=sum(tokens[int(i)] not in SPECIAL and float(v)>=.5 for i,v in zip(maxima,peaks))
        # PHN013: a tied unknown must not disappear behind vocabulary-order argmax.
        unknown=any(np.any(p[:,i]>=.5) for i,t in enumerate(tokens) if t in {'[UNK]','[PAD]','்'})
        if credible<2 or unknown:return base
        # Separators can carry silent CTC boundaries; they are not phones to omit.
        if '|' in tokens:
            separator=tokens.index('|');p[:,0]+=p[:,separator];p[:,separator]=0
        lp=np.log(np.maximum(p,1e-30))
        try:
            hypotheses=build_hypotheses(reference,tokens,accepted_variants)
            paths=[];groups=[]
            for row in hypotheses:
                native=native_sequences(row['phones'],tokens)
                groups.append((len(paths),len(paths)+len(native)));paths.extend(native)
            if len(paths)>2048:return dict(base,status='unsupported_reference')
        except ValueError:return dict(base,status='unsupported_reference')
        values=score_paths(lp,paths,0) if score_paths is not None else [ctc_log_probability(lp,path) for path in paths]
        if len(values)!=len(paths):return dict(base,status='invalid_evidence')
        scored=[]
        for row,(a,b) in zip(hypotheses,groups):
            score=float(np.logaddexp.reduce(values[a:b])) if a<b else -math.inf
            scored.append((score,row))
        if any(math.isnan(score) or score>1e-3 for score,row in scored):return dict(base,status='invalid_evidence')
        accepted=[x for x in scored if x[1]['kind']=='sequence_supported']
        alternatives=sorted([x for x in scored if x[1]['kind']!='sequence_supported'],key=lambda x:-x[0])
        expected_score=float(np.logaddexp.reduce([x[0] for x in accepted]))
        best_score,best=alternatives[0] if alternatives else (-math.inf,None)
        base.update(reference_log_probability=expected_score,best_alternative_log_probability=best_score)
        if expected_score>=math.log(minimum_event) and expected_score-best_score>=minimum_runner:
            return dict(base,status='sequence_supported')
        if best is None or best_score<math.log(minimum_event) or best_score-expected_score<minimum_difference:return base
        runner=alternatives[1][0] if len(alternatives)>1 else -math.inf
        families=set(best['families'])
        if best_score-runner<minimum_runner or len(families)!=1:return dict(base,status='ambiguous_evidence')
        kind,expected,alternative=next(iter(families))
        return dict(base,status=kind,expected_sounds=list(expected),alternative_sounds=list(alternative),
                    log_ratio=best_score-expected_score,runner_log_ratio=best_score-runner)
    finally:
        p.fill(0)
        if lp is not None:lp.fill(0)
