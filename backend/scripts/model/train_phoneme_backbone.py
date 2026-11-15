"""DEC068/PHN008: one fixed CUDA tail adaptation; selection on calibration only."""
from __future__ import annotations

import argparse,json,math,time
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import Dataset,DataLoader,WeightedRandomSampler
from transformers import Wav2Vec2Config
from transformers.models.wav2vec2.modeling_wav2vec2 import Wav2Vec2EncoderLayerStableLayerNorm
from app.vaakmitra_word.phoneme_backbone import PhonemeTail,decode_backbone_logits
from app.vaakmitra_word.backbone_training import mixed_sampling_weights,length_aware_ctc_loss
from app.vaakmitra_word.amp_training import scaled_backward_step
from app.vaakmitra_word.backbone_storage import storage_guard
from app.vaakmitra_word.focused_words import metrics
from app.vaakmitra_word.live_anchor import eligible_anchor
from app.vaakmitra_word.live_anchor_state import commit_epoch,load_trial_commit,select_trial_candidate
from scripts.model.cache_phoneme_backbone import ROOT,MODEL,read,write,sha

REPO=Path(__file__).resolve().parents[3]
PRACTICE=REPO/'SpeakEasyAndroid/app/src/main/assets/vaakmitra/practice-words-v1/references.json'
PRACTICE_IDS=('TA_WORD_0001','TA_WORD_0002','TA_WORD_0012','TA_WORD_0013','TA_WORD_0014','TA_WORD_0015','TA_WORD_0016','TA_WORD_0017',
    'TA_WORD_0049','TA_WORD_0050','TA_WORD_0061','TA_WORD_0072','TA_WORD_0082','TA_WORD_0083','TA_WORD_0084','TA_WORD_0086',
    'TA_WORD_0090','TA_WORD_0096','TA_WORD_0098','TA_WORD_0099','TA_WORD_0100','TA_WORD_0101','TA_WORD_0102','TA_WORD_0103','TA_WORD_0104')
CONFIG={'name':'tamil_tail2_all25_s919','seed':919,'tail_blocks':2,'batch':64,'epochs':8,'minutes':35,
        'patience':6,'tail_lr':5e-5,'head_lr':1e-4,'weight_decay':.01,'warmup_fraction':.1,
        'minimum_lr_factor':.1,'focus_fraction':.8,'focus_ids':list(PRACTICE_IDS),'clean_fraction':.75,'dropout':.1,'gradient_clip':1.,
        'max_amp_retries_per_batch':8,'patience_basis':'calibration_score_progress','output_budget_gib':10.}
DECODER={'type':'ctc_prefix_beam','beam_width':5,'nonblank_top_k':8}
BASELINE=Path('D:/VaakMitraData/artifacts/phoneme-focused25-20261112-v2/baseline-calibration.json')
TEMPO_BASELINE=Path('C:/Users/AJEYA/VaakMitraArtifacts/phoneme-live-anchor-20261112-v3/baseline-tempo.json')

def guard():return storage_guard(ROOT,max_output_gib=CONFIG['output_budget_gib'])

def make_tail(initial):
    config=Wav2Vec2Config.from_json_file(str(MODEL/'config.json'));config._attn_implementation='eager'
    tail=PhonemeTail([Wav2Vec2EncoderLayerStableLayerNorm(config)for _ in range(2)],
        nn.LayerNorm(config.hidden_size,eps=config.layer_norm_eps),nn.Linear(config.hidden_size,config.vocab_size),nn.Dropout(.1)).float()
    tail.load_state_dict(initial['tail'],strict=True)
    for layer in tail.layers:layer.attention.dropout=.1
    for module in tail.modules():
        if isinstance(module,nn.Dropout):module.p=.1
    return tail

class Features(Dataset):
    def __init__(self,cache,meta,rows):
        self.rows=rows;self.data=np.memmap(cache/'features.fp16',mode='r',dtype=np.float16,shape=(meta['frames'],1024))
    def __len__(self):return len(self.rows)
    def __getitem__(self,index):
        row=self.rows[index];start=row['offset'];end=start+row['frames']
        return torch.from_numpy(self.data[start:end].copy()),torch.tensor(row['native_targets'],dtype=torch.long),index

def collate(batch):
    length=max(len(x)for x,_,_ in batch)
    x=torch.zeros((len(batch),length,1024),dtype=torch.float16)
    for i,(values,_,_)in enumerate(batch):x[i,:len(values)]=values
    return x,torch.cat([t for _,t,_ in batch]),torch.tensor([len(t)for _,t,_ in batch]),torch.tensor([len(x)for x,_,_ in batch]),[i for _,_,i in batch]

@torch.no_grad()
def evaluate(model,dataset,native,legacy,*,tempo=False):
    model.eval();predictions=[[]for _ in dataset.rows];lookup={p:i for i,p in enumerate(legacy)}
    valid=[i for i,r in enumerate(dataset.rows)if r['frames']>0]
    for start in range(0,len(valid),64):
        ids=valid[start:start+64];batch=[dataset[i]for i in ids]
        x,_,_,lengths,_=collate(batch)
        with torch.autocast('cuda',dtype=torch.float16):values=model(x.cuda(non_blocking=True),lengths).float().cpu().numpy()
        for j,i in enumerate(ids):
            phones=decode_backbone_logits(values[j,:int(lengths[j])],native,DECODER)
            predictions[i]=[lookup.get(p,len(legacy))for p in phones]
    if not tempo:return metrics(predictions,dataset.rows)
    amma=[i for i,r in enumerate(dataset.rows)if r['word_id']=='TA_WORD_0001'and r['factor']in(2.,3.)]
    return {'all':metrics(predictions,dataset.rows)['all'],
        'amma':metrics([predictions[i]for i in amma],[dataset.rows[i]for i in amma])['all']}

def source_paths():
    import app.vaakmitra_word.phoneme_backbone as core
    import app.vaakmitra_word.backbone_training as training
    import app.vaakmitra_word.amp_training as precision
    import app.vaakmitra_word.backbone_storage as storage
    import app.vaakmitra_word.phoneme_decoder as decoder
    import app.vaakmitra_word.focused_words as groups
    import app.vaakmitra_word.live_anchor as gates
    import app.vaakmitra_word.live_anchor_state as commits
    import scripts.model.cache_phoneme_backbone as preparation
    import transformers.models.wav2vec2.modeling_wav2vec2 as encoder
    return [Path(__file__)]+[Path(m.__file__)for m in(core,training,precision,storage,decoder,groups,gates,commits,preparation,encoder)]

def preflight(cache,out,resume):
    if not __debug__ or not torch.cuda.is_available():raise RuntimeError('CUDA/nonoptimized Python required')
    guard();complete=read(cache/'cache-complete.json');origin=read(cache/'cache-intent.json')
    for filename,key in (('features.fp16','features_sha256'),('features.json','metadata_sha256'),('tail-initial.pt','tail_initial_sha256'),('cache-intent.json','intent_sha256')):
        if sha(cache/filename)!=complete[key]:raise ValueError('Frozen feature cache differs')
    for path,digest in origin['sources'].items():
        if sha(path)!=digest:raise ValueError('Cache source changed; no silent rebinding')
    for name,digest in origin['model_files'].items():
        if sha(MODEL/name)!=digest:raise ValueError('Backbone configuration/vocabulary changed')
    if origin['private_child_audio_used']or origin['reserved_evaluation_inferred']:raise ValueError('Invalid cache origin')
    meta=read(cache/'features.json')
    if (cache/'features.fp16').stat().st_size!=meta['frames']*1024*2:raise ValueError('Feature shape differs')
    rows=meta['records']
    if any(r['split']not in ('train','calibration')or r['frames']<0 or r['offset']<0 or r['offset']+r['frames']>meta['frames']for r in rows):raise ValueError('Invalid feature row/split')
    train=[r for r in rows if r['split']=='train'];cal=[r for r in rows if r['kind']=='calibration'];tempo=[r for r in rows if r['kind']=='calibration_tempo']
    if len(cal)!=1630 or len(tempo)!=315 or len(train)!=meta['train_source_parents']*2:raise ValueError('Frozen denominator differs')
    if set(read(PRACTICE)['expected'])!=set(PRACTICE_IDS) or set(PRACTICE_IDS)-{r['practice_id']for r in train}:
        raise ValueError('All25 practice scope differs or lacks training examples')
    mixed_sampling_weights(train,CONFIG['focus_fraction'],CONFIG['clean_fraction'],focus_ids=CONFIG['focus_ids'])
    initial=torch.load(cache/'tail-initial.pt',map_location='cpu',weights_only=True)
    if initial['cache_intent_sha256']!=complete['intent_sha256']or initial['native_vocab']!=meta['native_vocab']:raise ValueError('Initial tail binding differs')
    paths=source_paths()
    binding={'protocol':'DEC068_backbone_tail','cache_complete_sha256':sha(cache/'cache-complete.json'),
        'cache_metadata_sha256':complete['metadata_sha256'],'features_sha256':complete['features_sha256'],
        'initial_tail_sha256':complete['tail_initial_sha256'],'model_sha256':origin['model']['verified_sha256'],
        'baseline_calibration_sha256':sha(BASELINE),'baseline_tempo_sha256':sha(TEMPO_BASELINE),'practice_scope_sha256':sha(PRACTICE),
        'sources':{str(p):sha(p)for p in paths}}
    intent={'binding':binding,'config':CONFIG,'decoder':DECODER,'selection_split':'calibration',
        'reserved_evaluation_inferred':False,'private_child_audio_used':False,'torch':torch.__version__,
        'actual_valid_frames':True,'epoch_draws':meta['train_source_parents'],'cache':str(cache),
        'runtime_cap':'35minutes at epoch boundary; finish active epoch/commit',
        'amp_policy':'skip verified overflow; restore dropout RNG and retry same batch max8; no scheduler advance until finite update'}
    if resume:
        if read(out/'training-intent.json')!=intent:raise ValueError('Resume source/config mismatch')
        if(out/'selection-freeze.json').exists():raise ValueError('Terminal run cannot be reselected')
    else:
        out.mkdir(parents=True,exist_ok=False);write(out/'training-intent.json',intent);(out/'sources').mkdir()
        import shutil
        for i,path in enumerate(paths):shutil.copyfile(path,out/'sources'/f'{i:02}-{path.name}')
    return meta,initial,binding,train,cal,tempo

def run(cache,out,resume=False):
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    torch.manual_seed(CONFIG['seed']);torch.cuda.manual_seed_all(CONFIG['seed'])
    meta,initial,binding,train,cal,tempo=preflight(cache,out,resume)
    model=make_tail(initial).cuda();del initial
    trainset=Features(cache,meta,train);calset=Features(cache,meta,cal);temposet=Features(cache,meta,tempo)
    baseline=read(BASELINE);tempo_base=read(TEMPO_BASELINE)
    native=meta['native_vocab'];legacy=meta['legacy_tokens']
    opt=torch.optim.AdamW([{'params':list(model.layers.parameters())+list(model.norm.parameters()),'lr':CONFIG['tail_lr']},
        {'params':model.head.parameters(),'lr':CONFIG['head_lr']}],weight_decay=CONFIG['weight_decay'])
    steps=math.ceil(meta['train_source_parents']/CONFIG['batch']);total_steps=steps*8;warmup=max(1,math.ceil(total_steps*.1))
    def rate(step):return (step+1)/warmup if step<warmup else max(.1,1-.9*(step-warmup)/max(1,total_steps-warmup))
    scheduler=torch.optim.lr_scheduler.LambdaLR(opt,rate);scaler=torch.amp.GradScaler('cuda')
    trial=out/CONFIG['name'];trial.mkdir(exist_ok=resume)
    committed=load_trial_commit(trial,binding,CONFIG)
    history=committed['history']if committed else[]
    selected=select_trial_candidate(trial,binding,CONFIG,baseline,tempo_base)
    best=selected['score']if selected else float('inf');progress_best=min((r['score']for r in history),default=float('inf'));stale=0
    for record in reversed(history):
        if record['progress_improved']:break
        stale+=1
    if committed:
        saved=committed['last'];model.load_state_dict(saved['model'],strict=True);opt.load_state_dict(saved['optimizer'])
        scheduler.load_state_dict(saved['scheduler']);scaler.load_state_dict(saved['scaler'])
        torch.set_rng_state(saved['torch_rng']);torch.cuda.set_rng_state_all(saved['cuda_rng']);del saved,committed
    else:
        measured=evaluate(model,calset,native,legacy);mt=evaluate(model,temposet,native,legacy,tempo=True)
        write(out/'initial-calibration.json',{'calibration':measured,'tempo':mt,'eligible':eligible_anchor(measured,baseline,mt,tempo_base)})
        print(json.dumps({'stage':'initial_calibration','calibration':measured,'tempo':mt}),flush=True)
    weights=mixed_sampling_weights(train,CONFIG['focus_fraction'],CONFIG['clean_fraction'],focus_ids=CONFIG['focus_ids'])
    prior_elapsed=history[-1]['elapsed_seconds']if history else 0.;started=time.monotonic()
    torch.cuda.reset_peak_memory_stats()
    for epoch in range(len(history)+1,9):
        if stale>=6 or prior_elapsed+time.monotonic()-started>=35*60:break
        guard();model.train();total_loss=0.;seen=0;amp_retries=0
        sampler=WeightedRandomSampler(weights,meta['train_source_parents'],replacement=True,generator=torch.Generator().manual_seed(CONFIG['seed']+epoch))
        batches=DataLoader(trainset,batch_size=64,sampler=sampler,num_workers=0,pin_memory=True,collate_fn=collate)
        for features,targets,target_lengths,frames,_ in batches:
            features_cuda=features.cuda(non_blocking=True)
            cpu_rng=torch.get_rng_state();cuda_rng=torch.cuda.get_rng_state_all()
            for retry in range(CONFIG['max_amp_retries_per_batch']+1):
                if retry:torch.set_rng_state(cpu_rng);torch.cuda.set_rng_state_all(cuda_rng)
                opt.zero_grad(set_to_none=True)
                with torch.autocast('cuda',dtype=torch.float16):logits=model(features_cuda,frames)
                loss=length_aware_ctc_loss(logits,targets,target_lengths,frames,blank=native['[PAD]'])
                if epoch==1 and seen==0:guard()
                norm=scaled_backward_step(loss,model.parameters(),opt,scaler,CONFIG['gradient_clip'])
                if norm is not None:break
                amp_retries+=1
                print(json.dumps({'stage':'amp_overflow_retry','epoch':epoch,'processed_examples':seen,
                    'retry':retry+1,'new_scale':scaler.get_scale(),'optimizer_step_skipped':True}),flush=True)
            else:raise FloatingPointError('Repeated nonfinite gradients after bounded AMP recovery')
            scheduler.step()
            if epoch==1 and seen==0:
                write(out/'cuda-update-proof.json',{'device':str(logits.device),'batch':len(features),'max_frames':int(frames.max()),
                    'loss':float(loss.detach()),'gradient_norm':float(norm),'optimizer_step_completed':True,
                    'trainable_parameters':sum(p.numel()for p in model.parameters()),'prefix_parameters_present_in_optimizer':False,
                    'actual_lengths_used':True,'first_batch_retries':retry,'amp_scale':scaler.get_scale(),
                    'intent_sha256':sha(out/'training-intent.json')})
            total_loss+=float(loss.detach())*len(features);seen+=len(features)
            del features_cuda
        model.eval();calibration=evaluate(model,calset,native,legacy);tm=evaluate(model,temposet,native,legacy,tempo=True)
        eligible=eligible_anchor(calibration,baseline,tm,tempo_base)
        score=.6*calibration['focus18']['phoneme_error_rate']+.2*calibration['all']['phoneme_error_rate']+.2*tm['all']['phoneme_error_rate']
        improved=eligible and score<best
        if improved:best=score
        progress_improved=score<progress_best
        if progress_improved:progress_best=score;stale=0
        else:stale+=1
        record={'epoch':epoch,'loss':total_loss/seen,'calibration':calibration,'tempo':tm,'eligible':eligible,'improved':improved,
            'score':score,'elapsed_seconds':prior_elapsed+time.monotonic()-started,'peak_vram_bytes':torch.cuda.max_memory_allocated(),
            'amp_overflow_retries':amp_retries,'progress_improved':progress_improved}
        state={'model_kind':'wav2vec2_tail','model':{k:v.detach().cpu()for k,v in model.state_dict().items()},
            'optimizer':opt.state_dict(),'scheduler':scheduler.state_dict(),'scaler':scaler.state_dict(),
            'epoch':epoch,'anchor_binding':binding,'anchor_config':CONFIG,'torch_rng':torch.get_rng_state(),'cuda_rng':torch.cuda.get_rng_state_all(),
            'native_vocab':native,'formation_method':'DEC068_frozen22_supervised_tail2','source_train_parents':meta['train_source_parents']}
        commit_epoch(trial,state,record,binding,CONFIG);history.append(record);write(trial/'history.json',history)
        print(json.dumps({'stage':'epoch',**record}),flush=True)
        del state
    chosen=select_trial_candidate(trial,binding,CONFIG,baseline,tempo_base)
    decision={'winner':dict(chosen,trial=CONFIG['name'])if chosen else None,'binding':binding,'decoder':DECODER,
        'selection_split':'calibration','reserved_evaluation_inferred':False,'private_child_audio_used':False,
        'history_epochs':len(history),'production_ready':False,'approved_for_child_scoring':False}
    write(out/'selection-freeze.json',decision);print(json.dumps({'stage':'calibration_frozen','decision':decision}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--cache',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--resume',action='store_true');args=parser.parse_args();run(args.cache,args.output,args.resume)
