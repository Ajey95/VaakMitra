"""DEC077/PHN018: explicit control denominators and frozen PyTorch reconstruction identity."""
from __future__ import annotations
import re

KINDS=('possible_omission','possible_substitution')
UNSUPPORTED={'unsupported_reference','unsupported_scope','outside_input_contract'}

def _correct(row,out):
    truth=row['truth']
    return bool(truth and out.get('status')==truth['kind'] and out.get('expected_sounds')==truth['expected_sounds'] and out.get('alternative_sounds')==truth['alternative_sounds'])

def summarize_sound_cases(rows,key,interior_only=False):
    selected=[r for r in rows if r['truth'] is None or not interior_only or r['interior']]
    own=[r for r in selected if r['truth'] is None];changed=[r for r in selected if r['truth'] is not None]
    alert=lambda out:out.get('status') in KINDS
    statuses={}
    for row in selected:
        status=row[key].get('status','invalid_evidence');statuses[status]=statuses.get(status,0)+1
    result={'rows':len(selected),'source_panel_rows':len(rows),'excluded_boundary_changed_cases':len(rows)-len(selected),
            'own_targets':len(own),'own_target_alerts':sum(alert(r[key]) for r in own),
            'changed_cases':len(changed),'correct_differences':sum(_correct(r,r[key]) for r in changed),
            'wrong_attributions':sum(alert(r[key]) and not _correct(r,r[key]) for r in changed),
            'abstentions':sum(not alert(r[key]) and r[key].get('status')!='sequence_supported' for r in selected),
            'supported_own_targets':sum(r[key].get('status') not in UNSUPPORTED for r in own),
            'supported_changed_cases':sum(r[key].get('status') not in UNSUPPORTED for r in changed),'statuses':statuses}
    for kind in KINDS:
        panel=[r for r in changed if r['truth']['kind']==kind]
        supported=[r for r in panel if r[key].get('status') not in UNSUPPORTED]
        correct=sum(_correct(r,r[key]) for r in panel);supported_correct=sum(_correct(r,r[key]) for r in supported)
        result[kind]={'total':len(panel),'correct':correct,'sensitivity':correct/len(panel) if panel else None,
                      'supported_total':len(supported),'supported_sensitivity':supported_correct/len(supported) if supported else None}
    return result

def _validated(metric):
    def count(key):
        value=metric[key]
        if type(value) is not int or value<0:raise ValueError('invalid_count')
        return value
    own=count('own_targets');changed=count('changed_cases');rows=count('rows')
    if count('own_target_alerts')>own or count('wrong_attributions')>changed or rows!=own+changed:raise ValueError('inconsistent_denominator')
    totals=0;correct=0;rates={}
    for kind in KINDS:
        row=metric[kind];n=row['total'];c=row['correct']
        if type(n) is not int or type(c) is not int or not 0<=c<=n:raise ValueError('invalid_kind_count')
        totals+=n;correct+=c;rates[kind]=c/n if n else None
    if totals!=changed or count('correct_differences')!=correct:raise ValueError('kind_accounting')
    return rates

def qualify_boundary_results(summary,development_eligible):
    result={'status':'evaluated','interior_lexical_gate_passed':False,'whole_panel_gate_passed':False,
            'control_safety_gate_passed':False,'mobile_active':False,'natural_error_gate_passed':False,
            'approved_for_child_scoring':False,'clinical_assessment':False,'failures':[],'controls':{}}
    try:
        if type(development_eligible) is not bool:raise ValueError('development_status')
        full=summary['keyword']['candidate'];interior=summary['keyword']['interior_candidate'];baseline=summary['keyword']['interior_baseline']
        whole_rates=_validated(full);inner_rates=_validated(interior);_validated(baseline)
        if (interior['own_targets']!=full['own_targets'] or interior['rows']>full['rows'] or
            any(interior[k]['total']>full[k]['total'] or interior[k]['correct']>full[k]['correct'] for k in KINDS)):raise ValueError('invalid_subset')
        clean=full['own_targets']>0
        if full['own_target_alerts']:result['failures'].append('keyword_own_target_alerts');clean=False
        if full['wrong_attributions']:result['failures'].append('keyword_wrong_attributions');clean=False
        if any(full.get('statuses',{}).get(k,0) for k in ['invalid_model','invalid_evidence']):
            result['failures'].append('keyword_invalid_evidence');clean=False
        safe=True
        controls={'complete_source':summary['complete_source']['candidate'],
                  'quiet':summary['secondary']['quiet']['candidate'],'pause':summary['secondary']['pause']['candidate']}
        for name,metric in controls.items():
            _validated(metric)
            valid=(metric['own_targets']>0 and metric['changed_cases']>0 and metric['own_target_alerts']==metric['wrong_attributions']==0 and
                   not any(metric.get('statuses',{}).get(k,0) for k in ['invalid_model','invalid_evidence']))
            result['controls'][name]={'safety_passed':valid,'own_targets':metric['own_targets'],'changed_cases':metric['changed_cases'],
                'own_target_alerts':metric['own_target_alerts'],'wrong_attributions':metric['wrong_attributions']}
            if not valid:result['failures'].append(name+'_unsafe_or_missing_controls');safe=False
        result['control_safety_gate_passed']=safe
        performance=True
        for kind in KINDS:
            good=(interior[kind]['correct']>=10 and inner_rates[kind] is not None and inner_rates[kind]>=.50 and
                  interior[kind]['correct']>=baseline[kind]['correct'])
            if not good:result['failures'].append(kind+'_interior_coverage');performance=False
        gain=interior['correct_differences']>baseline['correct_differences']
        if not gain:result['failures'].append('no_interior_baseline_gain')
        if not development_eligible:result['failures'].append('development_ineligible')
        result['interior_lexical_gate_passed']=development_eligible and clean and performance and gain
        broad=all(whole_rates[k] is not None and whole_rates[k]>=.35 for k in KINDS)
        if not broad:result['failures'].append('whole_panel_coverage')
        result['whole_panel_gate_passed']=result['interior_lexical_gate_passed'] and broad and safe
        return result
    except (KeyError,ValueError,TypeError):
        return dict(result,status='invalid_evidence',interior_lexical_gate_passed=False,whole_panel_gate_passed=False,
                    control_safety_gate_passed=False,failures=result['failures']+['invalid_or_missing_denominator'])

def verify_acoustic_binding(binding,*,source_weight_sha256,checkpoint_sha256,native_vocab_sha256,bundle_vocab_sha256,native_vocab,bundle_tokens):
    """Historical exported graph identity is provenance; runtime uses frozen PyTorch weights."""
    expected={'source_weight_sha256':source_weight_sha256,'checkpoint_sha256':checkpoint_sha256,
              'native_source_vocab_sha256':native_vocab_sha256,'bundle_vocab_sha256':bundle_vocab_sha256}
    if not isinstance(binding,dict):raise ValueError('binding_schema')
    for key,actual in expected.items():
        frozen=binding.get(key)
        if not isinstance(frozen,str) or not re.fullmatch('[0-9a-f]{64}',frozen) or actual!=frozen:raise ValueError('frozen_'+key)
    if not isinstance(native_vocab,dict) or len(native_vocab)!=39 or set(native_vocab.values())!=set(range(39)):raise ValueError('native_vocabulary')
    if any(not isinstance(k,str) or type(v) is not int for k,v in native_vocab.items()):raise ValueError('native_token_type')
    blank=native_vocab.get('[PAD]')
    if blank!=38:raise ValueError('native_blank')
    order=[blank]+[i for i in range(39) if i!=blank];by_index={v:k for k,v in native_vocab.items()}
    expected_tokens=['<blank>']+[by_index[i] for i in order[1:]]
    if bundle_tokens!=expected_tokens:raise ValueError('frozen_vocabulary_order')
    return order

