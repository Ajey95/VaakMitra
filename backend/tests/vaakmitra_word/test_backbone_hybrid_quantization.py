"""DEC068/PHN008: preserve adapted tail/head exactly while quantizing the prefix."""
import onnx
import torch
import pytest
from transformers import Wav2Vec2Config,Wav2Vec2ForCTC
from app.vaakmitra_word.backbone_export import export_backbone_graph
from app.vaakmitra_word.backbone_hybrid_quantization import quantize_hybrid_graph


@pytest.mark.parametrize('float_prefix_layers',[0,1])
def test_hybrid_protects_trained_layers_projection_and_head_float_weights(tmp_path,float_prefix_layers):
    config=Wav2Vec2Config(hidden_size=16,num_hidden_layers=4,num_attention_heads=2,intermediate_size=32,
        conv_dim=[8]*7,conv_stride=[5,2,2,2,2,2,2],conv_kernel=[10,3,3,3,3,2,2],
        num_conv_pos_embeddings=16,num_conv_pos_embedding_groups=2,feat_extract_norm='layer',
        do_stable_layer_norm=True,vocab_size=39,pad_token_id=38,hidden_dropout=0.,attention_dropout=0.,
        activation_dropout=0.,feat_proj_dropout=0.,final_dropout=0.,layerdrop=0.,mask_time_prob=0.)
    config._attn_implementation='eager';torch.manual_seed(919)
    fp32=tmp_path/'model.onnx';hybrid=tmp_path/'hybrid.onnx'
    export_backbone_graph(Wav2Vec2ForCTC(config).eval(),fp32,max_samples=1600)
    original=onnx.load(fp32)
    def protected(name):return any(s in name for s in ('/feature_projection/','/layers.2/','/layers.3/','/lm_head/'))or(float_prefix_layers==1 and '/layers.0/'in name)
    constants={n.input[1] for n in original.graph.node if n.op_type in ('MatMul','Gemm')and protected(n.name)}
    before={t.name:(t.data_type,tuple(t.dims),t.raw_data)for t in original.graph.initializer if t.name in constants}
    assert before
    profile=quantize_hybrid_graph(fp32,hybrid,scratch_dir=tmp_path/'scratch',encoder_blocks=4,float_prefix_layers=float_prefix_layers)
    model=onnx.load(hybrid);after={t.name:(t.data_type,tuple(t.dims),t.raw_data)for t in model.graph.initializer if t.name in before}
    assert after==before
    assert any(n.op_type=='MatMulInteger'and '/layers.1/'in n.name for n in model.graph.node)
    assert not any(n.op_type=='MatMulInteger'and protected(n.name)for n in model.graph.node)
    assert profile['float_tail_layers']==[2,3]
    assert profile['reduce_range'] is False
    assert profile['float_prefix_layers']==list(range(float_prefix_layers))
