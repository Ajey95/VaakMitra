"""DEC-058 final review: exactly-once evaluation and no-winner recovery."""
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.vaakmitra_word.focused_finalization import freeze_operation,claim_evaluation,operation_lease,robustness_counts

def test_concurrent_evaluation_claim_has_exactly_one_winner(tmp_path):
 with ThreadPoolExecutor(max_workers=8)as pool:results=list(pool.map(lambda _:claim_evaluation(tmp_path,{'checkpoint':'same'}),range(16)))
 assert sum(results)==1

def test_interruption_after_freeze_without_candidate_can_resume_without_test_access(tmp_path):
 freeze_operation(tmp_path,{'checkpoint':'same'})
 with operation_lease(tmp_path):assert freeze_operation(tmp_path,{'checkpoint':'same'})=={'checkpoint':'same'}
 assert not(tmp_path/'evaluation-ticket.json').exists()
 with pytest.raises(ValueError):freeze_operation(tmp_path,{'checkpoint':'different'})

def test_parallel_report_operation_is_rejected_and_lease_releases(tmp_path):
 with operation_lease(tmp_path):
  with pytest.raises(RuntimeError):
   with operation_lease(tmp_path):pass
 with operation_lease(tmp_path):pass

def test_robustness_counts_clips_and_distinct_source_utterances_separately():
 assert robustness_counts([{'source_utterance_id':'a'},{'source_utterance_id':'a'},{'source_utterance_id':'b'}],5)==dict(source_clips=3,distinct_source_utterances=2,synthetic_derivatives=15)

def test_real_no_candidate_finalizer_recovers_after_freeze_without_opening_evaluation(tmp_path,monkeypatch):
 import numpy as np
 from scripts.model import finalize_focused_phoneme as final
 base=tmp_path/'base';base.mkdir();(base/'best.pt').write_bytes(b'checkpoint')
 root=tmp_path/'run';root.mkdir();monkeypatch.setattr(final.run,'BASE',base)
 final.run.original.write(root/'selection-freeze.json',dict(winner=None,focus_data_sha256='focus',evaluation_accessed=False))
 monkeypatch.setattr(final.run,'validate_inputs',lambda _:({},dict(focus_data_sha256='focus')))
 monkeypatch.setattr(final.torch,'load',lambda *a,**k:{})
 monkeypatch.setattr(final.torch,'set_num_threads',lambda _:None)
 def interrupted(*a):raise InterruptedError('after freeze')
 monkeypatch.setattr(final,'model_from_checkpoint',interrupted)
 with pytest.raises(InterruptedError):final.main(root)
 assert(root/'test-access-freeze.json').exists()and not(root/'evaluation-ticket.json').exists()
 class Tensor:
  def __init__(self,array):self.array=array
  def cuda(self):return self
  def cpu(self):return self
  def numpy(self):return self.array
 class Model:
  def cuda(self):return self
  def eval(self):return self
  def __call__(self,x):return Tensor(np.zeros((len(x.array),1,61),dtype=np.float32))
 class Calibration:
  rows=[dict(audio_path='public/test.wav',source_utterance_id='one',audio_sha256='hash',targets=[1],is_target=True,practice_id='TA_WORD_0001')]
  def __getitem__(self,i):return(Tensor(np.zeros(48000,dtype=np.float32)),)
 monkeypatch.setattr(final,'model_from_checkpoint',lambda *a:Model())
 monkeypatch.setattr(final.torch,'from_numpy',Tensor)
 monkeypatch.setattr(final.run,'Clips',lambda *a:Calibration())
 monkeypatch.setattr(final,'decode_logits',lambda *a:[1])
 def no_evaluation(*a):raise AssertionError('evaluation must stay unopened')
 monkeypatch.setattr(final.run,'evaluate',no_evaluation)
 final.main(root);final.main(root)
 report=final.run.read(root/'final-decision.json')
 assert report['test_accessed']is False and report['promoted']is False
 assert not(root/'evaluation-ticket.json').exists()
