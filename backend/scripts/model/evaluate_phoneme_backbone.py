"""DEC068: one frozen exposed-test comparison; never checkpoint/precision selection."""
from __future__ import annotations
import argparse,gc,math,time
from pathlib import Path
import numpy as np
import onnxruntime as ort
from app.vaakmitra_word.backbone_runtime import OnnxPhonemeRuntime,DECODER
from app.vaakmitra_word.backbone_storage import storage_guard
from app.vaakmitra_word.focused_finalization import freeze_operation,claim_evaluation,operation_lease
from app.vaakmitra_word.focused_words import metrics,eligible
from app.vaakmitra_word.phoneme_decoder import decode_logits
from scripts.model.cache_phoneme_backbone import ROOT,BASE,DATA,read,write,sha,waveform
from scripts.model.export_phoneme_backbone import authenticate


def validate_export_lineage(export_intent,training_sha,selection_sha,winner_sha):
    expected=dict(training_intent_sha256=training_sha,selection_freeze_sha256=selection_sha,checkpoint_sha256=winner_sha)
    if any(export_intent.get(k)!=v for k,v in expected.items()):raise ValueError('Export is not the authenticated training selection')


def cohort_claim_root(workspace,identity):
    digest=identity['data_sha256']
    if not isinstance(digest,str)or len(digest)!=64 or any(c not in'0123456789abcdef'for c in digest):raise ValueError('Invalid cohort identity')
    root=Path(workspace)/'evaluation-claims'/digest;root.mkdir(parents=True,exist_ok=True)
    return root


def claim_scientific_evaluation(workspace,identity,report):
    canonical=cohort_claim_root(workspace,identity)
    # Recognize any earlier ticket in this DEC068 workspace, including the old output-local layout.
    for top in Path(workspace).iterdir():
        if top.name in('models','deps','tmp','evaluation-claims')or not top.is_dir():continue
        for ticket in top.rglob('evaluation-ticket.json'):
            stored=read(ticket)
            if stored.get('data_sha256')==identity['data_sha256']:raise ValueError('Historical cohort ticket already exists')
    freeze_operation(canonical,identity)
    return claim_evaluation(canonical,dict(identity,report_output=str(Path(report).resolve())))


def validate_qualification(complete,report):
    wanted=dict(qualified_for_native_validation=True,production_ready=False,
        approved_for_child_scoring=False,private_child_audio_used=False,reserved_evaluation_inferred=False)
    if any(complete.get(k)is not v for k,v in wanted.items()):raise ValueError('Precision has not qualified')
    agreement=report.get('decoded_agreement')
    if report.get('eligible')is not True or report.get('records')!=1945 or type(agreement)not in(int,float)or not math.isfinite(agreement)or not .95<=agreement<=1:
        raise ValueError('Full calibration qualification/agreement failed')


def main(training,quantized,verification,out,precision='fp32',fp32_export=None):
    storage_guard(ROOT,max_output_gib=11.)
    _,selection,_,origin=authenticate(training)
    completion=read(verification/'verification-complete.json')
    if precision=='fp32':
        from scripts.model.prepare_fp32_backbone import validate_fp32
        cal=read(verification/'fp32-calibration.json');validate_fp32(cal,read(verification/'fp32-parity.json'))
        if completion.get('precision')!='FP32' or any(completion.get(k)is not v for k,v in dict(
            qualified_for_native_validation=True,production_ready=False,approved_for_child_scoring=False,
            private_child_audio_used=False,reserved_evaluation_inferred=False).items()):raise ValueError('FP32 qualification origin differs')
        calibration_file,calibration_key='fp32-calibration.json','fp32_calibration_sha256'
        artifact_complete,ancestor_key,model_file='fp32-export-complete.json','fp32_complete_sha256','phoneme.fp32.onnx'
    else:
        cal=read(verification/'int8-calibration.json');validate_qualification(completion,cal)
        calibration_file,calibration_key='int8-calibration.json','int8_calibration_sha256'
        artifact_complete,ancestor_key,model_file='quantization-complete.json','quantized_complete_sha256','phoneme.int8.onnx'
    for name,key in ((calibration_file,calibration_key),('fp32-parity.json','fp32_parity_sha256'),('verification-intent.json','intent_sha256')):
        if sha(verification/name)!=completion[key]:raise ValueError('Qualification evidence changed')
    intent=read(verification/'verification-intent.json')
    for p,h in intent['sources'].items():
        if sha(p)!=h:raise ValueError('Verified inference source changed')
    q=read(quantized/artifact_complete)
    if sha(quantized/artifact_complete)!=intent[ancestor_key]:raise ValueError('Precision ancestor changed')
    if q['model_sha256']!=completion['model_sha256']or sha(quantized/model_file)!=q['model_sha256']:raise ValueError('Selected precision changed')
    if sha(quantized/'vocabulary.json')!=q['vocabulary_sha256']:raise ValueError('Selected units changed')
    parent_export=quantized if precision=='fp32'else fp32_export
    if parent_export is None:raise ValueError('INT8 evaluation requires its authenticated --export parent')
    parent_intent=read(parent_export/'export-intent.json');parent_complete=read(parent_export/'fp32-export-complete.json')
    if sha(parent_export/'export-intent.json')!=parent_complete['export_intent_sha256']:raise ValueError('Export intent changed')
    if precision=='int8'and read(quantized/'quantization-intent.json')['fp32_complete_sha256']!=sha(parent_export/'fp32-export-complete.json'):
        raise ValueError('Quantization parent differs')
    validate_export_lineage(parent_intent,sha(training/'training-intent.json'),sha(training/'selection-freeze.json'),selection['winner']['sha256'])
    if parent_complete['checkpoint_sha256']!=selection['winner']['sha256']:raise ValueError('Export checkpoint differs')
    old=read(BASE/'bundle/bundle.json');old_vocab=read(BASE/'bundle/vocabulary.json')['tokens']
    old_model=BASE/'bundle'/old['model_file']
    if sha(old_model)!=old['model_sha256']or sha(BASE/'bundle/vocabulary.json')!=old['vocabulary_sha256']or old['decoder']!=DECODER:
        raise ValueError('Retained baseline identity changed')
    paths=[Path(__file__)]+[Path(p)for p in intent['sources']]
    import app.vaakmitra_word.focused_words as metric_module
    import app.vaakmitra_word.focused_finalization as final_module
    paths+=[Path(metric_module.__file__),Path(final_module.__file__)]
    frozen=dict(model_sha256=q['model_sha256'],model_file=model_file,precision=precision,vocabulary_sha256=q['vocabulary_sha256'],
        verification_complete_sha256=sha(verification/'verification-complete.json'),selection_sha256=sha(training/'selection-freeze.json'),
        baseline_model_sha256=old['model_sha256'],baseline_vocabulary_sha256=old['vocabulary_sha256'],data_sha256=origin['data_sha256'],decoder=DECODER,
        preprocessing='actual400..48000_mean_variance_eps1e-7_contiguous_ones',
        public_cache_preprocessing='nonzero_edge_trim_of_centered_cache; source WAV edge zeros not retained',
        exact_source_wav_sample_lengths=False,
        sources={str(p):sha(p)for p in paths},test_cap=.5929667,
        no_reselection=True,private_child_audio_used=False,
        historical_evaluation_previously_exposed=True,upstream_pretraining_overlap_not_verified=True)
    out.mkdir(parents=True,exist_ok=True)
    with operation_lease(cohort_claim_root(ROOT,frozen)):
        result=out/'evaluation-results.json'
        if result.exists():
            stored=read(result)
            if stored['freeze']!=frozen:raise ValueError('Stored comparison binding changed')
            print('Existing bound comparison retained; no inference repeated',flush=True);return
        if not claim_scientific_evaluation(ROOT,frozen,out):raise RuntimeError('Previous evaluation claimed; do not repeat interrupted exposed-test inference')
        freeze_operation(out,frozen)
        # The immutable model/precision/source freeze and exclusive claim precede all test inference.
        rows=[r for r in read(DATA/'focus-data.json')['rows']if r['split']=='evaluation']
        if len(rows)!=1665:raise ValueError('Evaluation denominator changed')
        base=np.load(BASE/'audio.npy',mmap_mode='r');extra=np.load(DATA/'extra-audio.npy',mmap_mode='r')
        vocab=read(quantized/'vocabulary.json')['tokens'];lookup={p:i for i,p in enumerate(old_vocab)}
        predicted=[];started=time.monotonic()
        with OnnxPhonemeRuntime(quantized/model_file,vocab,expected_sha256=q['model_sha256'])as runtime:
            for i,row in enumerate(rows):
                audio=np.asarray((base if row['cache_shard']=='base'else extra)[row['cache_index']],dtype=np.float32)
                active=waveform(audio)
                phones=runtime.infer(active).phones if len(active)>=400 else ()
                predicted.append([lookup.get(p,len(old_vocab))for p in phones])
                if i%100==0:
                    storage_guard(ROOT,max_output_gib=11.);print(dict(stage='frozen_candidate_evaluation',done=i+1,total=len(rows)),flush=True)
        gc.collect();baseline=[]
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        options.add_session_config_entry('session.intra_op.allow_spinning','0')
        session=ort.InferenceSession(str(old_model),options,providers=['CPUExecutionProvider'])
        for i,row in enumerate(rows):
            audio=np.array((base if row['cache_shard']=='base'else extra)[row['cache_index']],dtype=np.float32)[None,:]
            logits=session.run(['logits'],{'waveform':audio})[0]
            try:baseline.append(decode_logits(logits[0],DECODER))
            finally:audio.fill(0);logits.fill(0)
            if i%200==0:print(dict(stage='retained_baseline_evaluation',done=i+1,total=len(rows)),flush=True)
        del session;gc.collect()
        candidate=metrics(predicted,rows);retained=metrics(baseline,rows)
        per_word={word:metrics([p for p,r in zip(predicted,rows)if r.get('practice_id')==word],
            [r for r in rows if r.get('practice_id')==word])['all']for word in sorted({r['practice_id']for r in rows if r.get('practice_id')})}
        report=dict(freeze=frozen,candidate_evaluation=candidate,baseline_evaluation=retained,
            per_word_evaluation=per_word,evaluation_eligible=eligible(candidate,retained,.5929667),
            elapsed_seconds=time.monotonic()-started,production_ready=False,approved_for_child_scoring=False,
            references_provisional=True,child_or_clinical_performance_measured=False)
        write(result,report);print(report,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for name in('training','artifact','verification','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--precision',choices=('int8','fp32'),default='fp32');p.add_argument('--export',type=Path)
    a=p.parse_args();main(a.training,a.artifact,a.verification,a.output,a.precision,a.export)
