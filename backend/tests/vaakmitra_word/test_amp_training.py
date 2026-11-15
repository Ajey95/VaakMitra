"""DEC068/PHN008: AMP overflow skips optimizer updates and permits a finite retry."""
import pytest
import torch
from app.vaakmitra_word.amp_training import scaled_backward_step


@pytest.mark.skipif(not torch.cuda.is_available(),reason='actual CUDA AMP required')
def test_finite_loss_scaled_gradient_overflow_never_updates_weights_or_optimizer():
    parameter=torch.nn.Parameter(torch.tensor([1.],device='cuda'))
    optimizer=torch.optim.AdamW([parameter],lr=.01)
    scaler=torch.amp.GradScaler('cuda',init_scale=65536.)
    # Finite forward2.0, but 2*65536 cannot be represented in FP16 backward.
    loss=(parameter.half()*2).float().sum()
    norm=scaled_backward_step(loss,[parameter],optimizer,scaler)
    assert norm is None
    assert parameter.item()==1.
    assert len(optimizer.state)==0
    assert scaler.get_scale()==32768.
    optimizer.zero_grad(set_to_none=True)
    assert scaled_backward_step((parameter.half()*2).float().sum(),[parameter],optimizer,scaler) is None
    optimizer.zero_grad(set_to_none=True)
    norm=scaled_backward_step((parameter.half()*2).float().sum(),[parameter],optimizer,scaler)
    assert norm is not None and torch.isfinite(norm)
    assert parameter.item()<1.
    assert optimizer.state[parameter]['step'].item()==1.


def test_nonfinite_forward_loss_is_rejected_before_backward():
    parameter=torch.nn.Parameter(torch.tensor([1.]))
    optimizer=torch.optim.AdamW([parameter],lr=.01)
    scaler=torch.amp.GradScaler('cuda',enabled=False)
    with pytest.raises(FloatingPointError):
        scaled_backward_step((parameter*float('nan')).sum(),[parameter],optimizer,scaler)
    assert parameter.grad is None and not optimizer.state
