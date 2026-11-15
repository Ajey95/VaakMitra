"""DEC072/COA002: combined engineering release gate, separate from recognition."""


def guidance_release_decision(*,protocol_conformant=False,native_parity_passed=False,
                             calibration=None,baseline=None,candidate=None,natural=None,
                             public_controls_passed=False):
    """Consume clean synthetic counts and natural own-target controls; fail closed.

    A result only concerns a benign demonstration candidate. It never enables
    clinical assessment, child scoring, or rewrites phoneme predictions.
    """
    calibration=calibration or {};baseline=baseline or {};candidate=candidate or {};natural=natural or {}
    def number(source,key):
        value=source.get(key)
        return value if type(value) is int and value>=0 else None
    failures=[]
    if protocol_conformant is not True:failures.append('protocol_deviation')
    if native_parity_passed is not True:failures.append('native_parity_unverified')
    if public_controls_passed is not True:failures.append('public_controls_unverified')
    calibration_positive=number(calibration,'positive')
    populations=[(number(panel,'positive'),number(panel,'negative')) for panel in (baseline,candidate)]
    if (calibration_positive is None or calibration_positive<1 or
        any(p is None or n is None or p<1 or n<1 for p,n in populations) or populations[0]!=populations[1]):
        failures.append('clean_denominators_invalid')
    if number(calibration,'false_corrections_positive')!=0:failures.append('calibration_target_alert')
    if number(candidate,'false_corrections_positive')!=0:failures.append('clean_target_alert')
    old=number(baseline,'correct_error_attributions');new=number(candidate,'correct_error_attributions')
    if old is None or new is None or new<=old:failures.append('no_localization_improvement')
    old_wrong=number(baseline,'wrong_error_attributions');new_wrong=number(candidate,'wrong_error_attributions')
    if old_wrong is None or new_wrong is None or new_wrong>old_wrong:failures.append('extra_wrong_attribution')
    total=number(natural,'all_rows');inferred=number(natural,'inferred')
    if total is None or total<1 or inferred!=total:failures.append('natural_controls_incomplete')
    if number(natural,'own_target_false_alerts')!=0:failures.append('natural_own_target_alert')
    return {'qualified':not failures,'failed_gates':failures,
            'clinical_assessment':False,'approved_for_child_scoring':False,
            'scope':'benign demonstration engineering gate only'}
