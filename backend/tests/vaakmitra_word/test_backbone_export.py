"""DEC068/PHN008: reconstruction preserves actual supervised tail and blank semantics."""
import copy
import numpy as np
import torch
import pytest
from transformers import Wav2Vec2Config,Wav2Vec2ForCTC
from app.vaakmitra_word.phoneme_backbone import split_backbone,normalize_and_pad,feature_lengths
from app.vaakmitra_word.backbone_export import install_tail,BackboneOnnx


def tiny():
    config=Wav2Vec2Config(hidden_size=16,num_hidden_layers=4,num_attention_heads=2,intermediate_size=32,
        conv_dim=[8]*7,conv_stride=[5,2,2,2,2,2,2],conv_kernel=[10,3,3,3,3,2,2],
        num_conv_pos_embeddings=16,num_conv_pos_embedding_groups=2,feat_extract_norm='layer',
        do_stable_layer_norm=True,vocab_size=7,pad_token_id=6,hidden_dropout=0.,attention_dropout=0.,
        activation_dropout=0.,feat_proj_dropout=0.,final_dropout=0.,layerdrop=0.,mask_time_prob=0.)
    config._attn_implementation='eager'
    return Wav2Vec2ForCTC(config).eval()


def test_reconstruction_installs_independent_tail_without_changing_prefix():
    torch.manual_seed(919);full=tiny();prefix,tail=split_backbone(copy.deepcopy(full),2)
    with torch.no_grad():tail.head.weight.add_(.02);tail.layers[0].feed_forward.output_dense.bias.add_(.1)
    prefix_before={k:v.clone() for k,v in full.wav2vec2.encoder.layers[0].state_dict().items()}
    result=install_tail(full,tail)
    values,mask=normalize_and_pad([np.linspace(-.3,.3,1600,dtype=np.float32),np.linspace(-.2,.3,1200,dtype=np.float32)])
    values=torch.from_numpy(values);mask=torch.from_numpy(mask)
    with torch.no_grad():
        expected=tail(prefix(values,attention_mask=mask).last_hidden_state,feature_lengths(mask.sum(-1)))
        actual=result(values,attention_mask=mask).logits
    assert torch.allclose(actual,expected,atol=1e-5,rtol=1e-5)
    assert all(torch.equal(v,prefix_before[k])for k,v in result.wav2vec2.encoder.layers[0].state_dict().items())
    assert not any(p.requires_grad for p in result.parameters())
    assert result.lm_head.weight.data_ptr()!=tail.head.weight.data_ptr()


def test_onnx_boundary_has_only_waveform_and_mask_and_reorders_blank_once():
    full=tiny();wrapper=BackboneOnnx(full)
    values=torch.linspace(-1.,1.,1600)[None];mask=torch.ones_like(values,dtype=torch.long)
    with torch.no_grad():original=full(values,attention_mask=mask).logits;actual=wrapper(values,mask)
    assert actual.shape==original.shape
    assert torch.equal(actual[...,0],original[...,6])
    assert torch.equal(actual[...,1:],original[...,:6])


def test_real_dynamic_onnx_matches_torch_for_short_and_padded_valid_audio(tmp_path):
    """PHN008/3.3.55: dynamic frames and optional padding retain acoustic evidence."""
    import onnxruntime as ort
    from app.vaakmitra_word.backbone_export import export_backbone_graph
    model=tiny();path=tmp_path/'tiny.onnx'
    export_backbone_graph(model,path,max_samples=1600)
    options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
    session=ort.InferenceSession(str(path),options,providers=['CPUExecutionProvider'])
    wrapper=BackboneOnnx(model)
    for samples in (400,800,1200,1600):
        wave=np.linspace(-1,1,samples,dtype=np.float32)[None];mask=np.ones_like(wave,dtype=np.int64)
        with torch.no_grad():expected=wrapper(torch.from_numpy(wave),torch.from_numpy(mask)).numpy()
        actual=session.run(None,{'waveform':wave,'attention_mask':mask})[0]
        assert actual.shape==(1,int(feature_lengths(torch.tensor([samples]))[0]),7)
        assert np.allclose(actual,expected,atol=1e-4,rtol=1e-4)
    short=np.linspace(-1,1,800,dtype=np.float32)[None]
    padded=np.pad(short,((0,0),(0,800)));mask=np.pad(np.ones_like(short,dtype=np.int64),((0,0),(0,800)))
    valid=session.run(None,{'waveform':short,'attention_mask':np.ones_like(short,dtype=np.int64)})[0]
    larger=session.run(None,{'waveform':padded,'attention_mask':mask})[0]
    assert np.allclose(larger[:,:valid.shape[1]],valid,atol=1e-4,rtol=1e-4)


@pytest.mark.skipif(not torch.cuda.is_available(),reason='CUDA reconstruction required')
def test_unused_cpu_spec_mask_does_not_move_active_tail_or_export_input_to_cpu(tmp_path):
    """PHN008: HF's unused eval spec-mask can precede active CUDA parameters."""
    from app.vaakmitra_word.backbone_export import export_backbone_graph
    full=tiny().cuda()
    full.wav2vec2.masked_spec_embed=torch.nn.Parameter(torch.zeros(16,device='cpu'))
    assert next(full.parameters()).device.type=='cpu'
    prefix,tail=split_backbone(copy.deepcopy(full),2)
    install_tail(full,tail)
    values=torch.linspace(-1,1,1600,device='cuda')[None]
    mask=torch.ones_like(values,dtype=torch.long)
    with torch.no_grad():
        expected=tail(prefix(values,attention_mask=mask).last_hidden_state,feature_lengths(mask.sum(-1)))
        actual=full(values,attention_mask=mask).logits
    assert torch.allclose(actual,expected,atol=1e-5,rtol=1e-5)
    export_backbone_graph(full,tmp_path/'cuda.onnx',max_samples=1600)
