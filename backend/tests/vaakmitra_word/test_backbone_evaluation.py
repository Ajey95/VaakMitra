"""DEC068: reject unqualified precision/evidence before any exposed-test access."""
import pytest
from scripts.model.evaluate_phoneme_backbone import validate_qualification


def test_fp32_uses_its_declared_full_torch_calibration_and_exact53_graph_parity():
    from scripts.model.prepare_fp32_backbone import validate_fp32
    cal=dict(eligible=True,records=1945)
    parity=dict(all_match=True,cases=[dict(decoded_match=True,kind='calibration',source_row=i)for i in range(53)])
    validate_fp32(cal,parity)
    for bad in (dict(all_match=True,cases=parity['cases'][:-1]),dict(all_match=False,cases=parity['cases']),
            dict(all_match=True,cases=[dict(decoded_match=False)]+parity['cases'][1:])):
        with pytest.raises(ValueError):validate_fp32(cal,bad)
    with pytest.raises(ValueError):validate_fp32(dict(eligible=False,records=1945),parity)
    with pytest.raises(ValueError):validate_fp32(cal,dict(all_match=True,cases=[parity['cases'][0]]*53))


def test_two_report_directories_and_interruption_share_the_same_canonical_claim(tmp_path):
    from scripts.model.evaluate_phoneme_backbone import claim_scientific_evaluation
    from concurrent.futures import ThreadPoolExecutor
    identity=dict(data_sha256='a'*64,model_sha256='b'*64)
    with ThreadPoolExecutor(max_workers=2)as pool:
        results=list(pool.map(lambda name:claim_scientific_evaluation(tmp_path,identity,tmp_path/name),('reportA','reportB')))
    assert sum(results)==1
    assert not claim_scientific_evaluation(tmp_path,identity,tmp_path/'reportB')
    assert not claim_scientific_evaluation(tmp_path,identity,tmp_path/'reportA')


def test_legacy_claim_in_another_report_directory_blocks_a_new_claim(tmp_path):
    from scripts.model.evaluate_phoneme_backbone import claim_scientific_evaluation
    from scripts.model.cache_phoneme_backbone import write
    previous=tmp_path/'previous-report';previous.mkdir()
    identity=dict(data_sha256='a'*64,model_sha256='b'*64)
    write(previous/'evaluation-ticket.json',identity)
    with pytest.raises(ValueError):claim_scientific_evaluation(tmp_path,identity,tmp_path/'new-report')


def test_precision_ancestry_must_join_the_authenticated_training_selection():
    from scripts.model.evaluate_phoneme_backbone import validate_export_lineage
    expected=dict(training_intent_sha256='train',selection_freeze_sha256='selection',checkpoint_sha256='winner')
    validate_export_lineage(expected,'train','selection','winner')
    for key in expected:
        with pytest.raises(ValueError):validate_export_lineage(dict(expected,**{key:'another-qualified-run'}),'train','selection','winner')


def test_fixture_rule_is_regenerated_and_never_accepts_duplicates():
    from scripts.model.prepare_fp32_backbone import fixture_identities
    rows=[dict(split='calibration',practice_id=f'word{i}',audio_sha256=f'{i:064x}')for i in range(25)]
    rows += [dict(split='calibration',practice_id=None,audio_sha256=f'{i+25:064x}')for i in range(10)]
    bank=[dict(split='calibration',audio_sha256=f'{i+35:064x}')for i in range(18)]
    predictions=[dict(kind='calibration',source_row=i,samples=500)for i in range(35)]
    predictions += [dict(kind='calibration_tempo',source_row=i,samples=500)for i in range(18)]
    selected=fixture_identities(rows,bank,predictions,{f'word{i}':[]for i in range(25)})
    assert len(selected)==53 and len({(r['kind'],r['source_row'])for r in selected})==53
    assert sum(r['kind']=='calibration_tempo'for r in selected)==18
    assert selected==fixture_identities(rows,bank,list(reversed(predictions)),{f'word{i}':[]for i in reversed(range(25))})


def valid():
    return dict(qualified_for_native_validation=True,production_ready=False,
        approved_for_child_scoring=False,private_child_audio_used=False,reserved_evaluation_inferred=False)


def test_exact_qualification_and_safety_flags_cannot_be_missing_or_coerced():
    validate_qualification(valid(),dict(eligible=True,decoded_agreement=.95,records=1945))
    for key in valid():
        fields=valid();fields.pop(key)
        with pytest.raises(ValueError):validate_qualification(fields,dict(eligible=True,decoded_agreement=.96,records=1945))
    for report in (dict(eligible=True,decoded_agreement=.9499,records=1945),
            dict(eligible='true',decoded_agreement=.96,records=1945),dict(eligible=True,decoded_agreement=float('nan'),records=1945),
            dict(eligible=True,decoded_agreement=.96,records=1944)):
        with pytest.raises(ValueError):validate_qualification(valid(),report)
