"""DEC068/PHN008: bounded-memory INT8 export retains dynamic audio/mask behavior."""
import numpy as np
import torch
import onnxruntime as ort
from transformers import Wav2Vec2Config,Wav2Vec2ForCTC
from app.vaakmitra_word.backbone_export import export_backbone_graph
from app.vaakmitra_word.backbone_quantization import quantize_backbone_graph


def test_real_int8_graph_runs_dynamic_short_audio_and_preserves_float_logits(tmp_path):
    config=Wav2Vec2Config(hidden_size=16,num_hidden_layers=4,num_attention_heads=2,intermediate_size=32,
        conv_dim=[8]*7,conv_stride=[5,2,2,2,2,2,2],conv_kernel=[10,3,3,3,3,2,2],
        num_conv_pos_embeddings=16,num_conv_pos_embedding_groups=2,feat_extract_norm='layer',
        do_stable_layer_norm=True,vocab_size=7,pad_token_id=6,hidden_dropout=0.,attention_dropout=0.,
        activation_dropout=0.,feat_proj_dropout=0.,final_dropout=0.,layerdrop=0.,mask_time_prob=0.)
    config._attn_implementation='eager';torch.manual_seed(919)
    model=Wav2Vec2ForCTC(config).eval();fp32=tmp_path/'model.onnx';int8=tmp_path/'model.int8.onnx'
    export_backbone_graph(model,fp32,max_samples=1600)
    quantize_backbone_graph(fp32,int8)
    options=ort.SessionOptions();options.intra_op_num_threads=1;options.inter_op_num_threads=1
    original=ort.InferenceSession(str(fp32),options,providers=['CPUExecutionProvider'])
    quantized=ort.InferenceSession(str(int8),options,providers=['CPUExecutionProvider'])
    for count in (400,800,1600):
        x=np.linspace(-1,1,count,dtype=np.float32)[None];mask=np.ones_like(x,dtype=np.int64)
        inputs={'waveform':x,'attention_mask':mask}
        before=original.run(None,inputs)[0];after=quantized.run(None,inputs)[0]
        assert after.shape==before.shape and np.isfinite(after).all()
        assert np.allclose(after,before,atol=.05,rtol=.05)
    assert not list(tmp_path.glob('*inferred*'))
