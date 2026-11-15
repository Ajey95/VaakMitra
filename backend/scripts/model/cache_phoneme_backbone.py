"""DEC068/PHN008: immutable frozen-prefix features; no gradients or private audio."""
from __future__ import annotations

import argparse,hashlib,json,os,shutil,time
from pathlib import Path
import numpy as np
import torch
import transformers
from transformers import Wav2Vec2Config,Wav2Vec2ForCTC
from app.vaakmitra_word.phoneme_backbone import (
    normalize_and_pad,feature_lengths,map_target_ids,ctc_min_frames,
    split_backbone,decode_backbone_logits,
)
from scripts.model.improve_mobile_phoneme import tempo_in_padding

ROOT=Path('E:/VaakMitraModelLab/20261112-phoneme-transfer')
REPO=Path(__file__).resolve().parents[3]
MODEL=ROOT/'models/speech31-tamil'
DATA=Path('D:/VaakMitraData/artifacts/phoneme-focused25-20261112-v2')
BASE=Path('D:/VaakMitraData/artifacts/phoneme-ta19-v7-improved')
BANK=Path('D:/VaakMitraData/analysis/phoneme-live-debug-20261111/tempo-calibration-bank')
DECODER={'type':'ctc_prefix_beam','beam_width':5,'nonblank_top_k':8}
SEED=919

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb')as source:
        for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
    return h.hexdigest()
def write(p,value):
    p=Path(p);temporary=p.with_suffix(p.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8')as f:
        json.dump(value,f,indent=2,ensure_ascii=False);f.flush();os.fsync(f.fileno())
    temporary.replace(p)
def guard():
    free={drive:shutil.disk_usage(drive+':/').free for drive in ('C','D','E')}
    if free['E']<2*1024**3 or free['C']<512*1024**2 or free['D']<250*1024**2:
        raise OSError('Backbone storage reserve reached; free_bytes='+json.dumps(free))
    total=sum(p.stat().st_size for top in ROOT.iterdir()if top.name not in ('models','deps','tmp')for p in ([top]if top.is_file()else top.rglob('*'))if p.is_file())
    if total>7.5*1024**3:raise OSError('Backbone output budget reached')
    return free

def load_full_model(dtype=torch.float16,device='cuda'):
    if sha(MODEL/'pytorch_model.bin')!=read(MODEL/'download-proof.json')['verified_sha256']:
        raise ValueError('Public model weight hash changed')
    config=Wav2Vec2Config.from_json_file(str(MODEL/'config.json'))
    if config.hidden_size!=1024 or config.num_hidden_layers!=24 or config.vocab_size!=39 or config.pad_token_id!=38 or not config.do_stable_layer_norm:
        raise ValueError('Unexpected public model architecture')
    config._attn_implementation='eager'
    previous=torch.get_default_dtype();torch.set_default_dtype(dtype)
    try:
        with torch.device(device):model=Wav2Vec2ForCTC(config)
    finally:torch.set_default_dtype(previous)
    state=torch.load(MODEL/'pytorch_model.bin',map_location='cpu',weights_only=True,mmap=True)
    if not isinstance(state,dict)or any(not isinstance(v,torch.Tensor)for v in state.values()):raise ValueError('Only tensor model state is permitted')
    remapped={k.replace('.weight_g','.parametrizations.weight.original0').replace('.weight_v','.parametrizations.weight.original1'):v for k,v in state.items()}
    model.load_state_dict(remapped,strict=True)
    return model.eval().requires_grad_(False)

def waveform(fixed):
    nonzero=np.flatnonzero(fixed!=0)
    if not len(nonzero):return np.empty(0,dtype=np.float32)
    return np.array(fixed[nonzero[0]:nonzero[-1]+1],dtype=np.float32)

def sources():
    import app.vaakmitra_word.phoneme_backbone as core
    import app.vaakmitra_word.phoneme_decoder as decoder
    import scripts.model.improve_mobile_phoneme as augmentation
    import scripts.model.finetune_mobile_phoneme as finetune
    import app.vaakmitra_word.phoneme_ctc as legacy_arch
    import app.vaakmitra_word.mobile_student_model as legacy_encoder
    import transformers.models.wav2vec2.modeling_wav2vec2 as implementation
    import transformers.models.wav2vec2.configuration_wav2vec2 as configuration
    return [Path(__file__)]+[Path(m.__file__)for m in (core,decoder,augmentation,finetune,legacy_arch,legacy_encoder,implementation,configuration)]

def main(out):
    if not __debug__ or not torch.cuda.is_available():raise RuntimeError('Nonoptimized Python and CUDA required')
    torch.set_num_threads(2);torch.set_num_interop_threads(1);torch.manual_seed(SEED);torch.cuda.manual_seed_all(SEED)
    out.mkdir(parents=True,exist_ok=False);guard()
    started=time.monotonic();data=read(DATA/'focus-data.json');bank=read(BANK/'manifest.json');vocab=read(BASE/'bundle/vocabulary.json');native=read(MODEL/'vocab.json')
    expected=read(DATA/'input-binding.json')
    if sha(DATA/'focus-data.json')!=expected['focus_data_sha256']:raise ValueError('Frozen focused data changed')
    for p,h in ((BASE/'audio.npy',data['base_audio_sha256']),(DATA/'extra-audio.npy',data['extra_audio_sha256']),(BANK/'audio.npy',bank['audio_sha256'])):
        if sha(p)!=h:raise ValueError('Frozen input cache changed')
    sourcepaths=sources()
    intent={'protocol':'DEC068 frozen22block prefix; no gradients', 'seed':SEED,'tail_blocks':2,
        'data_sha256':sha(DATA/'focus-data.json'),'base_audio_sha256':data['base_audio_sha256'],
        'extra_audio_sha256':data['extra_audio_sha256'],'bank_manifest_sha256':sha(BANK/'manifest.json'),
        'bank_audio_sha256':bank['audio_sha256'],'model':read(MODEL/'download-proof.json'),
        'model_files':{n:sha(MODEL/n)for n in ('config.json','vocab.json','preprocessor_config.json')},
        'sources':{str(p):sha(p)for p in sourcepaths},'torch':torch.__version__,'transformers':transformers.__version__,
        'numpy':np.__version__,'gpu':torch.cuda.get_device_name(0),'private_child_audio_used':False,
        'reserved_evaluation_inferred':False,'feature_dtype':'float16','width':1024,'max_cache_minutes':45,
        'augmentation':'one deterministic safe1.5x/2x per feasible train parent only','decoder':DECODER,
        'cache_batch_size':4,'augmentation_device':'cpu'}
    write(out/'cache-intent.json',intent);(out/'sources').mkdir()
    for i,p in enumerate(sourcepaths):shutil.copyfile(p,out/'sources'/f'{i:02}-{p.name}')
    base=np.load(BASE/'audio.npy',mmap_mode='r');extra=np.load(DATA/'extra-audio.npy',mmap_mode='r');tempo=np.load(BANK/'audio.npy',mmap_mode='r')
    def fixed(row):return np.array((base if row['cache_shard']=='base'else extra)[row['cache_index']],dtype=np.float32)
    train=[(i,r)for i,r in enumerate(data['rows'])if r['split']=='train']
    cal=[(i,r)for i,r in enumerate(data['rows'])if r['split']=='calibration']
    if len(train)!=14919 or len(cal)!=1630 or any(r['split']!='calibration'for r in bank['records']):raise ValueError('Split inventory changed')
    feasible=[];rejected=[]
    for i,row in train:
        target=map_target_ids(row['targets'],vocab['tokens'],native);x=waveform(fixed(row))
        if len(x)<400 or int(feature_lengths(torch.tensor([len(x)]))[0])<ctc_min_frames(target):
            rejected.append({'source_row':i,'reason':'IMPOSSIBLE_VALID_CTC_LENGTH','samples':len(x),'minimum_ctc_frames':ctc_min_frames(target)})
        else:feasible.append((i,row))
    write(out/'train-rejections.json',rejected)
    model=load_full_model();torch.cuda.reset_peak_memory_stats()
    proofwaves=[waveform(fixed(r))for _,r in feasible[:4]]
    values,mask=normalize_and_pad(proofwaves);x=torch.from_numpy(values).cuda().half();attention=torch.from_numpy(mask).cuda();lengths=feature_lengths(attention.sum(-1))
    with torch.no_grad():expected_logits=model(x,attention_mask=attention).logits.float().cpu().numpy()
    prefix,tail=split_backbone(model,2);tail.eval()
    with torch.no_grad(),torch.autocast('cuda',dtype=torch.float16):
        hidden=prefix(x,attention_mask=attention).last_hidden_state
        actual=tail(hidden,lengths).float().cpu().numpy()
    diff=float(np.max(np.abs(expected_logits-actual)));matched=[]
    for i,length in enumerate(lengths.tolist()):
        matched.append(decode_backbone_logits(expected_logits[i,:length],native,DECODER)==decode_backbone_logits(actual[i,:length],native,DECODER))
    if diff>.05 or not all(matched):raise ValueError('Actual CUDA full/prefix-tail parity failed')
    write(out/'cuda-prefix-parity.json',{'public_train_clips':len(proofwaves),'max_abs_logit_error':diff,'all_decoded_match':all(matched),'no_gradients':True,'peak_gpu_bytes':torch.cuda.max_memory_allocated()})
    torch.save({'tail':{k:v.detach().cpu()for k,v in tail.state_dict().items()},'native_vocab':native,
        'source_model_sha256':intent['model']['verified_sha256'],'tail_blocks':2,'cache_intent_sha256':sha(out/'cache-intent.json')},out/'tail-initial.pt')
    del tail,model,x,attention,hidden;torch.cuda.empty_cache()
    records=[];offset=0;partial=out/'features.fp16.partial'
    with partial.open('xb')as stream:
        def emit(group,kind,split):
            nonlocal offset
            for start in range(0,len(group),4):
                if time.monotonic()-started>45*60:raise TimeoutError('Feature cache45minute bound reached')
                selected=group[start:start+4]
                matrices=np.stack([fixed(r)for _,r in selected])if kind!='calibration_tempo'else np.array(tempo[start:start+len(selected)])
                changed=[False]*len(selected);factor=1.
                if kind=='train_tempo':
                    factor=1.5 if start//4%2==0 else 2.
                    augmented=tempo_in_padding(torch.from_numpy(matrices),factor).numpy()
                    changed=[bool(np.any(a!=b))for a,b in zip(augmented,matrices)];matrices=augmented
                waves=[waveform(a)for a in matrices]
                valid_indices=[i for i,w in enumerate(waves)if len(w)>=400]
                cached={}
                if valid_indices:
                    values,mask=normalize_and_pad([waves[i]for i in valid_indices]);valid_lengths=feature_lengths(torch.from_numpy(mask).sum(-1))
                    with torch.no_grad():features=prefix(torch.from_numpy(values).cuda().half(),attention_mask=torch.from_numpy(mask).cuda()).last_hidden_state.cpu().numpy()
                    if not np.isfinite(features).all():raise FloatingPointError('Nonfinite frozen feature')
                    cached={i:features[j,:int(valid_lengths[j])].copy()for j,i in enumerate(valid_indices)}
                for j,(source_index,row)in enumerate(selected):
                    feature=cached.get(j,np.empty((0,1024),dtype=np.float16))
                    if split=='train'and not len(feature):raise ValueError('Feasible train parent became empty')
                    stream.write(feature.astype(np.float16,copy=False).tobytes())
                    records.append({'source_row':source_index,'kind':kind,'split':split,'offset':offset,'frames':len(feature),
                        'samples':len(waves[j]),'targets':row['targets'],'native_targets':map_target_ids(row['targets'],vocab['tokens'],native),
                        'practice_id':row.get('practice_id')or row.get('word_id'),'word_id':row.get('word_id'),
                        'is_target':row['is_target'],'speaker':row['speaker'],'audio_sha256':row['audio_sha256'],
                        'factor':factor if kind=='train_tempo'else row.get('duration_factor',1.),'augmentation_changed':changed[j]})
                    offset+=len(feature)
                if start%400==0:
                    free=guard();print(json.dumps({'stage':'prefix_features','kind':kind,'done':start+len(selected),'total':len(group),'elapsed_seconds':round(time.monotonic()-started),'free_bytes':free}),flush=True)
        emit(feasible,'train_clean','train');emit(feasible,'train_tempo','train');emit(cal,'calibration','calibration')
        bank_rows=[(i,dict(r,practice_id=r['word_id']))for i,r in enumerate(bank['records'])]
        emit(bank_rows,'calibration_tempo','calibration')
        stream.flush();os.fsync(stream.fileno())
    partial.replace(out/'features.fp16')
    if (out/'features.fp16').stat().st_size!=offset*1024*2:raise ValueError('Ragged cache byte count differs')
    metadata={'schema':'phoneme-frozen-prefix-v1','width':1024,'dtype':'float16','frames':offset,'records':records,
        'train_source_parents':len(feasible),'rejected_train_parents':len(rejected),'native_vocab':native,'legacy_tokens':vocab['tokens']}
    write(out/'features.json',metadata)
    complete={'intent_sha256':sha(out/'cache-intent.json'),'features_sha256':sha(out/'features.fp16'),
        'metadata_sha256':sha(out/'features.json'),'tail_initial_sha256':sha(out/'tail-initial.pt'),
        'elapsed_seconds':time.monotonic()-started,'private_child_audio_used':False,'gradients':False,
        'records':len(records),'frames':offset,'calibration_denominators_preserved':len(cal)==1630}
    write(out/'cache-complete.json',complete);print(json.dumps({'stage':'cache_frozen',**complete}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
    main(parser.parse_args().output)
