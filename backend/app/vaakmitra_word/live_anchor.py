"""DEC067/PHN007: clean acoustic preservation and conservative calibration selection."""
import math
import torch
import torch.nn.functional as F

def clean_anchor_loss(student,teacher,temperature=2.0):
    if student.ndim!=3 or student.shape!=teacher.shape or min(student.shape)<1 or student.shape[-1]<2:
        raise ValueError('matching nonempty batch/frame/phone logits required')
    if not math.isfinite(temperature) or not 0<temperature<=4:
        raise ValueError('invalid anchor temperature')
    if not torch.isfinite(student).all() or not torch.isfinite(teacher).all():
        raise ValueError('nonfinite anchor logits')
    # Frame averaging keeps the strength independent of the acoustic frame inventory.
    loss=F.kl_div((student.float()/temperature).log_softmax(-1),
        (teacher.detach().float()/temperature).softmax(-1),reduction='none').sum(-1).mean()
    return loss.clamp_min(0)*(temperature**2)

def select_training_targets(targets,lengths,indices):
    """Existing collate returns padded [batch,phone] targets, not a concatenated vector."""
    if targets.ndim!=2 or lengths.ndim!=1 or len(lengths)!=len(targets) or indices.ndim!=1 or not len(indices):
        raise ValueError('invalid padded CTC batch')
    if (indices<0).any() or (indices>=len(targets)).any() or (lengths<=0).any() or (lengths>targets.shape[1]).any():
        raise ValueError('CTC index/length outside padded batch')
    return targets.index_select(0,indices),lengths.index_select(0,indices)

def _same_group(candidate,baseline):
    try:
        return all(type(g[k])is int and g[k]>0 for g in (candidate,baseline) for k in ('records','phones')) and all(candidate[k]==baseline[k] for k in ('records','phones')) and all(type(g['edits'])is int and g['edits']>=0 for g in (candidate,baseline))
    except (KeyError,TypeError):return False

def eligible_anchor(candidate,baseline,tempo,baseline_tempo):
    try:
        if not all(_same_group(candidate[g],baseline[g]) for g in ('all','old19','new6','focus18')):return False
        if not all(_same_group(tempo[g],baseline_tempo[g]) for g in ('all','amma')):return False
        return (candidate['focus18']['edits']<baseline['focus18']['edits']
            and all(candidate[g]['edits']<=baseline[g]['edits'] for g in ('all','old19','new6'))
            and candidate['all']['edits']/candidate['all']['phones']<=.5570071699025215
            and tempo['all']['edits']<baseline_tempo['all']['edits']
            and tempo['amma']['edits']<=baseline_tempo['amma']['edits'])
    except (KeyError,TypeError,ZeroDivisionError):return False
