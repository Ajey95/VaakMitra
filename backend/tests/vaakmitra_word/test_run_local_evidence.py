"""DEC-018/DATA-013: local diagnostic evidence selection never promotes approval."""
import json
import runpy
from pathlib import Path

import pytest


def _runner():
    script = Path(__file__).resolve().parents[3] / 'scripts/backend/run_local.py'
    return runpy.run_path(str(script))


def _rebuilt(tmp_path):
    runner = _runner()
    evidence = tmp_path / 'evidence.jsonl'
    evidence.write_text('{"synthetic":true}\n', encoding='utf-8')
    calibration = tmp_path / 'calibration.json'
    calibration.write_text(json.dumps({'approved': False, 'population': 'adult_only_engineering',
        'dataset_manifest_hash': runner['digest'](evidence), 'live_pipeline_hash': 'a' * 64}),
        encoding='utf-8')
    (tmp_path / 'provenance.json').write_text(json.dumps({'approved': False,
        'population': 'adult_only_engineering', 'live_pipeline_hash': 'a' * 64,
        'scoring_ready': False}), encoding='utf-8')
    (tmp_path / 'report.json').write_text(json.dumps({'approved': False,
        'human_approved': False, 'scoring_ready': False, 'usable_attempt_count': 1,
        'live_pipeline_hash': 'a' * 64,
        'calibration_hash': runner['digest'](calibration)}), encoding='utf-8')
    return runner


def test_data013_local_runner_selects_complete_unapproved_rebuilt_evidence(tmp_path):
    runner = _rebuilt(tmp_path)
    old = {'model': Path('old-model'), 'calibration': Path('old-calibration'),
        'dataset_manifest': Path('old-evidence')}
    selected = runner['select_engineering_evidence'](old, tmp_path)
    assert selected['model'] == old['model']
    assert selected['calibration'] == tmp_path / 'calibration.json'
    assert selected['dataset_manifest'] == tmp_path / 'evidence.jsonl'
    assert old['calibration'] == Path('old-calibration')


def test_data013_local_runner_rejects_incomplete_or_approved_rebuild(tmp_path):
    runner = _rebuilt(tmp_path)
    old = {'calibration': Path('old-calibration'), 'dataset_manifest': Path('old-evidence')}
    (tmp_path / 'report.json').unlink()
    with pytest.raises(RuntimeError, match='engineering_rebuild_incomplete'):
        runner['select_engineering_evidence'](old, tmp_path)
    runner = _rebuilt(tmp_path)
    calibration = tmp_path / 'calibration.json'
    payload = json.loads(calibration.read_text(encoding='utf-8'))
    payload['approved'] = True
    calibration.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(RuntimeError, match='engineering_rebuild_not_unapproved'):
        runner['select_engineering_evidence'](old, tmp_path)
