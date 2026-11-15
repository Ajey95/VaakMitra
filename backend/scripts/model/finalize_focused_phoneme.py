"""DEC-058: freeze one calibration choice before exposed-test access; no reselection."""
from __future__ import annotations
import argparse,datetime,hashlib,json
from pathlib import Path
import numpy as np
import torch
from app.vaakmitra_word.focused_words import FOCUS_IDS,eligible,metrics,parent
from app.vaakmitra_word.focused_finalization import freeze_operation,claim_evaluation,operation_lease,robustness_counts
from app.vaakmitra_word.phoneme_ctc import model_from_checkpoint,stress_waveform
from app.vaakmitra_word.phoneme_decoder import decode_logits
from scripts.model import focused_phoneme_update as run

def main(root):
 with operation_lease(root):finalize(root)

def finalize(root):
 data,binding=run.validate_inputs(root)
 selection=run.read(root/'selection-freeze.json')
 if selection['focus_data_sha256']!=binding['focus_data_sha256'] or selection['evaluation_accessed']:
  raise ValueError('invalid calibration freeze')
 winner=selection['winner'];checkpoint=run.BASE/'best.pt' if winner is None else root/winner['name']/'best.pt'
 if winner and run.original.sha(checkpoint)!=winner['checkpoint_sha256']:raise ValueError('selected checkpoint changed')
 freeze=dict(selection_sha256=run.original.sha(root/'selection-freeze.json'),checkpoint_sha256=run.original.sha(checkpoint),finalizer_sha256=run.original.sha(__file__),decoder=run.DECODER,binding=binding)
 freeze_operation(root,freeze)
 torch.set_num_threads(4)
 model=model_from_checkpoint(torch.load(checkpoint,map_location='cpu',weights_only=True),61).cuda().eval()
 report=dict(selected=winner['name'] if winner else None,promoted=False,reason='no_calibration_eligible_candidate',test_accessed=False,freeze=freeze,production_ready=False,approved_for_child_scoring=False)
 if winner:
  results=root/'evaluation-results.json'
  if not results.exists()and claim_evaluation(root,freeze):
   test=run.Clips(root,data,'evaluation')
   baseline=model_from_checkpoint(torch.load(run.BASE/'best.pt',map_location='cpu',weights_only=True),61).cuda().eval()
   run.original.write(results,dict(freeze=freeze,baseline_evaluation=run.evaluate(baseline,test),candidate_evaluation=run.evaluate(model,test)))
   del baseline
  if results.exists():
   stored=run.read(results)
   if stored.pop('freeze')!=freeze:raise ValueError('evaluation result binding changed')
   report.update(stored,test_accessed=True)
   report['evaluation_eligible']=eligible(report['candidate_evaluation'],report['baseline_evaluation'],run.TEST_CAP)
   report['reason']='pending_export_native_parity' if report['evaluation_eligible'] else 'exposed_test_nonregression_gate_failed'
  else:
   report.update(test_accessed=None,reason='previous_evaluation_interrupted_not_repeated_retain_V7')
 # Synthetic variants are deterministic transforms of public adult calibration parents,
 # never independent samples, child simulations or additions to training.
 cal=run.Clips(root,data,'calibration');indices=[i for i,r in enumerate(cal.rows)if r.get('practice_id')in FOCUS_IDS]
 stress={};parents=[dict(audio_path=cal.rows[i]['audio_path'],audio_sha256=cal.rows[i]['audio_sha256'],source_utterance_id=parent(cal.rows[i]))for i in indices]
 for kind in ('clean','noise20','noise10','echo','lowpass','quiet'):
  predicted=[]
  for start in range(0,len(indices),32):
   batch=indices[start:start+32]
   audio=np.stack([cal[i][0].numpy() if kind=='clean' else stress_waveform(cal[i][0].numpy(),kind,911+i)for i in batch])
   with torch.no_grad():values=model(torch.from_numpy(audio).cuda()).cpu().numpy()
   predicted.extend(decode_logits(v,run.DECODER)for v in values)
  stress[kind]=metrics(predicted,[cal.rows[i]for i in indices])
  if kind=='clean':
   report['per_word_calibration']={word:metrics([p for p,i in zip(predicted,indices)if cal.rows[i].get('practice_id')==word],[cal.rows[i]for i in indices if cal.rows[i].get('practice_id')==word])['all']for word in FOCUS_IDS}
 run.original.write(root/'synthetic-robustness.json',dict(model_sha256=freeze['checkpoint_sha256'],source_split='calibration',adult_public_only=True,independent_test=False,parents=parents,counts=robustness_counts(parents,5),variants=stress))
 run.original.write(root/'final-decision.json',report)
 print(json.dumps(report),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);main(p.parse_args().root)
