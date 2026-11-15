"""DEC068/PHN009: acoustic comparisons are transient hypotheses, never child scores."""
from app.vaakmitra_word.phonetic_support import choose_phonetic_support

KNOWN=frozenset(('a','aː','m','p','n','i','iː'))

def choose(observed,reference,**options):
    return choose_phonetic_support(observed,reference,known_tokens=KNOWN,
        evidence_valid=True,model_qualified=True,**options)

def test_normal_tamil_gemination_and_long_vowels_are_preserved():
    result=choose(['a','m','m','aː'],['a','m','m','aː'])
    assert result.candidate_patterns==()
    assert result.action=='none'
    assert result.decision=='UNSCORABLE'
    assert choose(['a'],['aː']).candidate_patterns==('possible_substitution',)

def test_extra_repetition_is_distinct_from_normal_gemination():
    assert choose(['a','m','m','m','aː'],['a','m','m','aː']).candidate_patterns==('possible_repetition',)
    assert choose(['a','m','aː'],['a','m','m','aː']).candidate_patterns==('possible_omission',)
    assert choose(['a','p','aː'],['a','m','aː']).candidate_patterns==('possible_substitution',)

def test_invalid_unqualified_or_ambiguous_evidence_gets_generic_help():
    for observed,reference,options in [
        ([],['a'],{}),(['[UNK]'],['a'],{}),(['a']*65,['a'],{}),
        (['a'],['a'],{'evidence_valid':False}),
        (['a'],['a'],{'model_qualified':False}),
        # Two equally minimal alignments imply different edit interpretations.
        (['m','a'],['a','m'],{}),
        # A later repeated prefix must not erase earlier unsupported insertions.
        (['a','m','m','n'],['n'],{}),
    ]:
        args=dict(evidence_valid=True,model_qualified=True);args.update(options)
        result=choose_phonetic_support(observed,reference,known_tokens=KNOWN,**args)
        assert result.candidate_patterns==()
        assert result.action=='adult_example'
        assert result.decision=='UNSCORABLE'

def test_stop_break_and_constraints_override_all_hypotheses():
    assert choose(['a'],['m'],stop_requested=True).action=='safe_end'
    assert choose(['a'],['m'],break_requested=True).action=='break'
    assert choose(['a'],['m'],attempt_count=2,max_retries=2).action=='break'
    assert choose(['a'],['m'],allowed_actions=('picture',)).action=='picture'
    assert choose(['a'],['m'],allowed_actions=()).action=='none'

def test_result_does_not_retain_raw_tokens_or_claim_correctness():
    result=choose(['a'],['m'])
    assert set(vars(result))=={'action','candidate_patterns','decision','basis'}
    assert result.basis=='unvalidated_sequence_hypothesis'
    assert not any(x in vars(result) for x in ('score','mastery','observed','reference','diagnosis'))
