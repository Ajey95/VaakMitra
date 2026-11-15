"""DEC077/PHN018: same-context CTC evidence, separate from unrestricted decoding."""
from __future__ import annotations
import math
import numpy as np
from .adult_sound_evidence import SPECIAL,native_sequences,ctc_log_probability
from .real_adult_sound import units
from .reference_boundaries import free_unit_spans,word_windows,exact_window_status

BASE_FEATURES=['reference_full_per_phone','observed_full_per_phone','log_margin','margin_per_core_phone','placement_margin',
               'minimum_core_peak','mean_core_peak','entropy','mean_peak','mean_blank','uncertain_fraction',
               'reference_core_length','observed_core_length','context_before','context_after','core_midpoint',
               'left_gap','right_gap','frames','omission','repeated_group','complete_scope','greedy_core_agreement']

def feature_names(tokens):
    known=units(tokens)
    return BASE_FEATURES+[f'expected:{p}' for p in known]+[f'alternative:{p}' for p in known]

def extract_contextual_evidence(probabilities,tokens,reference,decoded,scope,*,body_id,accepted_variants=(),score_paths=None):
    raw=list(decoded) if isinstance(decoded,(list,tuple)) else []
    base={'status':'insufficient_evidence','expected_sounds':[],'alternative_sounds':[],'confirmed':False,
          'clinical_assessment':False,'approved_for_child_scoring':False,'raw_phones':raw,'scope':scope,'body_id':body_id}
    p=None;lp=None
    try:
        p=np.array(probabilities,dtype=np.float64,copy=True)
        spans=free_unit_spans(p,tokens,raw)
        if spans is None:return base
        known=set(units(tokens));refs=[reference]+list(accepted_variants)
        if any(not isinstance(r,(list,tuple)) or not set(r)<=known for r in refs):return dict(base,status='unsupported_reference')
        windows=word_windows(reference,raw,scope,accepted_variants)
        if windows['status']=='sequence_supported':
            return dict(base,status=exact_window_status(reference,raw,spans,scope,accepted_variants) or 'insufficient_evidence')
        if windows['status']!='candidates':return dict(base,status=windows['status'])
        candidates=[];compound_rejected=False
        for candidate in windows['candidates']:
            start,end=candidate['start'],candidate['end']
            if ((start and spans[start-1]['native_group']==spans[start]['native_group']) or
                (end<len(spans) and spans[end-1]['native_group']==spans[end]['native_group'])):
                compound_rejected=True;continue
            if min(s['confidence'] for s in spans[start:end])<.2:continue
            candidates.append(candidate)
        if not candidates:return dict(base,status='compound_boundary_uncertain') if compound_rejected else base
        if '|' in tokens:
            index=tokens.index('|');p[:,0]+=p[:,index];p[:,index]=0
        lp=np.log(np.maximum(p,1e-30))
        sequences=list(dict.fromkeys([tuple(raw)]+[tuple(c['expected_full']) for c in candidates]))
        paths=[];groups=[]
        for sequence in sequences:
            native=native_sequences(sequence,tokens);groups.append((len(paths),len(paths)+len(native)));paths.extend(native)
        if len(paths)>2048:return base
        scores=score_paths(lp,paths,0) if score_paths else [ctc_log_probability(lp,path) for path in paths]
        if len(scores)!=len(paths) or any(not math.isfinite(float(v)) or v>1e-3 for v in scores):return base
        values={sequence:float(np.logaddexp.reduce(scores[a:b])) if a<b else -math.inf for sequence,(a,b) in zip(sequences,groups)}
        observed=values[tuple(raw)]
        ranked=sorted(candidates,key=lambda c:-values[tuple(c['expected_full'])])
        best=ranked[0];expected=values[tuple(best['expected_full'])]
        signature=lambda c:(c['kind'],tuple(c['expected_sounds']),tuple(c['alternative_sounds']))
        runner=max((values[tuple(c['expected_full'])] for c in ranked if signature(c)!=signature(best)),default=-math.inf)
        if not all(math.isfinite(v) for v in [observed,expected]) or observed-expected<math.log(2):return base
        if expected-runner<math.log(2):return dict(base,status='ambiguous_placement')
        start,end=best['start'],best['end'];core=spans[start:end];length=len(p)
        maxima=np.argmax(p,axis=1);peaks=p[np.arange(length),maxima]
        greedy=[];last=None
        from .adult_sound_evidence import COMPOUNDS
        for i in range(core[0]['start'],core[-1]['end']):
            token=tokens[int(maxima[i])]
            if token not in {'<blank>','|'} and int(maxima[i])!=last:greedy.extend(COMPOUNDS.get(token,(token,)))
            last=int(maxima[i])
        clip=lambda v:max(-100.,min(100.,v))
        left=core[0]['start']-(spans[start-1]['end'] if start else 0)
        right=(spans[end]['start'] if end<len(spans) else length)-core[-1]['end']
        features=[clip(expected)/len(best['expected_full']),clip(observed)/len(raw),clip(observed-expected),
                  clip(observed-expected)/len(core),clip(expected-runner),min(s['confidence'] for s in core),
                  float(np.mean([s['confidence'] for s in core])),float(-(p*np.log(np.maximum(p,1e-30))).sum(1).mean()/math.log(len(tokens))),
                  float(peaks.mean()),float(p[:,0].mean()),float((peaks<.5).mean()),len(best['reference'])/32,
                  len(core)/32,start/16,(len(raw)-end)/16,(core[0]['start']+core[-1]['end'])/(2*length),
                  left/length,right/length,length/150,float(best['kind']=='possible_omission'),float(best['repeated_group']),
                  float(scope=='complete_utterance'),float(greedy==best['core'])]
        known_list=units(tokens)
        features.extend(float(u in best['expected_sounds']) for u in known_list)
        features.extend(float(u in best['alternative_sounds']) for u in known_list)
        return dict(base,status='proposal',kind=best['kind'],expected_sounds=best['expected_sounds'],
                    alternative_sounds=best['alternative_sounds'],repeated_group=best['repeated_group'],
                    features=features,feature_names=feature_names(tokens),tokens=list(tokens),core=best['core'],
                    expected_full=best['expected_full'],core_unit_range=[start,end],
                    approximate_frame_range=[core[0]['start'],core[-1]['end']])
    except (ValueError,TypeError,IndexError,OverflowError,KeyError):return base
    finally:
        if p is not None:p.fill(0)
        if lp is not None:lp.fill(0)

def apply_contextual_gate(evidence,model):
    base={'status':'insufficient_evidence',
          'expected_sounds':[],'alternative_sounds':[],'confirmed':False,'clinical_assessment':False,'approved_for_child_scoring':False}
    if not isinstance(evidence,dict):return dict(base,status='invalid_evidence')
    status=evidence.get('status')
    if status!='proposal':
        neutral={'insufficient_evidence','sequence_supported','unsupported_reference','unsupported_scope','boundary_uncertain',
                 'compound_boundary_uncertain','ambiguous_placement','outside_input_contract','invalid_evidence','invalid_model'}
        return dict(base,status=status if isinstance(status,str) and status in neutral else 'invalid_evidence')
    try:
        names=feature_names(evidence['tokens']);size=len(names)
        if (model['schema']!='vaakmitra.contextual_sound.v1' or model['reference_policy']!='partial_keyword_v2' or
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

