"""DEC075/PHN016: small trainable query/value updates over frozen acoustic layers."""
import torch
from torch import nn
from torch.nn import functional as F

class FrozenLowRankLinear(nn.Module):
    def __init__(self,base,rank=8,alpha=16):
        super().__init__()
        if not isinstance(base,nn.Linear) or not 1<=rank<=min(base.in_features,base.out_features) or alpha<=0:raise ValueError('Invalid acoustic adapter dimensions')
        self.base=base.requires_grad_(False);self.factor=float(alpha)/rank
        self.left=nn.Parameter(torch.empty(rank,base.in_features,device=base.weight.device,dtype=base.weight.dtype))
        self.right=nn.Parameter(torch.zeros(base.out_features,rank,device=base.weight.device,dtype=base.weight.dtype))
        nn.init.normal_(self.left,std=.01)
    def forward(self,values):return self.base(values)+F.linear(F.linear(values,self.left),self.right)*self.factor
    def merged_weight(self):return self.base.weight+self.factor*(self.right@self.left)

def install_tail_adapters(tail,rank=8,alpha=16):
    if not hasattr(tail,'layers') or len(tail.layers)!=2 or not isinstance(tail.head,nn.Linear):raise ValueError('Expected existing two-layer speech tail')
    projections=[]
    for layer in tail.layers:
        for name in ('q_proj','v_proj'):
            projection=getattr(layer.attention,name)
            if not isinstance(projection,nn.Linear):raise ValueError('Acoustic adapter already installed or unsupported')
            projections.append((layer.attention,name,projection))
    tail.requires_grad_(False)
    for attention,name,projection in projections:setattr(attention,name,FrozenLowRankLinear(projection,rank,alpha))
    tail.head.requires_grad_(True)
    return [name for name,p in tail.named_parameters() if p.requires_grad]
