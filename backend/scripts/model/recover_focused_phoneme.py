"""DEC-058 resource recovery: repeat the interrupted frozen control, no new search."""
import argparse,copy,datetime,hashlib,json,time
from pathlib import Path
import torch
from torch import nn
from torch.utils.data import WeightedRandomSampler
from app.vaakmitra_word.focused_words import sampling_weights,eligible
from app.vaakmitra_word.phoneme_ctc import model_from_checkpoint
from scripts.model import focused_phoneme_update as run
from scripts.model.improve_mobile_phoneme import augment,configure_encoder_training,configure_recurrent_dropout

def recovery_configuration(completed,interrupted,config,selection_exists):
 if selection_exists or len(completed)!=7 or any(x['eligible']for x in completed) or len(interrupted)!=1 or interrupted[0]['eligible']:
  raise ValueError('recovery applies only to this recorded interruption, never a completed search')
 if config!=dict(name='frozen80',seed=703,fraction=.8,encoder_lr=0.,head_lr=1e-5,frozen=True):raise ValueError('frozen control changed')
 return dict(config)

def recover(root):
 data,binding=run.validate_inputs(root)
 intent=run.read(root/'training-intent.json');baseline=run.read(root/'baseline-calibration.json')
 completed=run.read(root/'balanced75/history.json');interrupted=run.read(root/'frozen80/history.json')
 config=recovery_configuration(completed,interrupted,intent['configs'][1],(root/'selection-freeze.json').exists())
 out=root/'frozen80-recovery';out.mkdir(exist_ok=False);run.guard_space(root)
 run.original.write(root/'recovery-intent.json',dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reason='original process exited code1 during concurrent JVM native-memory exhaustion; exact training exit cause unconfirmed',unchanged_config=config,original_intent_sha256=run.original.sha(root/'training-intent.json'),interrupted_history_sha256=run.original.sha(root/'frozen80/history.json'),recovery_source_sha256=run.original.sha(__file__),evaluation_accessed=False))
 torch.set_num_threads(4);torch.manual_seed(703);torch.cuda.manual_seed_all(703)
 initial=torch.load(run.BASE/'best.pt',map_location='cpu',weights_only=True)
 trainset=run.Clips(root,data,'train');calset=run.Clips(root,data,'calibration')
 model=model_from_checkpoint(initial,61).cuda();configure_recurrent_dropout(model,.2)
 opt=torch.optim.AdamW([dict(params=model.encoder.parameters(),lr=0.),dict(params=list(model.sequence.parameters())+list(model.head.parameters()),lr=1e-5)],weight_decay=.0001)
 criterion=nn.CTCLoss(blank=0,reduction='none',zero_infinity=False);weights=sampling_weights(trainset.rows,.8);rng=torch.Generator().manual_seed(703)
 history=[];best=float('inf');stale=0;start=time.monotonic()
 for epoch in range(1,31):
  run.guard_space(root);model.train();configure_encoder_training(model,True,True)
  sampler=WeightedRandomSampler(weights,len(trainset),replacement=True,generator=torch.Generator().manual_seed(703+epoch));loss_sum=0
  for audio,targets,lengths,_,_ in run.loader(trainset,sampler=sampler):
   audio=augment(audio.cuda(non_blocking=True),rng,'channel');opt.zero_grad(set_to_none=True);logits=model(audio)
   loss=(criterion(logits.log_softmax(-1).transpose(0,1),targets.cuda(),torch.full((len(audio),),logits.shape[1],dtype=torch.long),lengths)/lengths.cuda()).mean()
   if not torch.isfinite(loss):raise FloatingPointError('nonfinite recovery CTC loss')
   loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5,error_if_nonfinite=True);opt.step();loss_sum+=float(loss.detach())*len(audio)
  cal=run.evaluate(model,calset);ok=eligible(cal,baseline,run.CAL_CAP);score=.7*cal['focus18']['phoneme_error_rate']+.3*cal['all']['phoneme_error_rate'];improved=ok and score<best
  stale=0 if improved else stale+1
  if improved:
   best=score;state=copy.copy(initial);fb=dict(initial['binding'],row_count=len(data['rows']),focus_data_sha256=binding['focus_data_sha256']);fb.pop('binding_sha256',None);fb['binding_sha256']=hashlib.sha256(json.dumps(fb,sort_keys=True).encode()).hexdigest()
   state.update(model={k:v.detach().cpu()for k,v in model.state_dict().items()},optimizer=opt.state_dict(),epoch=epoch,focus_data_sha256=binding['focus_data_sha256'],dataset_sha256=binding['focus_data_sha256'],parent_dataset_sha256=data['parent_dataset_sha256'],binding=fb,formation_method='DEC058_focused_continuation_resource_recovery',decoder=run.DECODER)
   run.original.save(out/'best.pt',state);run.original.write(out/'best-calibration.json',cal)
  record=dict(epoch=epoch,loss=loss_sum/len(trainset),calibration=cal,eligible=ok,score=score,elapsed_seconds=time.monotonic()-start,peak_vram_bytes=torch.cuda.max_memory_allocated());history.append(record);run.original.write(out/'history.json',history);print(json.dumps(record),flush=True)
  if stale and stale%4==0:
   for group in opt.param_groups:group['lr']*=.5
  if stale>=7 or time.monotonic()-start>12*60:break
 candidates=[dict(name=out.name,score=best,checkpoint_sha256=run.original.sha(out/'best.pt'),calibration=run.read(out/'best-calibration.json'))]if(out/'best.pt').exists()else[]
 run.original.write(root/'selection-freeze.json',dict(eligible_candidates=candidates,winner=candidates[0]if candidates else None,calibration_only=True,evaluation_accessed=False,focus_data_sha256=binding['focus_data_sha256'],decoder=run.DECODER,script_sha256=binding['script_sha256'],recovery_source_sha256=run.original.sha(__file__)))
 print(json.dumps(dict(stage='calibration_frozen',eligible_candidates=len(candidates))),flush=True)

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);recover(p.parse_args().root)
