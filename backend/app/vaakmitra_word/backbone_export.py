"""DEC068/PHN008: full model reconstruction and target-free ONNX boundary."""
import copy
import os
from pathlib import Path
import torch
from torch import nn


def install_tail(full_model, tail):
    """Caller must authenticate both artifacts before invoking this pure splice."""
    encoder=full_model.wav2vec2.encoder
    count=len(tail.layers)
    if not full_model.config.do_stable_layer_norm or not 0<count<len(encoder.layers):
        raise ValueError('Unsupported full/tail architecture')
    destination=list(encoder.layers[-count:])
    # Validate every tensor key/shape before changing the owned full model.
    for expected,source in zip(destination,tail.layers):
        shapes={k:tuple(v.shape)for k,v in expected.state_dict().items()}
        if shapes!={k:tuple(v.shape)for k,v in source.state_dict().items()}:
            raise ValueError('Tail block shape differs')
    for expected,source in ((encoder.layer_norm,tail.norm),(full_model.lm_head,tail.head)):
        if {k:tuple(v.shape)for k,v in expected.state_dict().items()}!={k:tuple(v.shape)for k,v in source.state_dict().items()}:
            raise ValueError('Tail head/normalization shape differs')
    # HF can keep an unused spec-mask parameter on CPU during CUDA construction.
    active=next(encoder.layers[-count].parameters())
    device=active.device;dtype=active.dtype
    encoder.layers=nn.ModuleList(list(encoder.layers[:-count])+[copy.deepcopy(layer).to(device=device,dtype=dtype)for layer in tail.layers])
    encoder.layer_norm=copy.deepcopy(tail.norm).to(device=device,dtype=dtype)
    full_model.lm_head=copy.deepcopy(tail.head).to(device=device,dtype=dtype)
    full_model.dropout=copy.deepcopy(tail.dropout)
    return full_model.eval().requires_grad_(False)


class BackboneOnnx(nn.Module):
    """Acoustic-only inputs; output blank0 with the other native units unchanged."""
    def __init__(self, full_model):
        super().__init__();self.model=full_model.eval().requires_grad_(False)
        blank=full_model.config.pad_token_id;size=full_model.config.vocab_size
        if type(blank)is not int or not 0<=blank<size:raise ValueError('Invalid native blank')
        device=next(full_model.lm_head.parameters()).device
        self.register_buffer('order',torch.tensor([blank]+[i for i in range(size)if i!=blank],dtype=torch.long,device=device))

    def forward(self, waveform, attention_mask):
        return self.model(waveform,attention_mask=attention_mask).logits.index_select(-1,self.order)


def export_backbone_graph(full_model, path, *, max_samples=48000):
    """PHN008/3.3.55: atomic single-file dynamic graph; caller binds the sources."""
    path=Path(path);partial=path.with_name(path.name+'.partial')
    if path.exists() or partial.exists():raise FileExistsError('Export artifacts are immutable')
    if type(max_samples)is not int or not 400<=max_samples<=48000:raise ValueError('Invalid export sample bound')
    device=next(full_model.wav2vec2.feature_extractor.parameters()).device
    waveform=torch.linspace(-1.,1.,max_samples,device=device,dtype=torch.float32)[None,:]
    mask=torch.ones((1,max_samples),device=device,dtype=torch.long)
    wrapper=BackboneOnnx(full_model).eval()
    with torch.inference_mode():
        torch.onnx.export(wrapper,(waveform,mask),str(partial),export_params=True,opset_version=17,
            do_constant_folding=True,input_names=['waveform','attention_mask'],output_names=['logits'],
            dynamic_axes={'waveform':{1:'samples'},'attention_mask':{1:'samples'},'logits':{1:'frames'}},
            dynamo=False,external_data=False)
    with partial.open('r+b')as stream:os.fsync(stream.fileno())
    partial.replace(path)
