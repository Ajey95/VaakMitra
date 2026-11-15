"""DEC068/PHN009: transient sequence hypotheses and bounded, optional help.

This runs after acoustic decoding. A difference from a provisional reference is
never a verified child error; no alignment feeds back into the recognizer.
"""
from dataclasses import dataclass
from collections.abc import Sequence


@dataclass(frozen=True)
class PhoneticSupport:
    action: str
    candidate_patterns: tuple[str, ...] = ()
    decision: str = 'UNSCORABLE'
    basis: str = 'generic_help'


def _patterns(observed, reference):
    # Carry all equally minimal edit interpretations. Repeated letters can make
    # positions ambiguous; we only need agreement on the kind of optional help.
    previous=[(j,{frozenset({'possible_omission'}) if j else frozenset()})
              for j in range(len(reference)+1)]
    for i,phone in enumerate(observed,1):
        repeated=(i>1 and observed[i-2]==phone) or (i<len(observed) and observed[i]==phone)
        inserted='possible_repetition' if repeated else 'unsupported_insertion'
        row=[(i,{signature|{inserted} for signature in previous[0][1]})]
        for j,target in enumerate(reference,1):
            candidates=[]
            for cost,signatures,extra in (
                (*previous[j],inserted),(*row[j-1],'possible_omission'),
                (*previous[j-1],None if phone==target else 'possible_substitution'),
            ):
                candidates.append((cost+(extra is not None),
                    {signature|({extra} if extra else set()) for signature in signatures}))
            best=min(cost for cost,_ in candidates)
            row.append((best,set().union(*(s for c,s in candidates if c==best))))
        previous=row
    signatures=previous[-1][1]
    if len(signatures)!=1:return ()
    signature=next(iter(signatures))
    if 'unsupported_insertion' in signature:return ()
    return tuple(sorted(signature))


def choose_phonetic_support(observed, reference, *, known_tokens,
        evidence_valid=False, model_qualified=False, allowed_actions=('adult_example','picture','repeat','break'),
        stop_requested=False, break_requested=False, attempt_count=0, max_retries=2):
    """Return no raw phones, score, diagnosis or forced retry. Caller owns erasure.

    model_qualified means the selected engineering model passed its checks; it
    does not mean child validation. evidence_valid must come from capture/model
    checks, never merely from a close match to the expected word.
    """
    if stop_requested:return PhoneticSupport('safe_end',basis='stop_requested')
    allowed=set(allowed_actions)&{'adult_example','picture','repeat','break','safe_end'}
    if break_requested or attempt_count>=max_retries:
        return PhoneticSupport('break' if 'break' in allowed else 'safe_end',basis='session_limit')
    action=next((a for a in ('adult_example','picture','repeat') if a in allowed),'none')
    def valid(sequence):
        return (isinstance(sequence,Sequence) and not isinstance(sequence,(str,bytes))
            and 0<len(sequence)<=64 and all(isinstance(p,str) and p in known_tokens
                and p not in ('<blank>','[PAD]','[UNK]','|','்') for p in sequence))
    if not evidence_valid or not model_qualified or not valid(observed) or not valid(reference):
        return PhoneticSupport(action)
    if list(observed)==list(reference):
        return PhoneticSupport('none',basis='sequence_agreement_only')
    patterns=_patterns(observed,reference)
    return PhoneticSupport(action,patterns,basis='unvalidated_sequence_hypothesis' if patterns else 'generic_help')
