"""DEC077/PHN018: release accounting and runtime identity fail closed."""
import copy
import pytest

def metric(own=20,total=80,each=25,wrong=0,own_alerts=0):
    return {'rows':own+total,'own_targets':own,'own_target_alerts':own_alerts,'changed_cases':total,'correct_differences':2*each,'wrong_attributions':wrong,
            'possible_omission':{'total':total//2,'correct':each},'possible_substitution':{'total':total//2,'correct':each}}

def summary():
    return {'keyword':{'candidate':metric(),'interior_candidate':metric(total=40,each=13),'interior_baseline':metric(total=40,each=9)},
            'complete_source':{'candidate':metric(own=5,total=10,each=1)},
            'secondary':{'quiet':{'candidate':metric(own=5,total=10,each=1)},'pause':{'candidate':metric(own=5,total=10,each=1)}}}

def test_correct_interior_cannot_hide_wrong_edge_attribution():
    from app.vaakmitra_word.boundary_release import qualify_boundary_results
    data=summary()
    assert qualify_boundary_results(data,True)['whole_panel_gate_passed']
    data['keyword']['candidate']['wrong_attributions']=1
    result=qualify_boundary_results(data,True)
    assert not result['whole_panel_gate_passed'] and not result['interior_lexical_gate_passed']
    assert 'keyword_wrong_attributions' in result['failures']

@pytest.mark.parametrize('control',['complete_source','quiet','pause'])
def test_controls_have_separate_false_attribution_dispositions(control):
    from app.vaakmitra_word.boundary_release import qualify_boundary_results
    data=summary();item=data['complete_source'] if control=='complete_source' else data['secondary'][control]
    item['candidate']['own_target_alerts']=1
    result=qualify_boundary_results(data,True)
    assert not result['control_safety_gate_passed'] and not result['whole_panel_gate_passed']

def test_missing_and_invalid_denominators_cannot_pass():
    from app.vaakmitra_word.boundary_release import qualify_boundary_results
    data=summary();data['secondary']['quiet']['candidate']['own_targets']=0
    assert not qualify_boundary_results(data,True)['whole_panel_gate_passed']
    data=summary();data['keyword']['interior_candidate']['possible_omission']['correct']=99
    assert qualify_boundary_results(data,True)['status']=='invalid_evidence'

def test_interior_status_and_abstention_denominators_are_scoped():
    from app.vaakmitra_word.boundary_release import summarize_sound_cases
    own={'truth':None,'interior':True,'candidate':{'status':'sequence_supported'}}
    truth={'kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['p']}
    inside={'truth':truth,'interior':True,'candidate':dict(truth,status='possible_substitution')}
    edge={'truth':truth,'interior':False,'candidate':{'status':'insufficient_evidence'}}
    result=summarize_sound_cases([own,inside,edge],'candidate',True)
    assert result['rows']==2 and result['source_panel_rows']==3
    assert result['excluded_boundary_changed_cases']==1 and result['abstentions']==0
    assert sum(result['statuses'].values())==result['rows']

def test_unsupported_baseline_comparisons_have_no_supported_denominator():
    from app.vaakmitra_word.boundary_release import summarize_sound_cases
    t={'kind':'possible_omission','expected_sounds':['m'],'alternative_sounds':[]}
    rows=[{'truth':None,'interior':True,'baseline':{'status':'unsupported_reference'}},
          {'truth':t,'interior':True,'baseline':{'status':'unsupported_reference'}}]
    result=summarize_sound_cases(rows,'baseline')
    assert result['supported_own_targets']==result['supported_changed_cases']==0
    assert result['possible_omission']['supported_sensitivity'] is None

def binding_setup():
    binding={'source_weight_sha256':'a'*64,'checkpoint_sha256':'b'*64,'native_source_vocab_sha256':'c'*64,'bundle_vocab_sha256':'d'*64,'original_graph_sha256':'f'*64}
    vocab={f't{i}':i for i in range(38)};vocab['[PAD]']=38
    args={'source_weight_sha256':'a'*64,'checkpoint_sha256':'b'*64,'native_vocab_sha256':'c'*64,'bundle_vocab_sha256':'d'*64,
          'native_vocab':vocab,'bundle_tokens':['<blank>']+[f't{i}' for i in range(38)]}
    return binding,args

def test_frozen_source_weights_are_bound_even_if_current_download_proof_changed():
    from app.vaakmitra_word.boundary_release import verify_acoustic_binding
    binding,args=binding_setup()
    assert verify_acoustic_binding(binding,**args)==[38]+list(range(38))
    args['source_weight_sha256']='e'*64
    with pytest.raises(ValueError):verify_acoustic_binding(binding,**args)

def test_vocabulary_order_and_file_identity_are_both_bound():
    from app.vaakmitra_word.boundary_release import verify_acoustic_binding
    binding,args=binding_setup();args['bundle_tokens'][1:3]=args['bundle_tokens'][2:0:-1]
    with pytest.raises(ValueError):verify_acoustic_binding(binding,**args)
    binding,args=binding_setup();args['native_vocab_sha256']='e'*64
    with pytest.raises(ValueError):verify_acoustic_binding(binding,**args)

