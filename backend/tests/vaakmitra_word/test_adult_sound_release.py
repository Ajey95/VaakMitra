"""DEC072: a synthetic/runtime subgate never bypasses natural or native gates."""
from app.vaakmitra_word.adult_sound_release import guidance_release_decision


def valid():
    return dict(protocol_conformant=True,native_parity_passed=True,
                calibration={'positive':8,'false_corrections_positive':0},
                baseline={'positive':8,'negative':16,'false_corrections_positive':2,'correct_error_attributions':1,'wrong_error_attributions':1},
                candidate={'positive':8,'negative':16,'false_corrections_positive':0,'correct_error_attributions':2,'wrong_error_attributions':0},
                natural={'all_rows':24,'inferred':24,'own_target_false_alerts':0},public_controls_passed=True)


def test_dec072_natural_false_alert_blocks_even_otherwise_passing_candidate():
    data=valid();data['natural']['own_target_false_alerts']=1
    result=guidance_release_decision(**data)
    assert result['qualified'] is False and 'natural_own_target_alert' in result['failed_gates']


def test_dec072_protocol_native_missing_rows_and_failed_gain_all_block():
    for key,value in [('protocol_conformant',False),('native_parity_passed',False),('public_controls_passed',False)]:
        data=valid();data[key]=value;assert guidance_release_decision(**data)['qualified'] is False
    data=valid();data['natural']['inferred']=23;assert guidance_release_decision(**data)['qualified'] is False
    data=valid();data['candidate']['correct_error_attributions']=1;assert guidance_release_decision(**data)['qualified'] is False


def test_dec072_all_engineering_gates_still_never_grant_clinical_scoring():
    result=guidance_release_decision(**valid())
    assert result['qualified'] is True
    assert result['clinical_assessment'] is False and result['approved_for_child_scoring'] is False


def test_dec072_missing_or_empty_denominators_cannot_qualify():
    for source,key in [('calibration','positive'),('candidate','positive'),('candidate','negative')]:
        data=valid();data[source].pop(key)
        assert guidance_release_decision(**data)['qualified'] is False
