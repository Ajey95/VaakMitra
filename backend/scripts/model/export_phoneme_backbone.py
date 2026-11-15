"""DEC068/PHN008: qualified frozen tail -> authenticated full FP32 dynamic ONNX.

Only calibration is inferred here. Quantization/precision choice must be frozen
before the separate reserved-cohort evaluation. No word reaches model/decoder.
"""
from __future__ import annotations
import argparse,json,shutil,time
from pathlib import Path
import numpy as np
import torch
import transformers
from app.vaakmitra_word.backbone_export import install_tail,export_backbone_graph
from app.vaakmitra_word.phoneme_backbone import normalize_and_pad,feature_lengths,decode_backbone_logits
from app.vaakmitra_word.backbone_storage import storage_guard
from app.vaakmitra_word.live_anchor import eligible_anchor
from app.vaakmitra_word.live_anchor_state import select_trial_candidate
from app.vaakmitra_word.focused_words import metrics
from scripts.model.cache_phoneme_backbone import ROOT,MODEL,BASE,DATA,BANK,read,write,sha,waveform,load_full_model
from scripts.model.train_phoneme_backbone import make_tail,BASELINE,TEMPO_BASELINE

DECODER={'type':'ctc_prefix_beam','beam_width':5,'nonblank_top_k':8}

def source_paths():
    import app.vaakmitra_word.backbone_export as exporter
    import app.vaakmitra_word.phoneme_backbone as core
    import app.vaakmitra_word.phoneme_decoder as decoder
    import scripts.model.cache_phoneme_backbone as cache
    import scripts.model.train_phoneme_backbone as trainer
    import transformers.models.wav2vec2.modeling_wav2vec2 as modeling
    import transformers.modeling_attn_mask_utils as masks
    import torch.onnx.utils as onnx_utils
    return [Path(__file__)]+[Path(m.__file__)for m in(exporter,core,decoder,cache,trainer,modeling,masks,onnx_utils)]

def authenticate(training):
    intent=read(training/'training-intent.json');freeze=read(training/'selection-freeze.json')
    if not freeze.get('winner')or freeze['binding']!=intent['binding']or freeze['decoder']!=DECODER:
        raise ValueError('No bound qualified calibration winner')
    if freeze['reserved_evaluation_inferred']or freeze['private_child_audio_used']:raise ValueError('Invalid training origin')
    for p,h in intent['binding']['sources'].items():
        if sha(p)!=h:raise ValueError('Training source changed before export')
    baseline=read(BASELINE);tempo_base=read(TEMPO_BASELINE)
    for p,key in ((BASELINE,'baseline_calibration_sha256'),(TEMPO_BASELINE,'baseline_tempo_sha256')):
        if sha(p)!=intent['binding'][key]:raise ValueError('Qualification baseline changed')
    selected=select_trial_candidate(training/intent['config']['name'],intent['binding'],intent['config'],baseline,tempo_base)
    if selected is None or dict(selected,trial=intent['config']['name'])!=freeze['winner']:
        raise ValueError('Selection freeze differs from committed qualified state')
    cache=Path(intent['cache']);complete=read(cache/'cache-complete.json');origin=read(cache/'cache-intent.json')
    if sha(cache/'cache-complete.json')!=intent['binding']['cache_complete_sha256']:raise ValueError('Cache completion changed')
    for filename,key in (('features.fp16','features_sha256'),('features.json','metadata_sha256'),('tail-initial.pt','tail_initial_sha256'),('cache-intent.json','intent_sha256')):
        if sha(cache/filename)!=complete[key]:raise ValueError('Frozen cache changed')
    for filename,h in origin['model_files'].items():
        if sha(MODEL/filename)!=h:raise ValueError('Source model configuration changed')
    if sha(MODEL/'pytorch_model.bin')!=intent['binding']['model_sha256']:raise ValueError('Source model weights changed')
    if sha(DATA/'focus-data.json')!=origin['data_sha256']or sha(BANK/'manifest.json')!=origin['bank_manifest_sha256']:
        raise ValueError('Calibration inventory changed')
    for p,key in ((BASE/'audio.npy','base_audio_sha256'),(DATA/'extra-audio.npy','extra_audio_sha256'),(BANK/'audio.npy','bank_audio_sha256')):
        if sha(p)!=origin[key]:raise ValueError('Calibration audio cache changed')
    return intent,freeze,cache,origin

def main(training,out):
    if not __debug__ or not torch.cuda.is_available():raise RuntimeError('Nonoptimized CUDA Python required')
    torch.set_num_threads(2);torch.set_num_interop_threads(1)
    storage_guard(ROOT);intent,freeze,cache,origin=authenticate(training)
    if shutil.disk_usage('E:/').free<(MODEL/'pytorch_model.bin').stat().st_size+2*1024**3:
        raise OSError('Full export would consume E reserve')
    out.mkdir(parents=True,exist_ok=False);paths=source_paths()
    export_intent={'protocol':'DEC068/PHN008/3.3.55 qualified FP32 reconstruction',
        'training_intent_sha256':sha(training/'training-intent.json'),'selection_freeze_sha256':sha(training/'selection-freeze.json'),
        'checkpoint_sha256':freeze['winner']['sha256'],'source_model_sha256':intent['binding']['model_sha256'],
        'sources':{str(p):sha(p)for p in paths},'torch':str(torch.__version__),'transformers':transformers.__version__,'numpy':np.__version__,
        'decoder':DECODER,'input_samples':'dynamic400..48000','output_frames':'exact valid convolution1..149',
        'native_units':39,'blank_reordered_to':0,'private_child_audio_used':False,'reserved_evaluation_inferred':False,
        'quantization_ready':False,'production_ready':False,'approved_for_child_scoring':False}
    write(out/'export-intent.json',export_intent);(out/'sources').mkdir()
    for i,p in enumerate(paths):shutil.copyfile(p,out/'sources'/f'{i:02}-{p.name}')
    started=time.monotonic();initial=torch.load(cache/'tail-initial.pt',weights_only=True,map_location='cpu')
    checkpoint=training/freeze['winner']['trial']/freeze['winner']['file']
    if sha(checkpoint)!=freeze['winner']['sha256']:raise ValueError('Selected checkpoint changed')
    state=torch.load(checkpoint,weights_only=True,map_location='cpu')
    if state.get('model_kind')!='wav2vec2_tail'or state['anchor_binding']!=intent['binding']:raise ValueError('Wrong tail checkpoint')
    tail=make_tail(initial);tail.load_state_dict(state['model'],strict=True);del state,initial
    full=load_full_model(dtype=torch.float32,device='cuda').to('cuda');install_tail(full,tail);del tail
    native=read(MODEL/'vocab.json');legacy=read(BASE/'bundle/vocabulary.json')['tokens'];lookup={p:i for i,p in enumerate(legacy)}
    data=read(DATA/'focus-data.json');bank=read(BANK/'manifest.json')
    base=np.load(BASE/'audio.npy',mmap_mode='r');extra=np.load(DATA/'extra-audio.npy',mmap_mode='r');tempo=np.load(BANK/'audio.npy',mmap_mode='r')
    natural=[(i,r)for i,r in enumerate(data['rows'])if r['split']=='calibration'];slowed=list(enumerate(bank['records']))
    if len(natural)!=1630 or len(slowed)!=315 or any(r['split']!='calibration'for _,r in slowed):raise ValueError('Calibration denominator differs')
    predictions={};records=[];torch.cuda.reset_peak_memory_stats()
    with torch.inference_mode():
        for kind,group in (('calibration',natural),('calibration_tempo',slowed)):
            predicted=[[]for _ in group]
            for start in range(0,len(group),4):
                storage_guard(ROOT)
                selected=group[start:start+4]
                waves=[waveform(np.asarray(tempo[i]if kind=='calibration_tempo'else (base if r['cache_shard']=='base'else extra)[r['cache_index']],dtype=np.float32))for i,r in selected]
                valid=[j for j,w in enumerate(waves)if len(w)>=400];decoded={}
                if valid:
                    values,mask=normalize_and_pad([waves[j]for j in valid]);lengths=feature_lengths(torch.from_numpy(mask).sum(-1))
                    logits=full(torch.from_numpy(values).cuda(),attention_mask=torch.from_numpy(mask).cuda()).logits.cpu().numpy()
                    for j,k in enumerate(valid):decoded[k]=decode_backbone_logits(logits[j,:int(lengths[j])],native,DECODER)
                for j,(index,row)in enumerate(selected):
                    phones=decoded.get(j,[]);predicted[start+j]=[lookup.get(p,len(legacy))for p in phones]
                    records.append({'kind':kind,'source_row':index,'audio_sha256':row['audio_sha256'],'phones':phones,'samples':len(waves[j])})
                if start%400==0:print(json.dumps({'stage':'full_fp32_calibration','kind':kind,'done':start+len(selected),'total':len(group)}),flush=True)
            predictions[kind]=predicted
    cal_rows=[r for _,r in natural];tempo_rows=[dict(r,practice_id=r['word_id'])for _,r in slowed]
    calibration=metrics(predictions['calibration'],cal_rows)
    amma=[i for i,r in enumerate(tempo_rows)if r['word_id']=='TA_WORD_0001'and r['duration_factor']in(2.,3.)]
    measured_tempo={'all':metrics(predictions['calibration_tempo'],tempo_rows)['all'],
        'amma':metrics([predictions['calibration_tempo'][i]for i in amma],[tempo_rows[i]for i in amma])['all']}
    qualified=eligible_anchor(calibration,read(BASELINE),measured_tempo,read(TEMPO_BASELINE))
    report={'calibration':calibration,'tempo':measured_tempo,'eligible':qualified,'precision':'FP32_full_reconstructed',
        'elapsed_seconds':time.monotonic()-started,'peak_gpu_bytes':torch.cuda.max_memory_allocated(),'reserved_evaluation_inferred':False}
    write(out/'full-calibration.json',report);write(out/'calibration-predictions.json',records)
    if not qualified:raise RuntimeError('Full FP32 reconstruction failed unchanged qualification gates')
    storage_guard(ROOT);export_backbone_graph(full,out/'phoneme.fp32.onnx')
    del full;torch.cuda.empty_cache();storage_guard(ROOT)
    inverse={i:p for p,i in native.items()};blank=native['[PAD]'];order=[blank]+[i for i in range(len(native))if i!=blank]
    tokens=['<blank>']+[inverse[i]for i in order[1:]]
    write(out/'vocabulary.json',{'schema':'phoneme-ta-backbone-v1','tokens':tokens,'frame_shift_ms':20,'max_output_frames':149})
    complete={'export_intent_sha256':sha(out/'export-intent.json'),'checkpoint_sha256':freeze['winner']['sha256'],
        'model_sha256':sha(out/'phoneme.fp32.onnx'),'model_bytes':(out/'phoneme.fp32.onnx').stat().st_size,
        'vocabulary_sha256':sha(out/'vocabulary.json'),'calibration_sha256':sha(out/'full-calibration.json'),
        'predictions_sha256':sha(out/'calibration-predictions.json'),'elapsed_seconds':time.monotonic()-started,
        'qualified_fp32_reconstruction':True,'onnx_parity_verified':False,'native_verified':False,
        'reserved_evaluation_inferred':False,'production_ready':False,'approved_for_child_scoring':False}
    write(out/'fp32-export-complete.json',complete);print(json.dumps({'stage':'fp32_export_complete',**complete}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--training',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();main(args.training,args.output)
