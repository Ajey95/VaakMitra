"""DEC058: bounded CUDA focus continuation, immutable input sidecars and calibration-only choice."""
from __future__ import annotations
import argparse,copy,hashlib,io,json,math,shutil,tarfile,time,zipfile
from collections import Counter
from pathlib import Path
import numpy as np
import soundfile as sf
import torch
from torch import nn
from torch.utils.data import DataLoader,Dataset,WeightedRandomSampler
from scipy.signal import resample_poly
from scripts.model import finetune_mobile_phoneme as original
from scripts.model.improve_mobile_phoneme import augment,configure_encoder_training,configure_recurrent_dropout
from scripts.model.prepare_phoneme_expansion import source_utterance_id
from app.vaakmitra_word.phoneme_ctc import SAMPLES,model_from_checkpoint,prepare_waveform,stress_waveform
from app.vaakmitra_word.phoneme_decoder import decode_logits
from app.vaakmitra_word.focused_words import NEW_WORDS,NEW_IDS,FOCUS_IDS,sampling_weights,validate_extra_rows,metrics,eligible

ROOT=Path('D:/VaakMitraData');BASE=ROOT/'artifacts/phoneme-ta19-v7-improved'
CAL_CAP=.5570071699025215;TEST_CAP=.5929667
DECODER=dict(type='ctc_prefix_beam',beam_width=5,nonblank_top_k=8)

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def guard_space(path):
 if shutil.disk_usage(path).free<250*1024**2:raise OSError('DEC058 disk reserve reached; no cleanup permitted')

def reserved_mswc_rows(prepared,rawsource):
 rawby={r['original_id']:r for r in rawsource}
 return [dict(split=r['split'],speaker=r['speaker_pseudonym'],source_utterance_id=source_utterance_id(rawby[r['original_id']]),audio_path=r.get('audio_path',r['original_id']),audio_sha256=r['audio_sha256'],audio_hash_kind='file',source_audio_sha256=rawby[r['original_id']]['audio_sha256'])for r in prepared if r['split']!='train']

def prepare(out):
 out.mkdir(parents=True,exist_ok=False);guard_space(out)
 meta,vocab=original.load_run(BASE)
 source=[json.loads(l)for l in original.SOURCE.read_text(encoding='utf8').splitlines()]
 bypath={r['audio_path']:r for r in source}
 with zipfile.ZipFile(original.ZIP)as z:lex={e['word']:e['units']for e in json.loads(z.read('full-lexicon.json'))['entries']}
 ids={t:i for i,t in enumerate(vocab['tokens'])};oldwords=vocab['expected']
 tamil_ids={w['tamil']:w['id']for w in NEW_WORDS}
 rows=[];base_audio=np.load(BASE/'audio.npy',mmap_mode='r')
 for i,r in enumerate(meta['rows']):
  raw=bypath.get(r['audio_path'],{});tamil=r.get('transcript')or raw.get('transcript')
  practice=r.get('word_id')or tamil_ids.get(tamil)
  rows.append(dict(r,practice_id=practice,cache_shard='base',cache_index=i,pcm_sha256=hashlib.sha256(base_audio[i].tobytes()).hexdigest()))
 prepared=[json.loads(l)for l in (ROOT/'prepared/mswc-ta-other/manifest.jsonl').read_text(encoding='utf8').splitlines()]
 rawsource=[json.loads(l)for l in (ROOT/'manifests/mswc-ta-other.jsonl').read_text(encoding='utf8').splitlines()]
 rawby={r['original_id']:r for r in rawsource};wanted={rawby[r['original_id']]['audio_path']:r for r in prepared if r['transcript']=='என்ன'and r['split']=='train'}
 reserved=reserved_mswc_rows(prepared,rawsource)
 original.write(out/'reserved-mswc.json',reserved)
 audit=read(BASE/'expansion-manifest.json')['audit']+reserved;extra=[];audio=[];reject=Counter();origins=[]
 for split in ['train','dev','test']:
  archive=ROOT/f'raw/ml_spoken_words/data/opus/ta/{split}/audio/0.tar.gz'
  if not archive.exists():continue
  origins.append(dict(path=str(archive),sha256=original.sha(archive)))
  with tarfile.open(archive)as tar:
   for member in tar:
    if not member.isfile()or member.name not in wanted:continue
    prep=wanted.pop(member.name);raw=rawby[prep['original_id']];data=tar.extractfile(member).read()
    if hashlib.sha256(data).hexdigest()!=raw['audio_sha256']:raise ValueError('original OPUS digest changed')
    wave,rate=sf.read(io.BytesIO(data),dtype='float32')
    if wave.ndim!=1 or not np.isfinite(wave).all()or not .2<=len(wave)/rate<=3:reject['incomplete_or_duration']+=1;continue
    if rate!=16000:
     factor=math.gcd(rate,16000);wave=resample_poly(wave,16000//factor,rate//factor).astype(np.float32)
    if len(wave)>SAMPLES:reject['too_long']+=1;continue
    if np.sqrt(np.mean(wave*wave))<.005 or np.mean(np.abs(wave)>=.99)>.01:reject['quiet_or_clipped']+=1;continue
    row=dict(audio_path=f'mswc-original:{member.name}',audio_sha256=hashlib.sha256(wave.tobytes()).hexdigest(),source_audio_sha256=raw['audio_sha256'],speaker=prep['speaker_pseudonym'],split='train',targets=[ids[t]for t in lex['என்ன']],word_id=None,is_target=False,practice_id='TA_WORD_0101',source_utterance_id=source_utterance_id(raw),cache_shard='extra',cache_index=len(extra),source_archive=str(archive),source_member=member.name,duration_seconds=len(wave)/16000,licence_id=raw['licence_id'])
    padded=prepare_waveform(wave);row.update(audio_hash_kind='decoded_float32',pcm_sha256=hashlib.sha256(padded.tobytes()).hexdigest())
    try:validate_extra_rows(rows,extra+[row],audit)
    except ValueError:reject['reserved_or_duplicate']+=1;continue
    extra.append(row);audio.append(padded)
 if wanted:raise ValueError(f'missing original parents: {len(wanted)}')
 np.save(out/'extra-audio.npy',np.asarray(audio,dtype=np.float32).reshape((-1,SAMPLES)))
 expected=copy.deepcopy(vocab['expected'])
 for word in NEW_WORDS:expected[word['id']]=lex[word['tamil']]
 data=dict(schema='focused-words-v1',parent_root=str(BASE),parent_dataset_sha256=original.sha(BASE/'dataset.json'),base_audio_sha256=read(BASE/'cache-complete.json')['audio_sha256'],extra_audio_sha256=original.sha(out/'extra-audio.npy'),token_vocabulary_sha256=meta['binding']['vocabulary_sha256'],expected=expected,rows=rows+extra,source_archives=origins,rejected=dict(reject),new_train_parents=len(extra),expert_approved=False,approved_for_child_scoring=False)
 original.write(out/'focus-data.json',data)
 data['reserved_mswc_sha256']=original.sha(out/'reserved-mswc.json')
 original.write(out/'focus-data.json',data)
 original.write(out/'input-binding.json',dict(focus_data_sha256=original.sha(out/'focus-data.json'),base_checkpoint_sha256=original.sha(BASE/'best.pt'),script_sha256=original.sha(Path(__file__)),contract_sha256=original.sha(Path(__file__).parents[2]/'app/vaakmitra_word/focused_words.py')))
 shutil.copyfile(__file__,out/'frozen-entrypoint.py');shutil.copyfile(Path(__file__).parents[2]/'app/vaakmitra_word/focused_words.py',out/'frozen-contract.py')
 print(json.dumps(dict(stage='prepared',rows=len(rows)+len(extra),added_original_train=len(extra),rejected=dict(reject),focus_counts={s:sum(r['split']==s and r.get('practice_id')in FOCUS_IDS for r in data['rows'])for s in ['train','calibration','evaluation']})),flush=True)

class Clips(Dataset):
 def __init__(self,root,data,split):
  self.rows=[r for r in data['rows']if r['split']==split]
  self.base=np.load(BASE/'audio.npy',mmap_mode='r');self.extra=np.load(root/'extra-audio.npy',mmap_mode='r')
  if self.base.shape[1:]!=(SAMPLES,)or self.extra.shape[1:]!=(SAMPLES,)or self.base.dtype!=np.float32 or self.extra.dtype!=np.float32:raise ValueError('cache shape/dtype changed')
  for r in self.rows:
   cache=self.base if r['cache_shard']=='base'else self.extra
   if not 0<=r['cache_index']<len(cache):raise ValueError('invalid cache index')
 def __len__(self):return len(self.rows)
 def __getitem__(self,i):
  r=self.rows[i];cache=self.base if r['cache_shard']=='base'else self.extra
  return torch.from_numpy(cache[r['cache_index']].copy()),torch.tensor(r['targets']),r['is_target'],i

def loader(dataset,batch=64,sampler=None):return DataLoader(dataset,batch_size=batch,sampler=sampler,num_workers=0,collate_fn=original.collate,pin_memory=torch.cuda.is_available())

@torch.no_grad()
def evaluate(model,dataset,device='cuda'):
 model.eval();predictions=[]
 for audio,_,_,_,_ in loader(dataset):
  values=model(audio.to(device)).cpu().numpy();predictions.extend(decode_logits(x,DECODER)for x in values)
 return metrics(predictions,dataset.rows)

def validate_inputs(root):
 data=read(root/'focus-data.json');binding=read(root/'input-binding.json')
 if original.sha(BASE/'audio.npy')!=data['base_audio_sha256']:raise ValueError('parent audio cache changed')
 if data.get('reserved_mswc_sha256')and original.sha(root/'reserved-mswc.json')!=data['reserved_mswc_sha256']:raise ValueError('reserved MSWC identities changed')
 if original.sha(root/'focus-data.json')!=binding['focus_data_sha256']or original.sha(BASE/'dataset.json')!=data['parent_dataset_sha256']or original.sha(BASE/'best.pt')!=binding['base_checkpoint_sha256']or original.sha(root/'extra-audio.npy')!=data['extra_audio_sha256']:raise ValueError('focused input binding changed')
 if original.sha(Path(__file__))!=binding['script_sha256']or original.sha(Path(__file__).parents[2]/'app/vaakmitra_word/focused_words.py')!=binding['contract_sha256']:raise ValueError('frozen training sources changed')
 return data,binding

def train(root):
 if not torch.cuda.is_available():raise RuntimeError('local CUDA required')
 data,binding=validate_inputs(root);guard_space(root);torch.set_num_threads(4)
 trainset=Clips(root,data,'train');calset=Clips(root,data,'calibration')
 initial=torch.load(BASE/'best.pt',map_location='cpu',weights_only=True);baseline_model=model_from_checkpoint(initial,61).cuda()
 baseline=evaluate(baseline_model,calset);del baseline_model;original.write(root/'baseline-calibration.json',baseline)
 configs=[dict(name='balanced75',seed=701,fraction=.75,encoder_lr=2e-6,head_lr=2e-5,frozen=False),dict(name='frozen80',seed=703,fraction=.8,encoder_lr=0.,head_lr=1e-5,frozen=True)]
 intent=dict(configs=configs,epochs=30,patience=7,max_minutes_each=12,decoder=DECODER,cal_cap=CAL_CAP,test_cap=TEST_CAP,selection_split='calibration',evaluation_accessed=False,binding=binding)
 original.write(root/'training-intent.json',intent);candidates=[]
 for config in configs:
  guard_space(root);out=root/config['name'];out.mkdir(exist_ok=False);torch.manual_seed(config['seed']);torch.cuda.manual_seed_all(config['seed'])
  model=model_from_checkpoint(initial,61).cuda();configure_recurrent_dropout(model,.2)
  opt=torch.optim.AdamW([dict(params=model.encoder.parameters(),lr=config['encoder_lr']),dict(params=list(model.sequence.parameters())+list(model.head.parameters()),lr=config['head_lr'])],weight_decay=.0001)
  criterion=nn.CTCLoss(blank=0,reduction='none',zero_infinity=False);weights=sampling_weights(trainset.rows,config['fraction']);rng=torch.Generator().manual_seed(config['seed']);history=[];best=float('inf');stale=0;start=time.monotonic()
  for epoch in range(1,31):
   guard_space(root);model.train();configure_encoder_training(model,config['frozen'],True)
   sampler=WeightedRandomSampler(weights,len(trainset),replacement=True,generator=torch.Generator().manual_seed(config['seed']+epoch));loss_sum=0
   for audio,targets,lengths,_,_ in loader(trainset,sampler=sampler):
    audio=augment(audio.cuda(non_blocking=True),rng,'channel');opt.zero_grad(set_to_none=True);logits=model(audio)
    loss=(criterion(logits.log_softmax(-1).transpose(0,1),targets.cuda(),torch.full((len(audio),),logits.shape[1],dtype=torch.long),lengths)/lengths.cuda()).mean()
    if not torch.isfinite(loss):raise FloatingPointError('nonfinite focus CTC loss')
    loss.backward();nn.utils.clip_grad_norm_(model.parameters(),5,error_if_nonfinite=True);opt.step();loss_sum+=float(loss.detach())*len(audio)
   cal=evaluate(model,calset);ok=eligible(cal,baseline,CAL_CAP);score=.7*cal['focus18']['phoneme_error_rate']+.3*cal['all']['phoneme_error_rate'];improved=ok and score<best
   stale=0 if improved else stale+1
   if improved:
    best=score;state=copy.copy(initial)
    focus_binding=dict(initial['binding'],row_count=len(data['rows']),focus_data_sha256=binding['focus_data_sha256'])
    focus_binding.pop('binding_sha256',None);focus_binding['binding_sha256']=hashlib.sha256(json.dumps(focus_binding,sort_keys=True).encode()).hexdigest()
    state.update(model={k:v.detach().cpu()for k,v in model.state_dict().items()},optimizer=opt.state_dict(),epoch=epoch,focus_data_sha256=binding['focus_data_sha256'],dataset_sha256=binding['focus_data_sha256'],parent_dataset_sha256=data['parent_dataset_sha256'],binding=focus_binding,formation_method='DEC058_focused_continuation',decoder=DECODER)
    original.save(out/'best.pt',state);original.write(out/'best-calibration.json',cal)
   record=dict(epoch=epoch,loss=loss_sum/len(trainset),calibration=cal,eligible=ok,score=score,elapsed_seconds=time.monotonic()-start,peak_vram_bytes=torch.cuda.max_memory_allocated());history.append(record);original.write(out/'history.json',history);print(json.dumps(dict(trial=config['name'],**record)),flush=True)
   if stale and stale%4==0:
    for group in opt.param_groups:group['lr']*=.5
   if stale>=7 or time.monotonic()-start>12*60:break
  if(out/'best.pt').exists():candidates.append(dict(name=config['name'],score=best,checkpoint_sha256=original.sha(out/'best.pt'),calibration=read(out/'best-calibration.json')))
  del model,opt;torch.cuda.empty_cache()
 decision=dict(eligible_candidates=candidates,winner=min(candidates,key=lambda c:c['score'])if candidates else None,calibration_only=True,evaluation_accessed=False,focus_data_sha256=binding['focus_data_sha256'],decoder=DECODER,script_sha256=binding['script_sha256'])
 original.write(root/'selection-freeze.json',decision);print(json.dumps(dict(stage='calibration_frozen',selection=decision)),flush=True)

def main():
 p=argparse.ArgumentParser();p.add_argument('phase',choices=['prepare','train']);p.add_argument('--root',type=Path,required=True);args=p.parse_args()
 if args.phase=='prepare':prepare(args.root)
 else:train(args.root)
if __name__=='__main__':main()
