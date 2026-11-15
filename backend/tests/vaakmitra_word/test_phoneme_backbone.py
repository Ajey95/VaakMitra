"""DEC068/PHN008: phone inventory, true acoustic lengths and real prefix/tail parity."""
import numpy as np
import pytest
import torch
from transformers import Wav2Vec2Config,Wav2Vec2ForCTC
from app.vaakmitra_word.phoneme_backbone import (
    canonicalize_phones,normalize_and_pad,feature_lengths,map_target_ids,
    ctc_min_frames,split_backbone,decode_backbone_logits,
)

def test_compounds_expand_without_losing_affricates_geminates_or_unknowns():
    assert canonicalize_phones(['aʋ','t͡ʃ','m','m','aj','kʂ','aː','[UNK]'])==['a','ʋ','t͡ʃ','m','m','a','j','k','ʂ','aː','[UNK]']
    with pytest.raises(ValueError):canonicalize_phones('amma')

def test_normalization_precedes_right_padding_and_mask_preserves_length():
    first=np.linspace(-.4,.4,800,dtype=np.float32);second=np.linspace(-.1,.3,1200,dtype=np.float32)
    values,mask=normalize_and_pad([first,second])
    assert values.shape==mask.shape==(2,1200)
    assert mask.dtype==np.int64 and mask.sum(1).tolist()==[800,1200]
    assert np.all(mask[0,:800]==1)and np.all(mask[0,800:]==0)
    assert np.all(values[0,800:]==0)
    assert abs(float(values[0,:800].mean()))<1e-6
    assert abs(float(values[0,:800].var())-1)<1e-4

@pytest.mark.parametrize('bad',[np.zeros(399),np.zeros(48001),np.zeros((800,2)),np.full(800,np.nan)])
def test_invalid_or_truncated_audio_is_never_silently_accepted(bad):
    with pytest.raises(ValueError):normalize_and_pad([bad])

def test_actual_feature_lengths_and_repeat_ctc_requirement():
    assert feature_lengths(torch.tensor([400,16000,48000])).tolist()==[1,49,149]
    with pytest.raises(ValueError):feature_lengths(torch.tensor([399]))
    assert ctc_min_frames([1,2,2,3])==5
    assert ctc_min_frames([1,2,3])==3

def test_target_mapping_is_exact_and_unknown_targets_fail_closed():
    old=['<blank>','t͡ʃ','n̪','aː','missing'];native={'[PAD]':0,'aː':1,'n̪':2,'t͡ʃ':3}
    assert map_target_ids([1,2,3],old,native)==[3,2,1]
    with pytest.raises(ValueError):map_target_ids([4],old,native)
    with pytest.raises(ValueError):map_target_ids([0],old,native)

def test_decoder_reorders_blank_then_expands_without_target_conditioning():
    vocabulary={'a':0,'m':1,'aʋ':2,'[PAD]':3,'|':4,'t͡ʃ':5}
    path=[0,0,3,1,3,1,2,4,5]
    logits=np.full((len(path),6),-20,dtype=np.float32)
    for i,t in enumerate(path):logits[i,t]=20
    assert decode_backbone_logits(logits,vocabulary,{'type':'greedy'})==['a','m','m','a','ʋ','t͡ʃ']

def test_real_hf_prefix_tail_matches_full_model_and_has_independent_gradients():
    torch.manual_seed(919)
    config=Wav2Vec2Config(hidden_size=16,num_hidden_layers=4,num_attention_heads=2,intermediate_size=32,
        conv_dim=[8]*7,conv_stride=[5,2,2,2,2,2,2],conv_kernel=[10,3,3,3,3,2,2],
        num_conv_pos_embeddings=16,num_conv_pos_embedding_groups=2,feat_extract_norm='layer',
        do_stable_layer_norm=True,vocab_size=7,pad_token_id=6,hidden_dropout=0.,
        attention_dropout=0.,activation_dropout=0.,feat_proj_dropout=0.,final_dropout=0.,layerdrop=0.,mask_time_prob=0.)
    config._attn_implementation='eager'
    model=Wav2Vec2ForCTC(config).eval()
    values,mask=normalize_and_pad([np.linspace(-.3,.2,1600,dtype=np.float32),np.linspace(-.2,.3,1200,dtype=np.float32)])
    x=torch.from_numpy(values);attention=torch.from_numpy(mask)
    with torch.no_grad():expected=model(x,attention_mask=attention).logits
    prefix,tail=split_backbone(model,tail_blocks=2)
    tail.eval()
    with torch.no_grad():features=prefix(x,attention_mask=attention).last_hidden_state
    actual=tail(features,feature_lengths(attention.sum(-1)))
    assert torch.allclose(expected,actual,atol=1e-5,rtol=1e-5)
    assert not any(p.requires_grad for p in prefix.parameters())
    assert all(p.requires_grad for p in tail.parameters())
    actual.square().mean().backward()
    assert all(p.grad is None for p in prefix.parameters())
    assert any(p.grad is not None and torch.isfinite(p.grad).all()for p in tail.parameters())
