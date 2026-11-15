"""DEC068/PHN008: source-bound INT8 artifact production; accuracy unverified here."""
from __future__ import annotations
import argparse,hashlib,json,os,shutil,time
from pathlib import Path
import onnx
import onnxruntime as ort
import onnxruntime.quantization as quant_package
import app.vaakmitra_word.backbone_quantization as implementation
from app.vaakmitra_word.backbone_quantization import PROFILE,quantize_backbone_graph
from app.vaakmitra_word.backbone_storage import storage_guard

ROOT=Path('E:/VaakMitraModelLab/20261112-phoneme-transfer')
SCRATCH=Path('D:/VaakMitraData/analysis/phoneme-backbone-20261112/quantizer-temp')

def read(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    result=hashlib.sha256()
    with Path(p).open('rb')as source:
        for block in iter(lambda:source.read(1024*1024),b''):result.update(block)
    return result.hexdigest()
def write(p,value):
    p=Path(p);temporary=p.with_suffix(p.suffix+'.tmp')
    with temporary.open('w',encoding='utf-8')as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2);stream.flush();os.fsync(stream.fileno())
    temporary.replace(p)

def main(export,out):
    if not __debug__:raise RuntimeError('Nonoptimized Python required')
    complete=read(export/'fp32-export-complete.json');origin=read(export/'export-intent.json')
    if not complete['qualified_fp32_reconstruction']or complete['reserved_evaluation_inferred']or origin['private_child_audio_used']:
        raise ValueError('Unqualified/invalid FP32 origin')
    for filename,key in (('export-intent.json','export_intent_sha256'),('phoneme.fp32.onnx','model_sha256'),
            ('vocabulary.json','vocabulary_sha256'),('full-calibration.json','calibration_sha256'),('calibration-predictions.json','predictions_sha256')):
        if sha(export/filename)!=complete[key]:raise ValueError('FP32 artifact changed')
    for p,h in origin['sources'].items():
        if sha(p)!=h:raise ValueError('Export source changed')
    storage_guard(ROOT)
    if shutil.disk_usage('D:/').free<complete['model_bytes']+300*1024**2:
        raise OSError('D temporary shape inference would consume reserve')
    if shutil.disk_usage('E:/').free<2*1024**3+400*1024**2:
        raise OSError('INT8 output would consume E reserve')
    out.mkdir(parents=True,exist_ok=False)
    paths=[Path(__file__),Path(implementation.__file__),Path(onnx.shape_inference.__file__)]+sorted(Path(quant_package.__file__).parent.rglob('*.py'))
    binaries=list((Path(ort.__file__).parent/'capi').glob('*.pyd'))+list((Path(ort.__file__).parent/'capi').glob('*.dll'))+list(Path(onnx.__file__).parent.glob('*.pyd'))
    intent={'protocol':'DEC068 fixed dynamic INT8 profile; calibration/phone verification pending','profile':PROFILE,
        'fp32_complete_sha256':sha(export/'fp32-export-complete.json'),'source_model_sha256':complete['model_sha256'],
        'checkpoint_sha256':complete['checkpoint_sha256'],'sources':{str(p):sha(p)for p in paths},
        'dependency_binaries':{str(p):sha(p)for p in binaries},'onnx':onnx.__version__,'onnxruntime':ort.__version__,
        'scratch_parent':str(SCRATCH),'scratch_policy':'one generated inferred ONNX copy; removed after load, original retained',
        'calibration_agreement_minimum':.95,'original_qualification_gates_unchanged':True,
        'private_child_audio_used':False,'reserved_evaluation_inferred':False,'production_ready':False,'approved_for_child_scoring':False}
    write(out/'quantization-intent.json',intent);(out/'sources').mkdir()
    for i,p in enumerate(paths):shutil.copyfile(p,out/'sources'/f'{i:03}-{p.name}')
    started=time.monotonic();print(json.dumps({'stage':'quantization_started','profile':PROFILE}),flush=True)
    quantize_backbone_graph(export/'phoneme.fp32.onnx',out/'phoneme.int8.onnx',scratch_dir=SCRATCH)
    storage_guard(ROOT);shutil.copyfile(export/'vocabulary.json',out/'vocabulary.json')
    result={'intent_sha256':sha(out/'quantization-intent.json'),'fp32_complete_sha256':intent['fp32_complete_sha256'],
        'model_sha256':sha(out/'phoneme.int8.onnx'),'model_bytes':(out/'phoneme.int8.onnx').stat().st_size,
        'vocabulary_sha256':sha(out/'vocabulary.json'),'elapsed_seconds':time.monotonic()-started,
        'calibration_verified':False,'native_verified':False,'reserved_evaluation_inferred':False,
        'production_ready':False,'approved_for_child_scoring':False}
    write(out/'quantization-complete.json',result);print(json.dumps({'stage':'quantized_unverified',**result}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();main(args.export,args.output)
