"""DEC068/PHN008: FP32 parity and complete INT8 calibration, never evaluation."""
from __future__ import annotations
import argparse,gc,json,shutil,time,wave
from pathlib import Path
import numpy as np
import onnxruntime as ort
from app.vaakmitra_word.backbone_runtime import OnnxPhonemeRuntime,DECODER
from app.vaakmitra_word.focused_words import metrics
from app.vaakmitra_word.live_anchor import eligible_anchor
from app.vaakmitra_word.backbone_storage import storage_guard
from scripts.model.export_phoneme_backbone import authenticate
from scripts.model.cache_phoneme_backbone import ROOT,BASE,DATA,BANK,read,write,sha,waveform
from scripts.model.train_phoneme_backbone import BASELINE,TEMPO_BASELINE,PRACTICE


def sources():
    import app.vaakmitra_word.backbone_runtime as runtime
    import app.vaakmitra_word.phoneme_decoder as decoder
    import app.vaakmitra_word.phonetic_support as support
    import scripts.model.export_phoneme_backbone as exporter
    return [Path(__file__)]+[Path(m.__file__)for m in(runtime,decoder,support,exporter)]


def main(training,export,quantized,out):
    storage_guard(ROOT,max_output_gib=11.);train_intent,_,_,_=authenticate(training)
    fp=read(export/'fp32-export-complete.json');fp_intent=read(export/'export-intent.json')
    q=read(quantized/'quantization-complete.json');q_intent=read(quantized/'quantization-intent.json')
    if fp_intent['training_intent_sha256']!=sha(training/'training-intent.json')or q['fp32_complete_sha256']!=sha(export/'fp32-export-complete.json'):
        raise ValueError('Artifact ancestry differs')
    for p,key,metadata in ((export/'export-intent.json','export_intent_sha256',fp),(export/'phoneme.fp32.onnx','model_sha256',fp),
            (export/'calibration-predictions.json','predictions_sha256',fp),(quantized/'quantization-intent.json','intent_sha256',q),
            (quantized/'phoneme.int8.onnx','model_sha256',q),(quantized/'vocabulary.json','vocabulary_sha256',q)):
        if sha(p)!=metadata[key]:raise ValueError('Model/evidence changed')
    for intent in (fp_intent,q_intent):
        for p,h in intent['sources'].items():
            if sha(p)!=h:raise ValueError('Production source changed')
    for p,h in q_intent['dependency_binaries'].items():
        if sha(p)!=h:raise ValueError('ORT/ONNX binary changed')
    if q_intent['private_child_audio_used']or q_intent['reserved_evaluation_inferred']:raise ValueError('Invalid quantization origin')
    vocab=read(quantized/'vocabulary.json')['tokens'];legacy=read(BASE/'bundle/vocabulary.json')['tokens'];lookup={p:i for i,p in enumerate(legacy)}
    data=read(DATA/'focus-data.json');bank=read(BANK/'manifest.json')
    base=np.load(BASE/'audio.npy',mmap_mode='r');extra=np.load(DATA/'extra-audio.npy',mmap_mode='r');tempo=np.load(BANK/'audio.npy',mmap_mode='r')
    natural=[(i,r)for i,r in enumerate(data['rows'])if r['split']=='calibration'];slowed=list(enumerate(bank['records']))
    if len(natural)!=1630 or len(slowed)!=315:raise ValueError('Calibration denominator differs')
    rows={('calibration',i):r for i,r in natural};rows.update({('calibration_tempo',i):r for i,r in slowed})
    expected=read(export/'calibration-predictions.json');predicted_by_key={(r['kind'],r['source_row']):r for r in expected}
    if len(expected)!=1945 or set(predicted_by_key)!=set(rows):raise ValueError('FP32 prediction inventory differs')
    def audio(key):
        kind,i=key;r=rows[key]
        fixed=tempo[i]if kind=='calibration_tempo'else(base if r['cache_shard']=='base'else extra)[r['cache_index']]
        return waveform(np.asarray(fixed,dtype=np.float32))
    practice=read(PRACTICE)['expected'];selected=[]
    valid=lambda k:predicted_by_key[k]['samples']>=400
    for word in sorted(practice):
        keys=[k for k,r in rows.items()if k[0]=='calibration'and r.get('practice_id')==word and valid(k)]
        if not keys:raise ValueError('Practice fixture has no valid calibration example')
        selected.append(min(keys,key=lambda k:(rows[k]['audio_sha256'],k[1])))
    broad=[k for k,r in rows.items()if k[0]=='calibration'and r.get('practice_id')not in practice and valid(k)]
    selected+=sorted(broad,key=lambda k:(rows[k]['audio_sha256'],k[1]))[:10]
    selected+=sorted([k for k in rows if k[0]=='calibration_tempo'and valid(k)],key=lambda k:(rows[k]['audio_sha256'],k[1]))[:18]
    if len(selected)!=53 or len(set(selected))!=53:raise ValueError('53fixture inventory differs')
    out.mkdir(parents=True,exist_ok=False);paths=sources();(out/'sources').mkdir()
    intent={'protocol':'DEC068 full calibration and53FP32 parity; no reserved/private inference',
        'fp32_complete_sha256':sha(export/'fp32-export-complete.json'),'quantized_complete_sha256':sha(quantized/'quantization-complete.json'),
        'training_intent_sha256':sha(training/'training-intent.json'),'sources':{str(p):sha(p)for p in paths},
        'fixture_rule':'first valid hash per25practice;10othernatural;18tempo; never prediction correctness',
        'fp32_exact_fixture_agreement_required':1.,'int8_full_calibration_agreement_required':.95,
        'eligibility_gates_unchanged':True,'ort':ort.__version__,'private_child_audio_used':False,'reserved_evaluation_inferred':False}
    write(out/'verification-intent.json',intent)
    write(out/'fixture-selection.json',[dict(kind=k[0],source_row=k[1],audio_sha256=rows[k]['audio_sha256'],source_split='calibration')for k in selected])
    for i,p in enumerate(paths):shutil.copyfile(p,out/'sources'/f'{i:02}-{p.name}')
    started=time.monotonic();fp32_results=[]
    with OnnxPhonemeRuntime(export/'phoneme.fp32.onnx',vocab,expected_sha256=fp['model_sha256'])as runtime:
        for k in selected:
            heard=list(runtime.infer(audio(k)).phones);wanted=predicted_by_key[k]['phones']
            fp32_results.append(dict(kind=k[0],source_row=k[1],decoded_match=heard==wanted))
    gc.collect();write(out/'fp32-parity.json',{'cases':fp32_results,'all_match':all(r['decoded_match']for r in fp32_results)})
    if not all(r['decoded_match']for r in fp32_results):raise RuntimeError('FP32 ONNX/Torch decoded parity failed')
    print(json.dumps({'stage':'fp32_parity_passed','cases':53,'elapsed_seconds':time.monotonic()-started}),flush=True)
    predictions={};agreements=0;total=0;all_results=[];latencies=[];fixtures=[]
    with OnnxPhonemeRuntime(quantized/'phoneme.int8.onnx',vocab,expected_sha256=q['model_sha256'])as runtime:
        for kind,group in (('calibration',natural),('calibration_tempo',slowed)):
            values=[]
            for index,(i,row)in enumerate(group):
                k=(kind,i);x=audio(k);tick=time.monotonic()
                phones=list(runtime.infer(x).phones)if len(x)>=400 else[]
                latencies.append((time.monotonic()-tick)*1000);values.append([lookup.get(p,len(legacy))for p in phones])
                same=phones==predicted_by_key[k]['phones'];agreements+=same;total+=1
                all_results.append(dict(kind=kind,source_row=i,phones=phones,torch_decoded_match=same))
                if index%100==0:
                    storage_guard(ROOT,max_output_gib=11.);print(json.dumps({'stage':'int8_calibration','kind':kind,'done':index+1,'total':len(group),
                        'elapsed_seconds':time.monotonic()-started,'decoded_agreement':agreements/total}),flush=True)
            predictions[kind]=values
        cal_rows=[r for _,r in natural];tempo_rows=[dict(r,practice_id=r['word_id'])for _,r in slowed]
        calibration=metrics(predictions['calibration'],cal_rows)
        amma=[i for i,r in enumerate(tempo_rows)if r['word_id']=='TA_WORD_0001'and r['duration_factor']in(2.,3.)]
        measured_tempo={'all':metrics(predictions['calibration_tempo'],tempo_rows)['all'],
            'amma':metrics([predictions['calibration_tempo'][i]for i in amma],[tempo_rows[i]for i in amma])['all']}
        eligible=eligible_anchor(calibration,read(BASELINE),measured_tempo,read(TEMPO_BASELINE))
        report={'calibration':calibration,'tempo':measured_tempo,'eligible':eligible,'decoded_agreement':agreements/total,
            'records':total,'elapsed_seconds':time.monotonic()-started,'laptop_inference_ms_p50':float(np.median(latencies)),
            'laptop_inference_ms_p95':float(np.percentile(latencies,95)),'private_child_audio_used':False,'reserved_evaluation_inferred':False}
        write(out/'int8-calibration.json',report);write(out/'int8-calibration-predictions.json',all_results)
        if not eligible or agreements/total<.95:raise RuntimeError('INT8 unchanged qualification/agreement gates failed')
        fixture_root=out/'native-fixtures';fixture_root.mkdir()
        for ordinal,k in enumerate(selected):
            x=audio(k);pcm=np.clip(np.rint(x*32768),-32768,32767).astype('<i2')
            roundtrip=pcm.astype(np.float32)/32768.;observation=runtime.infer(roundtrip)
            filename=f'calibration-{ordinal:02}.wav';path=fixture_root/filename
            with wave.open(str(path),'wb')as wav:
                wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(16000);wav.writeframes(pcm.tobytes())
            fixtures.append(dict(file=filename,sha256=sha(path),kind=k[0],source_row=k[1],source_split='calibration',
                source_audio_sha256=rows[k]['audio_sha256'],samples=len(pcm),valid_frames=observation.valid_frames,
                expected_prediction=list(observation.phones),reference_expert_approved=False))
        write(fixture_root/'manifest.json',{'model_sha256':q['model_sha256'],'vocabulary_sha256':q['vocabulary_sha256'],
            'decoder':DECODER,'cases':fixtures,'calibration_only':True,'prediction_is_not_reference_truth':True})
    gc.collect();storage_guard(ROOT,max_output_gib=11.)
    complete={'intent_sha256':sha(out/'verification-intent.json'),'fp32_parity_sha256':sha(out/'fp32-parity.json'),
        'int8_calibration_sha256':sha(out/'int8-calibration.json'),'native_fixtures_sha256':sha(out/'native-fixtures/manifest.json'),
        'model_sha256':q['model_sha256'],'checkpoint_sha256':fp['checkpoint_sha256'],
        'qualified_for_native_validation':True,'native_verified':False,'private_child_audio_used':False,'reserved_evaluation_inferred':False,
        'production_ready':False,'approved_for_child_scoring':False,'elapsed_seconds':time.monotonic()-started}
    write(out/'verification-complete.json',complete);print(json.dumps({'stage':'qualified_for_native_validation',**complete}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--training',type=Path,required=True);parser.add_argument('--export',type=Path,required=True)
    parser.add_argument('--quantized',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();main(args.training,args.export,args.quantized,args.output)
