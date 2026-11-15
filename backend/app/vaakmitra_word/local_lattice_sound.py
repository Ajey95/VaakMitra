"""DEC077/PHN018: local acoustic hypotheses never replace independently decoded tokens."""
from __future__ import annotations
import math
import numpy as np
from .adult_sound_evidence import COMPOUNDS,SPECIAL,native_sequences,ctc_log_probability
from .real_adult_sound import units,CONSONANTS,difference_proposal
from .reference_boundaries import free_unit_spans,word_windows,exact_window_status
from .focused_words import distance

LATTICE_FEATURES=['reference_per_phone','alternative_per_phone','reference_per_frame','alternative_per_frame',
    'difference_margin','runner_margin','alternative_vs_free','free_reference_edits','free_alternative_edits',
    'frame_entropy','mean_peak','mean_blank','uncertain_fraction','minimum_raw_core_peak','mean_raw_core_peak',
    'left_gap','right_gap','frame_count','reference_length','alternative_length','context_before','context_after',
    'core_midpoint','omission','repeated_group','complete_scope','global_reference_margin','reference_placement_gap']

MODEL_SCHEMA='vaakmitra.local_lattice.v2'

def lattice_feature_names(tokens):
    known=units(tokens)
    return LATTICE_FEATURES+[f'expected:{u}' for u in known]+[f'alternative:{u}' for u in known]

def select_reference_placements(placements,scores):
    ranked=sorted(placements,key=lambda r:-scores[r['expected_full']])
    if not ranked:return {'status':'insufficient_evidence','placements':[]}
    strongest=scores[ranked[0]['expected_full']];near=[];seen=set()
    for row in ranked:
        if strongest-scores[row['expected_full']]>=math.log(2):break
        identity=(row['start'],row['end'],tuple(row['reference']))
        if identity not in seen:near.append(row);seen.add(identity)
    if len(near)>2:return {'status':'boundary_uncertain','placements':[]}
    return {'status':'placements','placements':near,'global_reference':ranked[0]}

def _hypotheses(reference,allowed,scope):
    result={}
    def add(observed):
        proposal=difference_proposal(reference,observed)
        if proposal is None:return
        positions=[]
        if proposal['kind']=='possible_substitution':positions=[i for i,(a,b) in enumerate(zip(reference,observed)) if a!=b]
        else:
            for i in range(len(reference)):
                if reference[:i]+reference[i+1:]==observed:positions.append(i)
                if i+1<len(reference) and reference[i] in CONSONANTS and reference[i]==reference[i+1] and reference[:i]+reference[i+2:]==observed:positions.extend((i,i+1))
        if scope=='keyword' and (0 in positions or len(reference)-1 in positions):return
        key=tuple(observed);signature=(proposal['kind'],tuple(proposal['expected_sounds']),tuple(proposal['alternative_sounds']))
        if key in result and result[key][1]!=signature:result[key]=(proposal,None)
        else:result[key]=(proposal,signature)
    for i in range(len(reference)):
        add(reference[:i]+reference[i+1:])
        if i+1<len(reference) and reference[i] in CONSONANTS and reference[i]==reference[i+1]:add(reference[:i]+reference[i+2:])
        for sound in allowed:
            if sound!=reference[i]:add(reference[:i]+(sound,)+reference[i+1:])
            if i+1<len(reference) and reference[i] in CONSONANTS and reference[i]==reference[i+1] and sound in CONSONANTS and sound!=reference[i]:
                add(reference[:i]+(sound,sound)+reference[i+2:])
    return [(seq,p,sig) for seq,(p,sig) in result.items() if seq and sig is not None]

def extract_lattice_evidence(probabilities,tokens,reference,decoded,scope,*,body_id,accepted_variants=(),score_paths=None):
    raw=list(decoded) if isinstance(decoded,(list,tuple)) else []
    base={'status':'insufficient_evidence','expected_sounds':[],'alternative_sounds':[],'confirmed':False,
          'clinical_assessment':False,'approved_for_child_scoring':False,'raw_phones':raw,'scope':scope,'body_id':body_id}
    p=None;lp=None
    try:
        p=np.array(probabilities,dtype=np.float64,copy=True);spans=free_unit_spans(p,tokens,raw)
        if spans is None:return base
        known=units(tokens);refs=list(dict.fromkeys([tuple(reference)]+[tuple(r) for r in accepted_variants]))
        limit=32 if scope=='complete_utterance' else 12
        if scope not in {'keyword','complete_utterance'}:return dict(base,status='unsupported_scope')
        if len(refs)>9 or any(not r or len(r)>limit or not set(r)<=set(known) for r in refs):return dict(base,status='unsupported_reference')
        if word_windows(reference,raw,scope,accepted_variants)['status']=='sequence_supported':
            return dict(base,status=exact_window_status(reference,raw,spans,scope,accepted_variants) or 'insufficient_evidence')
        if '|' in tokens:
            index=tokens.index('|');p[:,0]+=p[:,index];p[:,index]=0
        lp=np.log(np.maximum(p,1e-30))
        def score(sequences):
            sequences=list(dict.fromkeys(tuple(s) for s in sequences));paths=[];groups=[]
            for seq in sequences:
                native=native_sequences(seq,tokens);groups.append((len(paths),len(paths)+len(native)));paths.extend(native)
            if len(paths)>2048:raise ValueError('native_path_budget')
            values=score_paths(lp,paths,0) if score_paths else [ctc_log_probability(lp,path) for path in paths]
            if len(values)!=len(paths) or any(not math.isfinite(float(v)) or v>1e-3 for v in values):raise ValueError('invalid_ctc_scores')
            return {seq:float(np.logaddexp.reduce(values[a:b])) if a<b else -math.inf for seq,(a,b) in zip(sequences,groups)}
        placements=[]
        for ref in refs:
            lengths=[len(raw)] if scope=='complete_utterance' else range(max(1,len(ref)-2),min(len(raw),len(ref)+2)+1)
            for length in lengths:
                for start in range(len(raw)-length+1):
                    end=start+length
                    if scope=='complete_utterance' and (start or end!=len(raw)):continue
                    if len(raw)-length>16:continue
                    if ((start and spans[start-1]['native_group']==spans[start]['native_group']) or
                        (end<len(raw) and spans[end-1]['native_group']==spans[end]['native_group'])):continue
                    placements.append({'start':start,'end':end,'reference':ref,'expected_full':tuple(raw[:start])+ref+tuple(raw[end:])})
        if not placements:return dict(base,status='boundary_uncertain')
        reference_scores=score([r['expected_full'] for r in placements]+[raw]);free=reference_scores[tuple(raw)]
        placements.sort(key=lambda r:-reference_scores[r['expected_full']])
        global_expected=reference_scores[placements[0]['expected_full']]
        if not math.isfinite(global_expected) or not math.isfinite(free):return base
        choice=select_reference_placements(placements,reference_scores)
        if choice['status']!='placements':return dict(base,status=choice['status'])
        near=choice['placements']
        alternatives=[]
        for placement in near:
            start,end=placement['start'],placement['end'];first=spans[start]['start'];last=spans[end-1]['end']
            mass={u:0. for u in known}
            for j,token in enumerate(tokens):
                if token in SPECIAL:continue
                for u in COMPOUNDS.get(token,(token,)):mass[u]+=float(p[first:last,j].sum())
            allowed=set(sorted(known,key=lambda u:(-mass[u],u))[:8])|set(raw[start:end])
            for core,proposal,sig in _hypotheses(placement['reference'],allowed,scope):
                full=tuple(raw[:start])+core+tuple(raw[end:])
                if full not in [r['expected_full'] for r in near]:
                    alternatives.append(dict(placement,core=core,proposal=proposal,signature=sig,alternative_full=full))
        if not alternatives:return dict(base,status='boundary_uncertain') if scope=='keyword' else base
        if len(alternatives)>1024:return base
        alt_scores=score([r['alternative_full'] for r in alternatives])
        by_sequence={}
        for row in alternatives:
            by_sequence.setdefault(row['alternative_full'],set()).add(row['signature'])
        ranked=sorted(alternatives,key=lambda r:-alt_scores[r['alternative_full']])
        best=ranked[0];alternative=alt_scores[best['alternative_full']]
        if len(by_sequence[best['alternative_full']])!=1:return dict(base,status='ambiguous_placement')
        runner=max((alt_scores[r['alternative_full']] for r in ranked if r['signature']!=best['signature']),default=-math.inf)
        if not math.isfinite(alternative) or alternative-global_expected<math.log(2):return base
        if alternative-runner<math.log(2):return dict(base,status='ambiguous_placement')
        expected=reference_scores[best['expected_full']]
        start,end=best['start'],best['end'];core=spans[start:end];n=len(p);maximum=np.argmax(p,1);peaks=p[np.arange(n),maximum]
        left=core[0]['start']-(spans[start-1]['end'] if start else 0)
        right=(spans[end]['start'] if end<len(spans) else n)-core[-1]['end'];clip=lambda v:max(-100.,min(100.,v))
        features=[clip(expected)/len(best['expected_full']),clip(alternative)/len(best['alternative_full']),clip(expected)/n,clip(alternative)/n,
            clip(alternative-expected),clip(alternative-runner),clip(alternative-free),distance(best['reference'],raw[start:end])/len(best['reference']),
            distance(best['core'],raw[start:end])/len(best['core']),float(-(p*np.log(np.maximum(p,1e-30))).sum(1).mean()/math.log(len(tokens))),
            float(peaks.mean()),float(p[:,0].mean()),float((peaks<.5).mean()),min(s['confidence'] for s in core),
            float(np.mean([s['confidence'] for s in core])),left/n,right/n,n/150,len(best['reference'])/32,len(best['core'])/32,
            start/16,(len(raw)-end)/16,(core[0]['start']+core[-1]['end'])/(2*n),
            float(best['proposal']['kind']=='possible_omission'),float(best['proposal']['repeated_group']),float(scope=='complete_utterance'),
            clip(alternative-global_expected),clip(global_expected-expected)]
        features.extend(float(u in best['proposal']['expected_sounds']) for u in known)
        features.extend(float(u in best['proposal']['alternative_sounds']) for u in known)
        return dict(base,status='proposal',**best['proposal'],features=features,feature_names=lattice_feature_names(tokens),tokens=list(tokens),
                    observed_core=raw[start:end],alternative_hypothesis=list(best['core']),expected_full=list(best['expected_full']),
                    alternative_full=list(best['alternative_full']),core_unit_range=[start,end],
                    reference_log_probability=expected,global_reference_log_probability=global_expected,
                    global_reference_full=list(choice['global_reference']['expected_full']),alternative_log_probability=alternative,
                    approximate_frame_range=[core[0]['start'],core[-1]['end']])
    except (ValueError,TypeError,IndexError,KeyError,OverflowError):return base
    finally:
        if p is not None:p.fill(0)
        if lp is not None:lp.fill(0)


def apply_lattice_gate(evidence,model):
    base={'status':'insufficient_evidence',
          'expected_sounds':[],'alternative_sounds':[],'confirmed':False,'clinical_assessment':False,'approved_for_child_scoring':False}
    if not isinstance(evidence,dict):return dict(base,status='invalid_evidence')
    status=evidence.get('status')
    if status!='proposal':
        neutral={'insufficient_evidence','sequence_supported','unsupported_reference','unsupported_scope','boundary_uncertain',
                 'compound_boundary_uncertain','ambiguous_placement','outside_input_contract','invalid_evidence','invalid_model'}
        return dict(base,status=status if isinstance(status,str) and status in neutral else 'invalid_evidence')
    try:
        names=lattice_feature_names(evidence['tokens']);size=len(names)
        if (model['schema']!=MODEL_SCHEMA or model['reference_policy']!='partial_keyword_v2' or
            model['body_id']!=evidence['body_id'] or model['tokens']!=evidence['tokens'] or
            model['feature_names']!=names or evidence['feature_names']!=names or
            model['approved_for_child_scoring'] is not False or model['clinical_assessment'] is not False):raise ValueError()
        scopes=model['trained_scopes']
        if not isinstance(scopes,list) or not scopes or len(scopes)!=len(set(scopes)) or not set(scopes)<={'keyword','complete_utterance'}:raise ValueError()
        expected={'mean':(size,),'scale':(size,),'w1':(16,size),'b1':(16,),'w2':(16,)}
        arrays={k:np.asarray(model[k],dtype=np.float64) for k in expected}
        if any(v.shape!=expected[k] or not np.isfinite(v).all() for k,v in arrays.items()) or (arrays['scale']<=0).any():raise ValueError()
        bias=float(model['b2']);threshold=float(model['threshold'])
        if not math.isfinite(bias) or not math.isfinite(threshold) or not 0<=threshold<=1:raise ValueError()
        known=set(units(evidence['tokens']));supported=set();table=model['trained_contrasts']
        if not isinstance(table,list) or len(table)>1024:raise ValueError()
        for row in table:
            if not isinstance(row,dict) or set(row)!={'scope','kind','expected_sounds','alternative_sounds'}:raise ValueError()
            scope=row['scope'];kind=row['kind'];a=row['expected_sounds'];b=row['alternative_sounds']
            if (scope not in scopes or kind not in {'possible_omission','possible_substitution'} or
                not isinstance(a,list) or not isinstance(b,list) or len(a)!=1 or len(b)!=(kind=='possible_substitution') or
                any(not isinstance(s,str) or s not in known for s in a+b)):raise ValueError()
            signature=(scope,kind,tuple(a),tuple(b))
            if signature in supported:raise ValueError()
            supported.add(signature)
        signature=(evidence['scope'],evidence['kind'],tuple(evidence['expected_sounds']),tuple(evidence['alternative_sounds']))
        if signature not in supported:return base
        values=np.asarray(evidence['features'],dtype=np.float64)
        if values.shape!=(size,) or not np.isfinite(values).all():raise ValueError()
        with np.errstate(over='ignore',invalid='ignore',divide='ignore'):
            standardized=(values-arrays['mean'])/arrays['scale']
            if not np.isfinite(standardized).all():raise ValueError()
            preactivation=arrays['w1']@standardized+arrays['b1']
            if not np.isfinite(preactivation).all():raise ValueError()
            hidden=np.maximum(0,preactivation)
            score=float(arrays['w2']@hidden)+bias
            if not math.isfinite(score):raise ValueError()
        confidence=1/(1+math.exp(-max(-80.,min(80.,score))))
        if confidence<threshold:return dict(base,engineering_confidence=confidence)
        return dict(base,status=evidence['kind'],expected_sounds=evidence['expected_sounds'],
                    alternative_sounds=evidence['alternative_sounds'],engineering_confidence=confidence)
    except (KeyError,ValueError,TypeError,OverflowError):return dict(base,status='invalid_model')

