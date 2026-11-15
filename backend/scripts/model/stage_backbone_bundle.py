"""DEC068: stage a calibration-qualified internal Android bundle without copying its model."""
import argparse,os,shutil
from pathlib import Path
from scripts.model.cache_phoneme_backbone import ROOT,read,write,sha
from scripts.model.evaluate_phoneme_backbone import validate_qualification
from app.vaakmitra_word.backbone_storage import storage_guard
from app.vaakmitra_word.backbone_runtime import DECODER


def main(quantized,verification,out,fixtures,precision='int8'):
    storage_guard(ROOT,max_output_gib=11.)
    complete=read(verification/'verification-complete.json')
    if precision=='fp32':
        from scripts.model.prepare_fp32_backbone import validate_fp32
        validate_fp32(read(verification/'fp32-calibration.json'),read(verification/'fp32-parity.json'))
        calibration_file,key,artifact_complete,model_file='fp32-calibration.json','fp32_calibration_sha256','fp32-export-complete.json','phoneme.fp32.onnx'
        if complete.get('precision')!='FP32' or complete.get('qualified_for_native_validation')is not True:raise ValueError('FP32 qualification differs')
    else:
        validate_qualification(complete,read(verification/'int8-calibration.json'))
        calibration_file,key,artifact_complete,model_file='int8-calibration.json','int8_calibration_sha256','quantization-complete.json','phoneme.int8.onnx'
    if sha(verification/calibration_file)!=complete[key]:
        raise ValueError('Calibration evidence changed')
    q=read(quantized/artifact_complete)
    if q['model_sha256']!=complete['model_sha256']or sha(quantized/model_file)!=q['model_sha256']:
        raise ValueError('Candidate identity differs')
    if sha(quantized/'vocabulary.json')!=q['vocabulary_sha256']:raise ValueError('Vocabulary changed')
    if sha(verification/'native-fixtures/manifest.json')!=complete['native_fixtures_sha256']:raise ValueError('Fixtures changed')
    if out.exists()or fixtures.exists():raise FileExistsError('Use a fresh declared staging location')
    out.mkdir(parents=True)
    if precision=='int8':os.link(quantized/model_file,out/model_file)
    shutil.copyfile(quantized/'vocabulary.json',out/'vocabulary.json')
    header=dict(bundle_version='phoneme-ta-backbone-v1',artifact_revision='DEC068-tail2-all25-s919-epoch8-'+precision,
        model_kind='wav2vec2_ctc',model_file=model_file,model_sha256=q['model_sha256'],model_bytes=q['model_bytes'],
        vocabulary_file='vocabulary.json',vocabulary_sha256=q['vocabulary_sha256'],tokens=39,sample_rate=16000,
        min_input_samples=400,max_input_samples=48000,max_output_frames=149,frame_shift_ms=20,
        preprocessing='wav2vec2_mean_variance_eps1e-7_dynamic',input_mask='contiguous_ones',decoder=DECODER,
        engineering_qualified_for_preview=True,native_verified=False,production_ready=False,approved_for_child_scoring=False,
        checkpoint_sha256=complete['checkpoint_sha256'],verification_complete_sha256=sha(verification/'verification-complete.json'))
    if precision=='fp32':header.update(model_delivery='authenticated_app_private_cache',review_install_requires_model_provisioning=True)
    write(out/'bundle.json',header)
    (out/'MODEL_CARD.txt').write_text(
        'Internal adult-public-data engineering preview. No child scoring or clinical validation.\n'
        'Speech31/XLS-R-tamil-phoneme revision0dd27bfcba3a8bbe12103f1998eea2123e948369; source license not declared.\n'
        'Public release approval is pending. Upstream pretraining/test overlap not verified.\n'
        'Two tail blocks adapted on public training audio only. Dynamic16kHz400..48000samples.\n'
        'Unconstrained CTC prefix beam5/top8; no expected-word conditioning.\n'
        'Preserve gemination, vowel length, affricates and unknown evidence.\n'
        'Error patterns are uncertain sequence hypotheses; all official outcomes remain UNSCORABLE.\n',encoding='utf8')
    shutil.copytree(verification/'native-fixtures',fixtures)
    for case in read(fixtures/'manifest.json')['cases']:
        if sha(fixtures/case['file'])!=case['sha256']:raise ValueError('Fixture copy differs')
    if precision=='int8'and sha(out/model_file)!=header['model_sha256']:raise ValueError('Hardlink readback differs')
    storage_guard(ROOT,max_output_gib=11.)
    write(out/'staging-proof.json',dict(model_sha256=header['model_sha256'],bundle_sha256=sha(out/'bundle.json'),
        fixtures_manifest_sha256=sha(fixtures/'manifest.json'),native_verified=False,main_app_uses_candidate=False,
        model_storage='authenticated app-private cache provisioned once by USB'if precision=='fp32'else'same-volume hardlink to preserve E reserve'))
    print(dict(stage='staged_for_native_validation',model_sha256=header['model_sha256'],native_verified=False),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in('artifact','verification','output','fixtures'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--precision',choices=('int8','fp32'),default='int8')
    a=p.parse_args();main(a.artifact,a.verification,a.output,a.fixtures,a.precision)
