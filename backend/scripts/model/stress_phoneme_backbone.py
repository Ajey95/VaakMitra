"""DEC068: correlated public-calibration transforms, never synthetic children or new training."""
import argparse,time
from pathlib import Path
import numpy as np
from app.vaakmitra_word.backbone_runtime import OnnxPhonemeRuntime,DECODER
from app.vaakmitra_word.backbone_storage import storage_guard
from app.vaakmitra_word.focused_words import metrics,parent
from app.vaakmitra_word.phoneme_ctc import stress_waveform
from scripts.model.cache_phoneme_backbone import ROOT,BASE,DATA,read,write,sha,waveform
from scripts.model.train_phoneme_backbone import PRACTICE
from scripts.model.evaluate_phoneme_backbone import validate_qualification


def main(quantized,verification,out,precision='int8'):
    storage_guard(ROOT,max_output_gib=11.)
    complete=read(verification/'verification-complete.json')
    if precision=='fp32':
        from scripts.model.prepare_fp32_backbone import validate_fp32
        validate_fp32(read(verification/'fp32-calibration.json'),read(verification/'fp32-parity.json'))
        model_file,complete_file='phoneme.fp32.onnx','fp32-export-complete.json'
    else:
        validate_qualification(complete,read(verification/'int8-calibration.json'))
        model_file,complete_file='phoneme.int8.onnx','quantization-complete.json'
    q=read(quantized/complete_file);vocab=read(quantized/'vocabulary.json')['tokens']
    if sha(quantized/model_file)!=complete['model_sha256']or sha(quantized/'vocabulary.json')!=q['vocabulary_sha256']:
        raise ValueError('Qualified artifact changed')
    if out.exists():raise FileExistsError('Stress report already exists')
    practice=read(PRACTICE)['expected'];rows=[r for r in read(DATA/'focus-data.json')['rows']if r['split']=='calibration'and r.get('practice_id')in practice]
    if not rows:raise ValueError('No public practice calibration parents')
    lookup={p:i for i,p in enumerate(read(BASE/'bundle/vocabulary.json')['tokens'])}
    base=np.load(BASE/'audio.npy',mmap_mode='r');extra=np.load(DATA/'extra-audio.npy',mmap_mode='r')
    started=time.monotonic();results={};versions=('clean','noise20','noise10','echo','lowpass','quiet')
    out.mkdir(parents=True)
    import app.vaakmitra_word.phoneme_ctc as stress_source
    write(out/'stress-intent.json',dict(model_sha256=complete['model_sha256'],decoder=DECODER,versions=versions,seed=919,
        calibration_only=True,independent_samples=False,child_simulation=False,no_reselection=True,
        script_sha256=sha(__file__),transform_source_sha256=sha(stress_source.__file__),
        data_sha256=sha(DATA/'focus-data.json'),parents=[dict(audio_sha256=r['audio_sha256'],source_utterance_id=parent(r))for r in rows]))
    with OnnxPhonemeRuntime(quantized/model_file,vocab,expected_sha256=complete['model_sha256'])as runtime:
        for kind in versions:
            predicted=[]
            for i,row in enumerate(rows):
                active=waveform(np.asarray((base if row['cache_shard']=='base'else extra)[row['cache_index']],dtype=np.float32))
                value=active if kind=='clean'else stress_waveform(active,kind,919+i)
                phones=runtime.infer(value).phones if len(value)>=400 else()
                predicted.append([lookup.get(p,len(lookup))for p in phones])
            results[kind]=metrics(predicted,rows)
            storage_guard(ROOT,max_output_gib=11.);print(dict(stage='public_synthetic_robustness',kind=kind,records=len(rows)),flush=True)
    write(out/'stress-results.json',dict(intent_sha256=sha(out/'stress-intent.json'),model_sha256=complete['model_sha256'],
        source_clips=len(rows),distinct_source_utterances=len({parent(r)for r in rows}),synthetic_derivatives=5*len(rows),
        variants=results,elapsed_seconds=time.monotonic()-started,not_child_validation=True,production_ready=False,approved_for_child_scoring=False))


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in('artifact','verification','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--precision',choices=('int8','fp32'),default='int8')
    a=p.parse_args();main(a.artifact,a.verification,a.output,a.precision)
