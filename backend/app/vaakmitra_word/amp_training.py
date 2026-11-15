"""DEC068/PHN008: finite CUDA updates, with explicit GradScaler overflow recovery."""
import torch
from torch import nn


def scaled_backward_step(loss, parameters, optimizer, scaler, max_norm=1.):
    """Return finite norm after an update, or None after a verified skipped step.

    The caller must clear gradients and recompute the same batch after None.
    Forward NaNs and non-finite clipping norms are hard failures, never masked.
    """
    if loss.numel()!=1 or not torch.isfinite(loss):
        raise FloatingPointError('Nonfinite/scalar training loss')
    parameters=list(parameters)
    scaler.scale(loss).backward();scaler.unscale_(optimizer)
    gradients=[parameter.grad for parameter in parameters if parameter.grad is not None]
    if not gradients:raise RuntimeError('No trainable gradients')
    finite=bool(torch.stack([torch.isfinite(gradient).all()for gradient in gradients]).all())
    if not finite:
        if not scaler.is_enabled():raise FloatingPointError('Nonfinite unscaled gradients')
        previous=scaler.get_scale()
        # unscale_ already registered the Inf/NaN, so GradScaler skips optimizer.step.
        scaler.step(optimizer);scaler.update()
        if scaler.get_scale()>=previous:raise RuntimeError('AMP did not confirm a skipped overflow')
        return None
    norm=nn.utils.clip_grad_norm_(parameters,max_norm,error_if_nonfinite=True)
    scaler.step(optimizer);scaler.update()
    return norm
