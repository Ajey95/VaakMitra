"""DEC071/PHN012: pause processing and reference diagnostics cannot create correctness."""
import numpy as np
import pytest
from app.vaakmitra_word.pause_alignment import compact_pauses, align_posteriors, coaching_tool_result


TOKENS=['<blank>','a','aː','m','s','ʂ','[UNK]']


def posterior(indices):
    values=np.full((len(indices),len(TOKENS)),.001,dtype=np.float32)
    for i,j in enumerate(indices):values[i,j]=.994
    return values/values.sum(axis=1,keepdims=True)


def test_phn012_removes_only_long_interior_pause_and_preserves_sample_mapping():
    voiced=np.full(3200,.1,dtype=np.float32)
    wave=np.concatenate([voiced,np.zeros(16000,dtype=np.float32),voiced])
    result=compact_pauses(wave)
    assert result.removed_samples==12800
    assert len(result.samples)==9600
    restored=np.concatenate([wave[a:b] for a,b in result.retained_ranges])
    np.testing.assert_array_equal(restored,result.samples)
    np.testing.assert_array_equal(result.samples[:3200],voiced)
    np.testing.assert_array_equal(result.samples[-3200:],voiced)


def test_phn012_retains_quiet_consonants_short_gaps_and_edges():
    wave=np.concatenate([np.zeros(8000),np.full(3200,.2),np.full(8000,.0008),np.full(3200,.2),np.zeros(8000)]).astype(np.float32)
    result=compact_pauses(wave)
    assert result.removed_samples==0
    np.testing.assert_array_equal(result.samples,wave)


def test_phn012_all_quiet_or_silent_is_not_shortened_into_a_word():
    for wave in [np.zeros(16000,dtype=np.float32),np.full(16000,.00001,dtype=np.float32)]:
        assert compact_pauses(wave).removed_samples==0


def test_phn012_nonfinite_or_nonmono_audio_rejected():
    for wave in [np.array([np.nan]*400),np.zeros((2,400))]:
        with pytest.raises(ValueError):compact_pauses(wave)


def test_phn012_stretch_and_blank_pauses_preserve_reference_support():
    result=align_posteriors(posterior([1]*8+[0]*20+[3]*6+[0]*5+[2]*10),TOKENS,['a','m','aː'])
    assert result['status']=='diagnostic_only'
    assert [x['kind'] for x in result['phones']]==['model_support']*3
    assert result['phones'][1]['start_frame']==28
    assert result['child_correctness'] is None


def test_phn012_geminates_and_long_vowels_are_not_collapsed():
    result=align_posteriors(posterior([1,1,0,3,3,0,3,3,0,2,2]),TOKENS,['a','m','m','aː'])
    assert [x['observed'] for x in result['phones']]==['a','m','m','aː']
    assert result['observed_sequence']==['a','m','m','aː']


def test_phn012_missing_phone_is_hypothesis_not_confirmed_child_omission():
    result=align_posteriors(posterior([1]*5+[0]*3+[2]*5),TOKENS,['a','m','aː'])
    missing=[r for r in result['phones'] if r['kind']=='possible_omission']
    assert len(missing)==1 and missing[0]['expected']=='m'
    assert missing[0]['confirmed'] is False


def test_phn012_unsupported_sh_and_silence_abstain():
    assert align_posteriors(posterior([4]*6),TOKENS,['ʃ'])['status']=='unsupported_reference'
    assert align_posteriors(posterior([0]*10),TOKENS,['m'])['status']=='insufficient_evidence'


def test_phn012_invalid_posteriors_rejected_and_uncertain_rows_not_asserted():
    with pytest.raises(ValueError):align_posteriors(np.array([[np.nan]*7]),TOKENS,['a'])
    uniform=np.full((5,7),1/7,dtype=np.float32)
    assert align_posteriors(uniform,TOKENS,['a'])['status']=='insufficient_evidence'


def test_coa002_failed_adult_gate_suppresses_tool_hypotheses_and_keeps_neutral_help():
    alignment=align_posteriors(posterior([1]*4+[0]*3+[2]*4),TOKENS,['a','m','aː'])
    result=coaching_tool_result('TA_WORD_0001',alignment,['low_recording_level'])
    assert result['schema']=='vaakmitra.speech_analysis.v1'
    assert result['local_only'] is True
    assert result['child_correctness'] is None
    assert result['clinical_assessment'] is False
    assert 'claim_child_error' in result['forbidden_actions']
    assert 'demonstrate_target' in result['allowed_actions']
    assert result['possible_sound_differences']==[]
    assert result['evidence_status']=='insufficient_evidence'


def test_coa001_no_recording_voice_features_or_unvalidated_identifiers_in_tool_result():
    import json
    alignment=align_posteriors(posterior([1]*4+[0]*3+[2]*4),TOKENS,['a','m','aː'])
    rendered=json.dumps(coaching_tool_result('TA_WORD_0001',alignment))
    for key in ['observed_sequence','observed','audio_path','pcm','embedding','spectrogram','transcript','speaker_id']:
        assert '"'+key+'"' not in rendered
    with pytest.raises(ValueError):coaching_tool_result('private recording filename',alignment)


def test_phn012_native_compounds_abstain_instead_of_inventing_split_phone_omissions():
    tokens=['<blank>','k','a','j','aj']
    p=np.full((4,5),.001,dtype=np.float32);p[:2,1]=.996;p[2:,4]=.996
    result=align_posteriors(p,tokens,['k','a','j'])
    assert result['status']=='insufficient_evidence' and result['phones']==[]


def test_phn012_tied_optimal_sound_attributions_abstain():
    result=align_posteriors(posterior([4]),TOKENS,['a','m'])
    assert result['status']=='ambiguous_alignment' and result['phones']==[]


def test_coa001_tool_contract_rejects_free_text_values_and_abstention_hypotheses():
    with pytest.raises(ValueError):coaching_tool_result('TA_WORD_9999',{})
    malicious={'status':'private filename.wav','phones':[{'expected':'secret transcript','kind':'possible_omission'}]}
    safe=coaching_tool_result('TA_WORD_0001',malicious)
    assert safe['evidence_status']=='insufficient_evidence' and safe['possible_sound_differences']==[]
    safe=coaching_tool_result('TA_WORD_0001',{'status':'insufficient_evidence','phones':[{'expected':'m','kind':'possible_omission'}]})
    assert safe['possible_sound_differences']==[]


def test_phn012_inactive_energy_candidate_has_documented_weak_sound_limit():
    wave=np.concatenate([np.full(3200,.2),np.full(6400,.0003),np.full(3200,.2)]).astype(np.float32)
    # This known limitation is why energy compaction cannot prove a child pause.
    assert compact_pauses(wave).removed_samples==3200
