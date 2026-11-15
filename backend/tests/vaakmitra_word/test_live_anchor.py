"""DEC067/PHN007: clean preservation and immutable nonregression acceptance."""
import copy
import pytest
import torch
from app.vaakmitra_word.live_anchor import clean_anchor_loss,eligible_anchor,select_training_targets

def group(edits):return dict(records=10,phones=100,edits=edits)
def values():
 base=dict(all=group(55),old19=group(5),new6=group(25),focus18=group(20))
 cand=dict(all=group(55),old19=group(5),new6=group(24),focus18=group(19))
 return cand,base,dict(all=group(80),amma=group(10)),dict(all=group(90),amma=group(10))

def test_identity_is_zero_and_teacher_never_receives_gradients():
 teacher=torch.randn(2,5,7,requires_grad=True);student=teacher.detach().clone().requires_grad_()
 loss=clean_anchor_loss(student,teacher);assert abs(float(loss))<1e-6
 (loss+student.sum()*0).backward();assert teacher.grad is None
 changed=(teacher.detach()+torch.randn_like(teacher)*.2).requires_grad_();assert clean_anchor_loss(changed,teacher)>0

def test_anchor_averages_frames_and_rejects_invalid_logits():
 a=torch.randn(2,3,7);b=torch.randn(2,3,7)
 assert torch.allclose(clean_anchor_loss(a,b),clean_anchor_loss(a.repeat(1,2,1),b.repeat(1,2,1)))
 with pytest.raises(ValueError):clean_anchor_loss(a,b[:,:2])
 with pytest.raises(ValueError):clean_anchor_loss(a*float('nan'),b)

def test_only_joint_clean_and_tempo_improvement_qualifies():
 c,b,t,bt=values();assert eligible_anchor(c,b,t,bt)
 assert not eligible_anchor(b,b,t,bt)
 assert not eligible_anchor(c,b,bt,bt)

@pytest.mark.parametrize('key',['all','old19','new6'])
def test_any_protected_group_regression_is_rejected(key):
 c,b,t,bt=values();c[key]['edits']=b[key]['edits']+1;assert not eligible_anchor(c,b,t,bt)

def test_denominator_and_empty_group_changes_are_rejected():
 c,b,t,bt=values();c['focus18']['phones']=101;assert not eligible_anchor(c,b,t,bt)
 c,b,t,bt=values();c['old19']['records']=0;assert not eligible_anchor(c,b,t,bt)
 c,b,t,bt=values();t['amma']['edits']=11;assert not eligible_anchor(c,b,t,bt)

def test_sparse_tempo_labels_follow_the_real_padded_batch_contract():
 targets=torch.tensor([[1,2,3],[4,5,0],[6,0,0]]);lengths=torch.tensor([3,2,1])
 chosen,n=select_training_targets(targets,lengths,torch.tensor([2,0]))
 assert chosen.tolist()==[[6,0,0],[1,2,3]] and n.tolist()==[1,3]
 with pytest.raises(ValueError):select_training_targets(targets,lengths,torch.tensor([3]))
