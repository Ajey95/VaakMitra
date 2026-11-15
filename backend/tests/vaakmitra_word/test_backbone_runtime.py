"""DEC068/PHN008..009: target-free transient inference, exact frames and safe help."""
import hashlib,json
import numpy as np
import pytest
import torch
from transformers import Wav2Vec2Config,Wav2Vec2ForCTC
from app.vaakmitra_word.backbone_export import export_backbone_graph
from app.vaakmitra_word.backbone_runtime import OnnxPhonemeRuntime,decode_native_phones,PhonemeObservation


def tokens():return ['<blank>','a','m','aː','aj','aʋ','kʂ','t͡ʃ','[UNK]','|']+[f'unit{i}'for i in range(29)]


def test_decoder_preserves_gemination_length_affricates_and_unknown_evidence():
    path=[1,1,0,2,0,2,3,4,5,6,7,8,9]
    logits=np.full((len(path),39),-30.,dtype=np.float32)
    for i,p in enumerate(path):logits[i,p]=30.
    assert decode_native_phones(logits,tokens())==('a','m','m','aː','a','j','a','ʋ','k','ʂ','t͡ʃ','[UNK]')


def test_real_runtime_has_no_word_argument_and_never_returns_a_child_score(tmp_path):
    config=Wav2Vec2Config(hidden_size=16,num_hidden_layers=4,num_attention_heads=2,intermediate_size=32,
        conv_dim=[8]*7,conv_stride=[5,2,2,2,2,2,2],conv_kernel=[10,3,3,3,3,2,2],
        num_conv_pos_embeddings=16,num_conv_pos_embedding_groups=2,feat_extract_norm='layer',
        do_stable_layer_norm=True,vocab_size=39,pad_token_id=38,hidden_dropout=0.,attention_dropout=0.,
        activation_dropout=0.,feat_proj_dropout=0.,final_dropout=0.,layerdrop=0.,mask_time_prob=0.)
    config._attn_implementation='eager';torch.manual_seed(919)
    path=tmp_path/'tiny.onnx';export_backbone_graph(Wav2Vec2ForCTC(config).eval(),path,max_samples=1600)
    digest=hashlib.sha256(path.read_bytes()).hexdigest()
    runtime=OnnxPhonemeRuntime(path,tokens(),expected_sha256=digest,engineering_qualified=False)
    wave=np.linspace(-.4,.4,1600,dtype=np.float32);original=wave.copy()
    observation=runtime.infer(wave)
    assert observation.valid_frames==4
    assert np.array_equal(wave,original)
    assert set(vars(observation))=={'phones','valid_frames','model_sha256','supported'}
    assert runtime.support(observation,['a']).decision=='UNSCORABLE'
    assert runtime.support(observation,['a']).candidate_patterns==()
    runtime.engineering_qualified=True
    known_but_uncertain=PhonemeObservation(('a','m','aː'),4,digest,True)
    help=runtime.support(known_but_uncertain,['a','m','m','aː'],capture_valid=True)
    assert help.basis=='generic_help'and help.candidate_patterns==()
    with pytest.raises(TypeError):runtime.infer(wave,target_word='Amma')
    for bad in (wave[:399],np.zeros(48001,dtype=np.float32),np.full(800,np.nan),np.zeros((800,2))):
        with pytest.raises(ValueError):runtime.infer(bad)
    with pytest.raises(ValueError):OnnxPhonemeRuntime(path,tokens(),expected_sha256='0'*64)
