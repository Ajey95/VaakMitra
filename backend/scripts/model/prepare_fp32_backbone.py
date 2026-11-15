"""DEC068: qualify the unchanged FP32 export and create public PCM native fixtures."""
import argparse,shutil,time,wave
from pathlib import Path
import numpy as np
from app.vaakmitra_word.backbone_runtime import OnnxPhonemeRuntime,DECODER
from app.vaakmitra_word.backbone_storage import storage_guard
from app.vaakmitra_word.live_anchor import eligible_anchor
from scripts.model.cache_phoneme_backbone import ROOT,BASE,DATA,BANK,read,write,sha,waveform
from scripts.model.export_phoneme_backbone import authenticate
from scripts.model.train_phoneme_backbone import BASELINE,TEMPO_BASELINE


def validate_fp32(cal,parity):
    cases=parity.get('cases',[])
    if cal.get('eligible')is not True or cal.get('records')!=1945:raise ValueError('Full FP32 calibration failed')
    if parity.get('all_match')is not True or len(cases)!=53 or any(r.get('decoded_match')is not True for r in cases):
        raise ValueError('Exact53 FP32 graph parity failed')
    identities=[(r.get('kind'),r.get('source_row'))for r in cases]
    if any(type(i)is not int or kind not in('calibration','calibration_tempo')for kind,i in identities)or len(set(identities))!=53:
        raise ValueError('Parity identities must be53 unique calibration cases')


def fixture_identities(rows,bank,predictions,practice):
    lookup={(r['kind'],r['source_row']):r for r in predictions}
    if len(lookup)!=len(predictions):raise ValueError('Duplicate calibration predictions')
    source={('calibration',i):r for i,r in enumerate(rows)if r['split']=='calibration'}
    source.update({('calibration_tempo',i):r for i,r in enumerate(bank)if r['split']=='calibration'})
    if set(source)!=set(lookup):raise ValueError('Calibration prediction identity inventory differs')
    valid=lambda k:lookup[k]['samples']>=400
    selected=[]
    for word in sorted(practice):
        keys=[k for k,r in source.items()if k[0]=='calibration'and r.get('practice_id')==word and valid(k)]
        if not keys:raise ValueError('Practice calibration fixture missing')
        selected.append(min(keys,key=lambda k:(source[k]['audio_sha256'],k[1])))
    broad=[k for k,r in source.items()if k[0]=='calibration'and r.get('practice_id')not in practice and valid(k)]
    selected+=sorted(broad,key=lambda k:(source[k]['audio_sha256'],k[1]))[:10]
    selected+=sorted([k for k in source if k[0]=='calibration_tempo'and valid(k)],key=lambda k:(source[k]['audio_sha256'],k[1]))[:18]
    if len(selected)!=53 or len(set(selected))!=53:raise ValueError('Unique25+10+18 fixture inventory differs')
    return [dict(kind=k[0],source_row=k[1],audio_sha256=source[k]['audio_sha256'],source_split='calibration')for k in selected]


def main(training,export,parity_root,out):
    storage_guard(ROOT,max_output_gib=11.);authenticate(training)
    complete=read(export/'fp32-export-complete.json');export_intent=read(export/'export-intent.json')
    for filename,key in (('phoneme.fp32.onnx','model_sha256'),('vocabulary.json','vocabulary_sha256'),
            ('full-calibration.json','calibration_sha256'),('calibration-predictions.json','predictions_sha256'),('export-intent.json','export_intent_sha256')):
        if sha(export/filename)!=complete[key]:raise ValueError('FP32 export identity changed')
    if export_intent['training_intent_sha256']!=sha(training/'training-intent.json'):raise ValueError('Training ancestor changed')
    for p,h in export_intent['sources'].items():
        if sha(p)!=h:raise ValueError('FP32 producer changed')
    previous=read(parity_root/'verification-intent.json')
    if previous['fp32_complete_sha256']!=sha(export/'fp32-export-complete.json'):raise ValueError('Parity used a different FP32 export')
    # Authenticate historical source snapshots; the current runtime is bound and replayed below.
    for i,(p,h)in enumerate(previous['sources'].items()):
        if sha(parity_root/'sources'/f'{i:02}-{Path(p).name}')!=h:raise ValueError('Historical parity source snapshot changed')
    cal=read(export/'full-calibration.json');parity=read(parity_root/'fp32-parity.json')
    summary=dict(eligible=eligible_anchor(cal['calibration'],read(BASELINE),cal['tempo'],read(TEMPO_BASELINE)),
        records=cal['calibration']['all']['records']+cal['tempo']['all']['records'],
        calibration=cal['calibration'],tempo=cal['tempo'],precision='FP32_full_reconstructed',
        full_calibration_engine='PyTorch CUDA FP32',onnx_exact_parity_cases=53,onnx_all1945_agreement_not_measured=True,
        public_cache_preprocessing='nonzero_edge_trim_of_centered_cache',exact_source_wav_sample_lengths=False)
    validate_fp32(summary,parity)
    data=read(DATA/'focus-data.json')['rows'];bank=read(BANK/'manifest.json')['records']
    predictions=read(export/'calibration-predictions.json')
    from scripts.model.train_phoneme_backbone import PRACTICE
    selected=fixture_identities(data,bank,predictions,read(PRACTICE)['expected'])
    if selected!=read(parity_root/'fixture-selection.json')or [(r['kind'],r['source_row'])for r in selected]!=[(r['kind'],r['source_row'])for r in parity['cases']]:
        raise ValueError('Declared fixture inventory changed')
    out.mkdir(parents=True,exist_ok=False);(out/'sources').mkdir()
    import app.vaakmitra_word.backbone_runtime as runtime_source
    import app.vaakmitra_word.phoneme_decoder as decoder_source
    import app.vaakmitra_word.phonetic_support as support_source
    source_paths=[Path(__file__)]+[Path(m.__file__)for m in(runtime_source,decoder_source,support_source)]
    intent=dict(protocol='unchanged FP32 graph:1945Torch calibration +53exactONNX/Torch parity',precision='FP32',
        fp32_complete_sha256=sha(export/'fp32-export-complete.json'),previous_verification_intent_sha256=sha(parity_root/'verification-intent.json'),
        original_fp32_parity_sha256=sha(parity_root/'fp32-parity.json'),fixture_selection_sha256=sha(parity_root/'fixture-selection.json'),
        sources={str(p):sha(p)for p in source_paths},decoder=DECODER,private_child_audio_used=False,reserved_evaluation_inferred=False)
    write(out/'verification-intent.json',intent);write(out/'fp32-calibration.json',summary)
    for i,p in enumerate(source_paths):shutil.copyfile(p,out/'sources'/f'{i:02}-{p.name}')
    base=np.load(BASE/'audio.npy',mmap_mode='r');extra=np.load(DATA/'extra-audio.npy',mmap_mode='r');tempo=np.load(BANK/'audio.npy',mmap_mode='r')
    fixture_root=out/'native-fixtures';fixture_root.mkdir();fixtures=[];latencies=[];started=time.monotonic()
    tokens=read(export/'vocabulary.json')['tokens'];expected={(r['kind'],r['source_row']):r['phones']for r in predictions};replayed=[]
    with OnnxPhonemeRuntime(export/'phoneme.fp32.onnx',tokens,expected_sha256=complete['model_sha256'])as runtime:
        for ordinal,item in enumerate(selected):
            i=item['source_row'];kind=item['kind'];row=bank[i]if kind=='calibration_tempo'else data[i]
            if kind!='calibration_tempo'and row['split']!='calibration':raise ValueError('Noncalibration fixture')
            if row['audio_sha256']!=item['audio_sha256']:raise ValueError('Fixture source changed')
            fixed=tempo[i]if kind=='calibration_tempo'else(base if row['cache_shard']=='base'else extra)[row['cache_index']]
            active=waveform(np.asarray(fixed,dtype=np.float32))
            same=list(runtime.infer(active).phones)==expected[kind,i]
            replayed.append(dict(kind=kind,source_row=i,decoded_match=same))
            if not same:raise RuntimeError('Current FP32 runtime differs from committed Torch calibration prediction')
            pcm=np.clip(np.rint(active*32768),-32768,32767).astype('<i2')
            tick=time.monotonic();observation=runtime.infer(pcm.astype(np.float32)/32768.);latencies.append((time.monotonic()-tick)*1000)
            filename=f'calibration-{ordinal:02}.wav';path=fixture_root/filename
            with wave.open(str(path),'wb')as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(pcm.tobytes())
            fixtures.append(dict(file=filename,sha256=sha(path),kind=kind,source_row=i,source_split='calibration',
                source_audio_sha256=row['audio_sha256'],samples=len(pcm),valid_frames=observation.valid_frames,
                expected_prediction=list(observation.phones),reference_expert_approved=False))
    write(fixture_root/'manifest.json',dict(model_sha256=complete['model_sha256'],vocabulary_sha256=complete['vocabulary_sha256'],
        decoder=DECODER,cases=fixtures,calibration_only=True,prediction_is_not_reference_truth=True))
    current_parity=dict(all_match=all(r['decoded_match']for r in replayed),cases=replayed)
    validate_fp32(summary,current_parity);write(out/'fp32-parity.json',current_parity)
    result=dict(intent_sha256=sha(out/'verification-intent.json'),fp32_calibration_sha256=sha(out/'fp32-calibration.json'),
        fp32_parity_sha256=sha(out/'fp32-parity.json'),native_fixtures_sha256=sha(fixture_root/'manifest.json'),
        model_sha256=complete['model_sha256'],model_file='phoneme.fp32.onnx',model_bytes=complete['model_bytes'],
        vocabulary_sha256=complete['vocabulary_sha256'],checkpoint_sha256=complete['checkpoint_sha256'],precision='FP32',
        qualified_for_native_validation=True,native_verified=False,private_child_audio_used=False,reserved_evaluation_inferred=False,
        production_ready=False,approved_for_child_scoring=False,laptop_fixture_inference_ms_p50=float(np.median(latencies)),
        laptop_fixture_inference_ms_p95=float(np.percentile(latencies,95)),elapsed_seconds=time.monotonic()-started)
    storage_guard(ROOT,max_output_gib=11.);write(out/'verification-complete.json',result);print(result,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in('training','export','parity','output'):p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args();main(a.training,a.export,a.parity,a.output)
