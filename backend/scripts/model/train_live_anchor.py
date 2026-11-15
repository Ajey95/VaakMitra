"""DEC067/PHN007: bounded local CUDA controls; no evaluation/private-audio training."""
from __future__ import annotations
if not __debug__:raise RuntimeError('Provenance checks require Python without -O')
import argparse,copy,hashlib,json,shutil,time,uuid
from pathlib import Path
import numpy as np
import torch
from torch import nn
from torch.utils.data import WeightedRandomSampler
from app.vaakmitra_word.live_anchor import clean_anchor_loss,eligible_anchor,select_training_targets
from app.vaakmitra_word.live_anchor_state import commit_epoch,load_trial_commit,select_trial_candidate
from app.vaakmitra_word.focused_words import sampling_weights,metrics,validate_extra_rows
from app.vaakmitra_word.phoneme_ctc import model_from_checkpoint,validate_splits
from app.vaakmitra_word.phoneme_decoder import decode_logits
from scripts.model import finetune_mobile_phoneme as original
from scripts.model.focused_phoneme_update import Clips,loader,DECODER,BASE,reserved_mswc_rows
from scripts.model.improve_mobile_phoneme import tempo_in_padding,configure_encoder_training,configure_recurrent_dropout

REPO=Path(__file__).resolve().parents[3]
DATA=Path('D:/VaakMitraData/artifacts/phoneme-focused25-20261112-v2')
BANK=Path('D:/VaakMitraData/analysis/phoneme-live-debug-20261111/tempo-calibration-bank')
CONFIGS=[dict(name='anchor4_tempo25',seed=811,fraction=.50,encoder_lr=1e-6,head_lr=5e-6,tempo_fraction=.25,anchor=4.),dict(name='anchor8_tempo125',seed=813,fraction=.50,encoder_lr=1e-6,head_lr=5e-6,tempo_fraction=.125,anchor=8.)]
def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):return original.sha(Path(p))
def write(p,v):original.write(p,v)
def guard(root):
    if shutil.disk_usage(root).free<512*1024**2:raise OSError('C512MiB reserve reached')
    if shutil.disk_usage(BASE).free<250*1024**2:raise OSError('D250MiB reserve reached')
    if sum(p.stat().st_size for p in root.rglob('*') if p.is_file())>250*1024**2:raise OSError('run artifact budget reached')
def state_digest(model):
    h=hashlib.sha256()
    for k,v in sorted(model.state_dict().items()):h.update(k.encode());h.update(v.detach().cpu().numpy().tobytes())
    return h.hexdigest()

def training_source_paths():
    return [Path(__file__),REPO/'backend/app/vaakmitra_word/live_anchor.py',REPO/'backend/app/vaakmitra_word/live_anchor_state.py',REPO/'backend/app/vaakmitra_word/phoneme_ctc.py',REPO/'backend/app/vaakmitra_word/mobile_student_model.py',REPO/'backend/app/vaakmitra_word/phoneme_decoder.py',REPO/'backend/scripts/model/focused_phoneme_update.py',REPO/'backend/scripts/model/improve_mobile_phoneme.py',REPO/'backend/scripts/model/finetune_mobile_phoneme.py',REPO/'backend/app/vaakmitra_word/focused_words.py',REPO/'backend/scripts/model/prepare_phoneme_expansion.py']

def publish_checkpoint(out,entry,name):
    if name not in ('last.pt','best.pt'):raise ValueError('Unknown derived checkpoint')
    source=out/entry['file']
    if sha(source)!=entry['sha256']:raise ValueError('Committed source changed')
    temporary=out/(name+'.'+uuid.uuid4().hex+'.tmp')
    shutil.copyfile(source,temporary);temporary.replace(out/name)
    if sha(out/name)!=entry['sha256']:raise ValueError('Derived checkpoint changed')
def preflight(root,resume):
    if not torch.cuda.is_available():raise RuntimeError('CUDA required; no CPU fallback')
    if not resume:root.mkdir(parents=True,exist_ok=False)
    guard(root);data=read(DATA/'focus-data.json');old=read(DATA/'input-binding.json')
    if sha(DATA/'focus-data.json')!=old['focus_data_sha256'] or sha(BASE/'best.pt')!=old['base_checkpoint_sha256']:raise ValueError('frozen focus/checkpoint changed')
    if sha(BASE/'dataset.json')!=data['parent_dataset_sha256'] or sha(BASE/'audio.npy')!=data['base_audio_sha256'] or sha(DATA/'extra-audio.npy')!=data['extra_audio_sha256']:raise ValueError('cache binding changed')
    if data.get('reserved_mswc_sha256') and sha(DATA/'reserved-mswc.json')!=data['reserved_mswc_sha256']:raise ValueError('reserved identities changed')
    prepared_path=Path('D:/VaakMitraData/prepared/mswc-ta-other/manifest.jsonl')
    raw_path=Path('D:/VaakMitraData/manifests/mswc-ta-other.jsonl')
    reserved=reserved_mswc_rows([json.loads(x)for x in prepared_path.read_text(encoding='utf-8').splitlines()],[json.loads(x)for x in raw_path.read_text(encoding='utf-8').splitlines()])
    expansion=read(BASE/'expansion-manifest.json')
    validate_extra_rows([r for r in data['rows'] if r['cache_shard']=='base'],[r for r in data['rows'] if r['cache_shard']=='extra'],expansion['audit']+reserved)
    if not resume:write(root/'reserved-derived.json',reserved)
    validate_splits(data['rows'])
    if any(not r['targets'] or any(type(t)is not int or not 0<t<61 for t in r['targets']) for r in data['rows']):raise ValueError('invalid phone targets')
    bank=read(BANK/'manifest.json')
    if sha(BANK/'audio.npy')!=bank['audio_sha256'] or bank['dataset_sha256']!=data['parent_dataset_sha256'] or any(r['split']!='calibration' for r in bank['records']):raise ValueError('tempo bank changed/not calibration')
    if sha(BANK/'manifest.json')!=read(BANK/'baseline.json')['bank_manifest_sha256']:raise ValueError('historical tempo freeze changed')
    paths=training_source_paths()
    binding={'row_count':len(data['rows']),'focus_data':sha(DATA/'focus-data.json'),'base_checkpoint':sha(BASE/'best.pt'),'base_audio':data['base_audio_sha256'],'extra_audio':data['extra_audio_sha256'],'tempo_manifest':sha(BANK/'manifest.json'),'tempo_audio':bank['audio_sha256'],'sources':{str(p):sha(p) for p in paths}}
    binding['reserved_audit']={'prepared_sha256':sha(prepared_path),'raw_sha256':sha(raw_path),'expansion_sha256':sha(BASE/'expansion-manifest.json'),'derived_sha256':sha(root/'reserved-derived.json')}
    intent={'binding':binding,'configs':CONFIGS,'epochs':8,'minutes_each':12,'time_cap_scope':'epoch_boundary; finish active epoch/checkpoint','patience':6,'batch':64,'aug_ctc_weight':.5,'factors':[1.5,2.],'decoder':DECODER,'selection_split':'calibration','evaluation_inference_accessed':False,'private_audio_used':False,'torch':torch.__version__,'gpu':torch.cuda.get_device_name(0),'output_budget_bytes':250*1024**2}
    if resume:
        if read(root/'training-intent.json')!=intent:raise ValueError('resume intent/source mismatch')
        if(root/'selection-freeze.json').exists():raise ValueError('run already terminal; no reselection')
    else:
        (root/'sources').mkdir()
        for p in paths:shutil.copyfile(p,root/'sources'/p.name)
        write(root/'training-intent.json',intent)
    return data,bank,binding

@torch.no_grad()
def evaluate(model,dataset):
    model.eval();pred=[]
    for x,_,_,_,_ in loader(dataset):pred.extend(decode_logits(a,DECODER) for a in model(x.cuda()).cpu().numpy())
    return metrics(pred,dataset.rows)

@torch.no_grad()
def evaluate_tempo(model,bank):
    model.eval();audio=np.load(BANK/'audio.npy',mmap_mode='r');pred=[]
    rows=[dict(r,practice_id=r.get('word_id')) for r in bank['records']]
    for i in range(0,len(rows),64):pred.extend(decode_logits(a,DECODER) for a in model(torch.from_numpy(audio[i:i+64].copy()).cuda()).cpu().numpy())
    ids=[i for i,r in enumerate(rows) if r['word_id']=='TA_WORD_0001' and r['duration_factor'] in (2.,3.)]
    return {'all':metrics(pred,rows)['all'],'amma':metrics([pred[i] for i in ids],[rows[i] for i in ids])['all']}

def ctc_loss(logits,targets,lengths):
    values=nn.functional.ctc_loss(logits.log_softmax(-1).transpose(0,1),targets.cuda(),torch.full((len(logits),),logits.shape[1],dtype=torch.long),lengths,blank=0,reduction='none',zero_infinity=False)
    return (values/lengths.cuda()).mean()

def checkpoint(initial,model,opt,epoch,config,binding,root):
    state={k:initial[k] for k in ('model_kind','encoder_blocks','frame_shift_ms') if k in initial}
    state.update(model={k:v.detach().cpu() for k,v in model.state_dict().items()},optimizer=opt.state_dict(),epoch=epoch,anchor_config=config,anchor_binding=binding,formation_method='DEC067_clean_anchored_tempo',parent_dataset_sha256=initial['dataset_sha256'],dataset_sha256=binding['focus_data'],focus_data_sha256=binding['focus_data'],decoder=DECODER)
    # Parent counters/RNG/data counts are provenance, never active child run state.
    state['parent_provenance']={'binding':copy.deepcopy(initial['binding']),'dataset_sha256':initial['dataset_sha256'],'checkpoint_sha256':binding.get('base_checkpoint')}
    state['binding']={'focus_data_sha256':binding['focus_data'],'row_count':binding['row_count'],'anchor_source_sha256':sha(Path(__file__)),'vocabulary_sha256':initial['binding'].get('vocabulary_sha256'),'parent_checkpoint_sha256':binding.get('base_checkpoint')}
    state['binding']['binding_sha256']=hashlib.sha256(json.dumps(state['binding'],sort_keys=True).encode()).hexdigest()
    return state

def run(root,resume=False):
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    data,bank,binding=preflight(root,resume);start=time.monotonic()
    print(json.dumps({'stage':'inputs_bound','gpu':torch.cuda.get_device_name(0),'rows':len(data['rows']),'root':str(root)}),flush=True)
    trainset=Clips(DATA,data,'train');calset=Clips(DATA,data,'calibration')
    if any(r['split']!='train' for r in trainset.rows) or any(r['split']!='calibration' for r in calset.rows):raise ValueError('split leakage')
    initial=torch.load(BASE/'best.pt',map_location='cpu',weights_only=True)
    teacher=model_from_checkpoint(initial,61).cuda().requires_grad_(False).eval();teacher_sha=state_digest(teacher)
    if not resume:
        baseline=evaluate(teacher,calset);tempo_base=evaluate_tempo(teacher,bank)
        expected=read(DATA/'baseline-calibration.json')
        if any(baseline[g]['edits']!=expected[g]['edits'] or baseline[g]['phones']!=expected[g]['phones'] for g in ('all','old19','new6','focus18')):raise ValueError('baseline does not reproduce frozen calibration')
        write(root/'baseline-calibration.json',baseline);write(root/'baseline-tempo.json',tempo_base)
    else:baseline=read(root/'baseline-calibration.json');tempo_base=read(root/'baseline-tempo.json')
    print(json.dumps({'stage':'baseline','calibration':baseline,'tempo':tempo_base}),flush=True)
    candidates=[]
    for config in CONFIGS:
        guard(root);out=root/config['name'];out.mkdir(exist_ok=resume)
        torch.manual_seed(config['seed']);torch.cuda.manual_seed_all(config['seed']);torch.cuda.reset_peak_memory_stats()
        model=model_from_checkpoint(initial,61).cuda();configure_recurrent_dropout(model,0.)
        opt=torch.optim.AdamW([dict(params=model.encoder.parameters(),lr=config['encoder_lr']),dict(params=list(model.sequence.parameters())+list(model.head.parameters()),lr=config['head_lr'])],weight_decay=.0001)
        committed=load_trial_commit(out,binding,config)
        history=committed['history'] if committed else []
        selected=select_trial_candidate(out,binding,config,baseline,tempo_base)
        best=selected['score'] if selected else float('inf');stale=0
        for r in reversed(history):
            if r.get('improved'):break
            stale+=1
        if history:
            saved=committed['last']
            model.load_state_dict(saved['model']);opt.load_state_dict(saved['optimizer'])
        weights=sampling_weights(trainset.rows,config['fraction']);trial_start=time.monotonic();previous_elapsed=history[-1]['elapsed_seconds'] if history else 0
        for epoch in range(len(history)+1,9):
            if stale>=6 or previous_elapsed+time.monotonic()-trial_start>=720:break
            guard(root);model.train();configure_encoder_training(model,False,True)
            sampler=WeightedRandomSampler(weights,len(trainset),replacement=True,generator=torch.Generator().manual_seed(config['seed']+epoch))
            rng=torch.Generator().manual_seed(config['seed']*1000+epoch);total=0.;changed=0;seen=0
            for audio,targets,lengths,_,_ in loader(trainset,sampler=sampler):
                x=audio.cuda(non_blocking=True);opt.zero_grad(set_to_none=True)
                with torch.no_grad():old=teacher(x)
                clean=model(x);anchor=clean_anchor_loss(clean,old);loss=ctc_loss(clean,targets,lengths)
                ids=torch.randperm(len(x),generator=rng)[:max(1,int(len(x)*config['tempo_fraction']))]
                source=x.index_select(0,ids.cuda());factor=(1.5,2.)[int(torch.randint(2,(),generator=rng))]
                aug=tempo_in_padding(source,factor);changed+=int(((aug-source).abs().amax(1)>1e-7).sum())
                aug_targets,aug_lengths=select_training_targets(targets,lengths,ids)
                loss=loss+.5*ctc_loss(model(aug),aug_targets,aug_lengths)+config['anchor']*anchor
                if not torch.isfinite(loss):raise FloatingPointError('nonfinite anchored CTC')
                loss.backward();norm=nn.utils.clip_grad_norm_(model.parameters(),5,error_if_nonfinite=True)
                if epoch==1 and seen==0:
                    if any(p.grad is not None for p in teacher.parameters()):raise RuntimeError('teacher received gradients')
                    write(out/'cuda-proof.json',{'batch':len(x),'device':str(x.device),'loss':float(loss.detach()),'grad_norm':float(norm),'teacher_frozen':True,'logits_shape':list(clean.shape)})
                opt.step();seen+=len(x);total+=float(loss.detach())*len(x)
            cal=evaluate(model,calset);tempo=evaluate_tempo(model,bank);ok=eligible_anchor(cal,baseline,tempo,tempo_base)
            score=.6*cal['focus18']['phoneme_error_rate']+.2*cal['all']['phoneme_error_rate']+.2*tempo['all']['phoneme_error_rate'];improved=ok and score<best
            stale=0 if improved else stale+1
            record={'epoch':epoch,'loss':total/seen,'calibration':cal,'tempo':tempo,'eligible':ok,'improved':improved,'score':score,'tempo_changed_samples':changed,'elapsed_seconds':previous_elapsed+time.monotonic()-trial_start,'peak_vram_bytes':torch.cuda.max_memory_allocated()}
            state=checkpoint(initial,model,opt,epoch,config,binding,root)
            entry=commit_epoch(out,state,record,binding,config)
            publish_checkpoint(out,entry,'last.pt')
            if improved:best=score;publish_checkpoint(out,entry,'best.pt');write(out/'best-calibration.json',record)
            history.append(record);write(out/'history.json',history)
            print(json.dumps({'trial':config['name'],**record}),flush=True)
        committed=load_trial_commit(out,binding,config)
        if committed:publish_checkpoint(out,committed['entries'][-1],'last.pt')
        selected=select_trial_candidate(out,binding,config,baseline,tempo_base)
        if selected:
            publish_checkpoint(out,selected,'best.pt');write(out/'best-calibration.json',selected['record'])
            candidates.append({'name':config['name'],'score':selected['score'],'checkpoint_sha256':selected['sha256'],'committed_file':selected['file'],'record':selected['record']})
        if state_digest(teacher)!=teacher_sha:raise RuntimeError('teacher state changed')
        del model,opt;torch.cuda.empty_cache()
    decision={'winner':min(candidates,key=lambda x:x['score']) if candidates else None,'eligible_candidates':candidates,'binding':binding,'decoder':DECODER,'selection_split':'calibration','evaluation_inference_accessed':False,'private_audio_used':False,'elapsed_seconds':time.monotonic()-start,'teacher_unchanged':True}
    write(root/'selection-freeze.json',decision);print(json.dumps({'stage':'calibration_frozen','decision':decision}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--resume',action='store_true');args=parser.parse_args();run(args.root,args.resume)
