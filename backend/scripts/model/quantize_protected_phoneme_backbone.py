"""DEC068/PHN008: third fixed precision control, protected first/last2 blocks."""
from __future__ import annotations
import argparse,shutil,time
from pathlib import Path
import onnx
import onnxruntime as ort
import onnxruntime.quantization as quant_package
import app.vaakmitra_word.backbone_hybrid_quantization as implementation
from app.vaakmitra_word.backbone_hybrid_quantization import PROFILE as BASE_PROFILE,quantize_hybrid_graph
PROFILE=dict(BASE_PROFILE,float_prefix_layers=[0],precision_control="protected_first_and_tail2")
from app.vaakmitra_word.backbone_storage import storage_guard
from scripts.model.quantize_phoneme_backbone import ROOT,read,write,sha

SCRATCH=Path('C:/Users/AJEYA/VaakMitraBuildTemp/phoneme-backbone-20261113/quantizer-scratch')

def main(export,out):
    if not __debug__:raise RuntimeError('Nonoptimized Python required')
    complete=read(export/'fp32-export-complete.json');origin=read(export/'export-intent.json')
    if not complete['qualified_fp32_reconstruction']or complete['reserved_evaluation_inferred']or origin['private_child_audio_used']:
        raise ValueError('Invalid FP32 origin')
    for filename,key in (('export-intent.json','export_intent_sha256'),('phoneme.fp32.onnx','model_sha256'),
            ('vocabulary.json','vocabulary_sha256'),('full-calibration.json','calibration_sha256'),('calibration-predictions.json','predictions_sha256')):
        if sha(export/filename)!=complete[key]:raise ValueError('FP32 artifact changed')
    for p,h in origin['sources'].items():
        if sha(p)!=h:raise ValueError('Export source changed')
    cpu=ROOT/'host-cpu-capabilities.json'
    if read(cpu)['avx_vnni']is not True:raise ValueError('Local full-range calibration requires verified VNNI')
    storage_guard(ROOT,max_output_gib=11.)
    if shutil.disk_usage('C:/').free<complete['model_bytes']+600*1024**2:raise OSError('C temporary inference would consume reserve')
    if shutil.disk_usage('E:/').free<2*1024**3+500*1024**2:raise OSError('Hybrid output would consume reserve')
    out.mkdir(parents=True,exist_ok=False)
    import scripts.model.quantize_phoneme_backbone as io_helpers
    paths=[Path(__file__),Path(implementation.__file__),Path(io_helpers.__file__),Path(onnx.shape_inference.__file__)]+sorted(Path(quant_package.__file__).parent.rglob('*.py'))
    binaries=list((Path(ort.__file__).parent/'capi').glob('*.pyd'))+list((Path(ort.__file__).parent/'capi').glob('*.dll'))+list(Path(onnx.__file__).parent.glob('*.pyd'))
    intent={'protocol':'DEC068 fixed hybrid precision control; accuracy/native unverified','profile':PROFILE,
        'fp32_complete_sha256':sha(export/'fp32-export-complete.json'),'source_model_sha256':complete['model_sha256'],
        'checkpoint_sha256':complete['checkpoint_sha256'],'host_cpu_proof_sha256':sha(cpu),
        'sources':{str(p):sha(p)for p in paths},'dependency_binaries':{str(p):sha(p)for p in binaries},
        'onnx':onnx.__version__,'onnxruntime':ort.__version__,'scratch_parent':str(SCRATCH),
        'calibration_agreement_minimum':.95,'original_qualification_gates_unchanged':True,
        'private_child_audio_used':False,'reserved_evaluation_inferred':False,'production_ready':False,'approved_for_child_scoring':False}
    write(out/'quantization-intent.json',intent);(out/'sources').mkdir()
    for i,p in enumerate(paths):shutil.copyfile(p,out/'sources'/f'{i:03}-{p.name}')
    started=time.monotonic();print({'stage':'hybrid_quantization_started','profile':PROFILE},flush=True)
    executed=quantize_hybrid_graph(export/'phoneme.fp32.onnx',out/'phoneme.int8.onnx',scratch_dir=SCRATCH,encoder_blocks=24,float_prefix_layers=1)
    write(out/'executed-profile.json',executed);storage_guard(ROOT,max_output_gib=11.)
    shutil.copyfile(export/'vocabulary.json',out/'vocabulary.json')
    result={'intent_sha256':sha(out/'quantization-intent.json'),'fp32_complete_sha256':intent['fp32_complete_sha256'],
        'model_sha256':sha(out/'phoneme.int8.onnx'),'model_bytes':(out/'phoneme.int8.onnx').stat().st_size,
        'vocabulary_sha256':sha(out/'vocabulary.json'),'executed_profile_sha256':sha(out/'executed-profile.json'),
        'elapsed_seconds':time.monotonic()-started,'calibration_verified':False,'native_verified':False,
        'reserved_evaluation_inferred':False,'production_ready':False,'approved_for_child_scoring':False}
    write(out/'quantization-complete.json',result);print({'stage':'hybrid_quantized_unverified',**result},flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();main(args.export,args.output)
