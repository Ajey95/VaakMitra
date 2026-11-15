"""DEC077/PHN018: reference scope and raw-derived spans, never forced recognition."""
from __future__ import annotations
import math
import numpy as np
from .adult_sound_evidence import COMPOUNDS,SPECIAL,native_sequences
from .real_adult_sound import CONSONANTS,difference_proposal

def _phones(value,maximum=32):
    return isinstance(value,(list,tuple)) and 0<len(value)<=maximum and all(isinstance(x,str) and x and x not in SPECIAL for x in value)

def lexical_neighbors(actual,sequences,known):
    """Bounded edit queries avoid an index proportional to every lexicon position."""
    if not _phones(actual) or len(known)>64:return []
    actual=tuple(actual);candidates=set()
    for i in range(len(actual)+1):
        for sound in known:
            candidate=actual[:i]+(sound,)+actual[i:]
            if candidate in sequences:candidates.add(candidate)
            if sound in CONSONANTS:
                candidate=actual[:i]+(sound,sound)+actual[i:]
                if candidate in sequences:candidates.add(candidate)
            if i<len(actual) and sound!=actual[i]:
                candidate=actual[:i]+(sound,)+actual[i+1:]
                if candidate in sequences:candidates.add(candidate)
                if i+1<len(actual) and actual[i] in CONSONANTS and actual[i]==actual[i+1] and sound in CONSONANTS:
                    candidate=actual[:i]+(sound,sound)+actual[i+2:]
                    if candidate in sequences:candidates.add(candidate)
    return sorted(c for c in candidates if difference_proposal(c,actual) is not None)

def build_reference_record(row,phones,review=None):
    if not isinstance(row,dict) or not _phones(phones):raise ValueError('reference_fields')
    source=row.get('source_id','');segmented=row.get('provenance_kind')=='segmented'
    keyword=source=='mlcommons-mswc-ta' or segmented
    complete=source in {'openslr-65-ta','openslr-127-mile-ta'} and row.get('provenance_kind')=='original' and bool(row.get('transcript'))
    scope='keyword' if keyword else 'complete_utterance' if complete else 'unverified'
    actual=None;provenance=None
    if review is not None:
        if (not isinstance(review,dict) or review.get('source_id')!=row.get('sample_id') or
            review.get('owner_confirmed_free_tokens') is not True or not _phones(review.get('owner_confirmed_spoken_phones'))):
            raise ValueError('owner_review_identity_or_content')
        actual=list(review['owner_confirmed_spoken_phones']);provenance='owner_confirmed_existing_model_draft'
    return {'schema':'vaakmitra.reference_scope.v2','source_id':row.get('sample_id'),'word_label':row.get('transcript'),
            'scope':scope,'intended_phones':list(phones),'owner_reviewed_actual_phones':actual,'actual_provenance':provenance,
            'boundary_provenance':'machine_alignment' if segmented else 'fixed_keyword_window' if keyword else 'source_utterance' if complete else 'unverified',
            'eligible_for_whole_clip_ctc':scope=='complete_utterance','independently_verified_phonetic_reference':False}

def _changed_positions(reference,observed,kind):
    positions=set();m=len(reference)
    if kind=='possible_substitution':
        positions.update(i for i,(a,b) in enumerate(zip(reference,observed)) if a!=b)
    else:
        for i in range(m):
            if reference[:i]+reference[i+1:]==observed:positions.add(i)
            if i+1<m and reference[i] in CONSONANTS and reference[i]==reference[i+1] and reference[:i]+reference[i+2:]==observed:
                positions.update((i,i+1))
    return sorted(positions)

def is_interior_difference(reference,observed):
    if not _phones(reference) or not _phones(observed):return False
    proposal=difference_proposal(tuple(reference),tuple(observed))
    if proposal is None:return False
    positions=_changed_positions(tuple(reference),tuple(observed),proposal['kind'])
    return bool(positions) and 0 not in positions and len(reference)-1 not in positions

def exact_window_status(reference,decoded,spans,scope,accepted_variants=()):
    """An exact canonical substring must also respect native compound atomicity."""
    if len(spans)!=len(decoded):return None
    blocked=False
    for ref in [tuple(reference)]+[tuple(r) for r in accepted_variants]:
        for start in range(len(decoded)-len(ref)+1):
            end=start+len(ref)
            if tuple(decoded[start:end])!=ref:continue
            if scope=='complete_utterance' and (start or end!=len(decoded)):continue
            if scope=='keyword' and len(decoded)-len(ref)>16:continue
            if ((start and spans[start-1]['native_group']==spans[start]['native_group']) or
                (end<len(decoded) and spans[end-1]['native_group']==spans[end]['native_group'])):
                blocked=True;continue
            return 'sequence_supported'
    return 'compound_boundary_uncertain' if blocked else None

def word_windows(reference,decoded,scope,accepted_variants=()):
    raw=list(decoded) if isinstance(decoded,(list,tuple)) else [];base={'status':'insufficient_evidence','raw_phones':raw,'candidates':[]}
    if scope not in {'keyword','complete_utterance'}:return dict(base,status='unsupported_scope')
    limit=32 if scope=='complete_utterance' else 12
    if (not _phones(reference,limit) or not _phones(decoded) or not isinstance(accepted_variants,(list,tuple)) or
        len(accepted_variants)>8 or any(not _phones(r,limit) for r in accepted_variants)):return base
    references=list(dict.fromkeys([tuple(reference)]+[tuple(r) for r in accepted_variants]))
    for ref in references:
        if scope=='complete_utterance':
            if tuple(raw)==ref:return dict(base,status='sequence_supported')
        elif any(tuple(raw[start:start+len(ref)])==ref and len(raw)-len(ref)<=16 for start in range(len(raw)-len(ref)+1)):
            return dict(base,status='sequence_supported')
    candidates=[];seen=set();edge=False
    for ref in references:
        for length in set((len(ref),len(ref)-1,len(ref)-2)):
            if length<1 or length>len(raw):continue
            for start in range(len(raw)-length+1):
                end=start+length
                if scope=='complete_utterance' and (start!=0 or end!=len(raw)):continue
                if len(raw)-length>16:continue
                core=tuple(raw[start:end]);proposal=difference_proposal(ref,core)
                if proposal is None:continue
                changed=_changed_positions(ref,core,proposal['kind'])
                if not changed:continue
                if scope=='keyword' and (0 in changed or len(ref)-1 in changed):
                    edge=True;continue
                expected_full=raw[:start]+list(ref)+raw[end:]
                signature=(tuple(expected_full),proposal['kind'],tuple(proposal['expected_sounds']),tuple(proposal['alternative_sounds']),start,end)
                if signature in seen:continue
                seen.add(signature)
                candidates.append(dict(proposal,start=start,end=end,reference=list(ref),core=list(core),changed_positions=changed,expected_full=expected_full))
    if len(candidates)>96:return base
    return dict(base,status='candidates' if candidates else 'boundary_uncertain' if edge else 'insufficient_evidence',candidates=candidates)

def _viterbi(lp,target):
    if not target:return None
    states=np.zeros(2*len(target)+1,dtype=np.int64);states[1::2]=target
    previous=np.full(len(states),-np.inf);previous[0]=lp[0,0];previous[1]=lp[0,target[0]]
    back=np.full((len(lp),len(states)),-1,dtype=np.int16)
    skip=np.zeros(len(states),dtype=bool);skip[2:]=(states[2:]!=0)&(states[2:]!=states[:-2])
    for frame in range(1,len(lp)):
        step=np.concatenate(([-np.inf],previous[:-1]))
        jump=np.concatenate(([-np.inf,-np.inf],previous[:-2]));jump[~skip]=-np.inf
        choices=np.stack((previous,step,jump));move=np.argmax(choices,axis=0)
        back[frame]=np.arange(len(states))-move
        previous=choices[move,np.arange(len(states))]+lp[frame,states]
    end=len(states)-1 if previous[-1]>previous[-2] else len(states)-2
    score=float(previous[end])
    if not math.isfinite(score):return None
    path=np.empty(len(lp),dtype=np.int16);path[-1]=end
    for frame in range(len(lp)-1,0,-1):path[frame-1]=back[frame,path[frame]]
    spans=[]
    for index in range(len(target)):
        locations=np.flatnonzero(path==2*index+1)
        if not len(locations):return None
        spans.append((int(locations[0]),int(locations[-1])+1))
    return score,spans

def free_unit_spans(probabilities,tokens,decoded):
    """Align only an already independently decoded sequence. Spikes are not phonetic boundaries."""
    p=np.array(probabilities,dtype=np.float64,copy=True);lp=None
    try:
        if (p.ndim!=2 or not 1<=len(p)<=400 or not tokens or tokens[0]!='<blank>' or
            p.shape[1]!=len(tokens) or len(set(tokens))!=len(tokens) or not np.isfinite(p).all() or
            (p<0).any() or (p>1).any() or not np.allclose(p.sum(1),1,atol=1e-4) or not _phones(decoded)):return None
        if any(np.any(p[:,i]>=.5) for i,t in enumerate(tokens) if t in {'[UNK]','[PAD]','்'}):return None
        maxima=np.argmax(p,axis=1)
        if sum(tokens[int(i)] not in SPECIAL and p[f,i]>=.5 for f,i in enumerate(maxima))<2:return None
        if '|' in tokens:
            sep=tokens.index('|');p[:,0]+=p[:,sep];p[:,sep]=0
        lp=np.log(np.maximum(p,1e-30));best=None
        for path in native_sequences(decoded,tokens):
            aligned=_viterbi(lp,path)
            if aligned is None:continue
            score,spans=aligned
            result=[]
            for group,(token,(start,end)) in enumerate(zip(path,spans)):
                for unit in COMPOUNDS.get(tokens[token],(tokens[token],)):
                    result.append({'unit':unit,'start':start,'end':end,'native_group':group,'native_token':tokens[token],
                                   'confidence':float(p[start:end,token].max())})
            if best is None or score>best[0]:best=(score,result)
        return best[1] if best else None
    except (ValueError,TypeError,IndexError,OverflowError):return None
    finally:
        p.fill(0)
        if lp is not None:lp.fill(0)

