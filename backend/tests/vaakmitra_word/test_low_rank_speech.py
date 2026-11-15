"""DEC075/PHN016: train only the declared acoustic adapters and head."""
import torch
from torch import nn
import pytest
from app.vaakmitra_word.low_rank_speech import FrozenLowRankLinear,install_tail_adapters

def test_phn016_zero_update_is_exact_identity_and_base_stays_frozen():
    torch.manual_seed(4);base=nn.Linear(5,4);values=torch.randn(2,3,5)
    expected=base(values).detach();wrapped=FrozenLowRankLinear(base,rank=2,alpha=4)
    torch.testing.assert_close(wrapped(values),expected,rtol=0,atol=0)
    wrapped(values).sum().backward();assert base.weight.grad is None and wrapped.right.grad is not None

def test_phn016_merged_weight_matches_low_rank_path():
    wrapped=FrozenLowRankLinear(nn.Linear(5,4),rank=2,alpha=4)
    with torch.no_grad():wrapped.right.normal_(0,.1)
    values=torch.randn(3,5)
    expected=torch.nn.functional.linear(values,wrapped.merged_weight(),wrapped.base.bias)
    torch.testing.assert_close(wrapped(values),expected,rtol=1e-5,atol=1e-6)

def test_phn016_install_trains_only_query_value_adapters_and_head():
    class Layer(nn.Module):
        def __init__(self):
            super().__init__();self.attention=nn.Module();self.attention.q_proj=nn.Linear(5,5);self.attention.v_proj=nn.Linear(5,5);self.other=nn.Linear(5,5)
    tail=nn.Module();tail.layers=nn.ModuleList([Layer(),Layer()]);tail.head=nn.Linear(5,4)
    install_tail_adapters(tail,rank=2,alpha=4)
    names={n for n,p in tail.named_parameters() if p.requires_grad}
    assert names=={'layers.0.attention.q_proj.left','layers.0.attention.q_proj.right','layers.0.attention.v_proj.left','layers.0.attention.v_proj.right','layers.1.attention.q_proj.left','layers.1.attention.q_proj.right','layers.1.attention.v_proj.left','layers.1.attention.v_proj.right','head.weight','head.bias'}
    with pytest.raises(ValueError):install_tail_adapters(tail,rank=2,alpha=4)
