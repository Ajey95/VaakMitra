"""DEC067/PHN007: final-review data provenance and interruption regressions."""
import hashlib,json,os
from pathlib import Path
import pytest
import torch
from scripts.model import train_live_anchor as runner

def test_child_checkpoint_drops_parent_training_state_and_counts_current_rows(tmp_path):
    model=torch.nn.Linear(2,2);opt=torch.optim.AdamW(model.parameters())
    initial={'model':model.state_dict(),'encoder_blocks':5,'frame_shift_ms':40,'dataset_sha256':'parent',
             'binding':{'row_count':18134,'binding_sha256':'old'},'best':.13,'stale':4,'rng':'parent-rng','experiment_config':{'parent':True}}
    binding={'focus_data':'child','row_count':18214}
    state=runner.checkpoint(initial,model,opt,1,{'name':'trial'},binding,tmp_path)
    assert state['binding']['row_count']==18214
    assert not {'best','stale','rng','cuda_rng','augmentation_rng','experiment_config'} & state.keys()
    assert state['parent_provenance']['binding']['row_count']==18134

def test_imported_encoder_is_in_pre_gradient_source_inventory():
    paths=runner.training_source_paths()
    assert any(p.name=='mobile_student_model.py' for p in paths)

def test_export_rejects_changed_cache_or_metadata_bytes(tmp_path):
    from app.vaakmitra_word.live_anchor_state import verify_export_inputs
    keys=('focus_data','base_audio','extra_audio','tempo_manifest','tempo_audio')
    paths={key:tmp_path/key for key in keys}
    for path in paths.values():path.write_bytes(b'frozen')
    binding={k:hashlib.sha256(p.read_bytes()).hexdigest() for k,p in paths.items()}
    verify_export_inputs(binding,paths)
    for key,path in paths.items():
        path.write_bytes(b'changed')
        with pytest.raises(ValueError):verify_export_inputs(binding,paths)
        path.write_bytes(b'frozen')

def test_parity_tracks_preexposed_evaluation_fixture_separately():
    from app.vaakmitra_word.live_anchor_state import parity_origins
    rows=[{'audio_sha256':'cal','split':'calibration'},{'audio_sha256':'fixture','split':'evaluation'}]
    actual=parity_origins(rows,[rows[0]],[{'split':'calibration'}],'fixture')
    assert actual['natural_calibration_clips']==1 and actual['tempo_calibration_clips']==1
    assert actual['fixture_source_split']=='evaluation'
    assert actual['evaluation_inference_accessed'] and not actual['calibration_only']
    assert not actual['full_evaluation_cohort_inferred']
    with pytest.raises(ValueError):parity_origins(rows,[rows[1]],[],'fixture')
    with pytest.raises(ValueError):parity_origins(rows,[rows[0]],[],'unknown')

def groups(edits):return {g:{'records':10,'phones':100,'edits':v,'phoneme_error_rate':v/100} for g,v in edits.items()}
def evidence():
    base=groups(dict(all=55,old19=5,new6=25,focus18=20));cal=groups(dict(all=54,old19=5,new6=24,focus18=19))
    tb=groups(dict(all=90,amma=10));tempo=groups(dict(all=80,amma=10))
    rec={'epoch':1,'calibration':cal,'tempo':tempo,'eligible':True,'improved':True,'score':.382}
    return base,tb,rec

def test_interrupted_epoch_publication_resumes_from_last_committed_model(tmp_path,monkeypatch):
    from app.vaakmitra_word.live_anchor_state import commit_epoch,load_trial_commit
    binding={'source':'bound'};cfg={'name':'trial'};_,_,record=evidence()
    state={'model':{'w':torch.tensor([1.])},'epoch':1,'anchor_binding':binding,'anchor_config':cfg}
    commit_epoch(tmp_path,state,record,binding,cfg)
    replace=os.replace
    def interrupted(src,dst):
        if Path(dst).name=='epoch-commit.json':raise OSError('controlled power interruption before pointer commit')
        return replace(src,dst)
    with monkeypatch.context() as patch:
        patch.setattr(os,'replace',interrupted)
        with pytest.raises(OSError):commit_epoch(tmp_path,dict(state,epoch=2,model={'w':torch.tensor([2.])}),dict(record,epoch=2),binding,cfg)
    restored=load_trial_commit(tmp_path,binding,cfg)
    assert restored['last']['epoch']==1 and restored['last']['model']['w'].item()==1.
    commit_epoch(tmp_path,dict(state,epoch=2,model={'w':torch.tensor([2.])}),dict(record,epoch=2),binding,cfg)
    assert load_trial_commit(tmp_path,binding,cfg)['last']['epoch']==2

def test_candidate_comes_only_from_verified_committed_eligible_evidence(tmp_path):
    from app.vaakmitra_word.live_anchor_state import commit_epoch,select_trial_candidate
    binding={'source':'bound'};cfg={'name':'trial'};base,tb,record=evidence()
    # A convenience best file alone is never candidate evidence.
    (tmp_path/'best.pt').write_bytes(b'orphan')
    assert select_trial_candidate(tmp_path,binding,cfg,base,tb) is None
    state={'model':{'w':torch.tensor([1.])},'epoch':1,'anchor_binding':binding,'anchor_config':cfg}
    commit_epoch(tmp_path,state,record,binding,cfg)
    selected=select_trial_candidate(tmp_path,binding,cfg,base,tb)
    assert selected['record']['epoch']==1
    (tmp_path/selected['file']).write_bytes(b'corrupted committed checkpoint')
    with pytest.raises(ValueError):select_trial_candidate(tmp_path,binding,cfg,base,tb)
