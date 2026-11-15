"""DEC068/PHN008: source-balanced train-only sampling and length-aware CTC."""
from collections import Counter,defaultdict
import math
import numpy as np
import torch
from torch.nn import functional as F
from .focused_words import FOCUS_IDS
from .phoneme_backbone import ctc_min_frames


def mixed_sampling_weights(rows, focus_fraction=.5, clean_fraction=.75, *, focus_ids=FOCUS_IDS):
    if not rows or not all(math.isfinite(x) and 0<x<1 for x in (focus_fraction,clean_fraction)):
        raise ValueError('Nonempty training rows and mixture fractions in(0,1) required')
    if isinstance(focus_ids,(str,bytes)) or not focus_ids or any(not isinstance(w,str)or not w for w in focus_ids):
        raise ValueError('Explicit nonempty practice ID inventory required')
    focus_ids=frozenset(focus_ids)
    keys=set();parents=defaultdict(set);identities={}
    for row in rows:
        if row['split']!='train' or row['kind']not in ('train_clean','train_tempo') or not row['speaker']:
            raise ValueError('Only identified train source features may be sampled')
        key=(row['source_row'],row['kind'])
        if key in keys:raise ValueError('Duplicate source/kind in training features')
        keys.add(key);parents[row['source_row']].add(row['kind'])
        identity=(row.get('practice_id'),row['speaker'])
        if identities.setdefault(row['source_row'],identity)!=identity:raise ValueError('Augmented source identity differs')
    if any(kinds!={'train_clean','train_tempo'}for kinds in parents.values()):
        raise ValueError('Every retained source needs clean and paired tempo features')
    focus_words={r['practice_id']for r in rows if r.get('practice_id')in focus_ids}
    other=Counter(r['kind']for r in rows if r.get('practice_id')not in focus_ids)
    if not focus_words or not other:raise ValueError('Focus and broad replay groups are required')
    speakers={w:{r['speaker']for r in rows if r.get('practice_id')==w}for w in focus_words}
    counts=Counter((r.get('practice_id'),r['speaker'],r['kind'])for r in rows)
    weights=[]
    for row in rows:
        kind_mass=clean_fraction if row['kind']=='train_clean'else 1-clean_fraction
        word=row.get('practice_id')
        if word in focus_words:
            weight=focus_fraction*kind_mass/len(focus_words)/len(speakers[word])/counts[(word,row['speaker'],row['kind'])]
        else:weight=(1-focus_fraction)*kind_mass/other[row['kind']]
        weights.append(weight)
    return np.asarray(weights,dtype=np.float64)


def length_aware_ctc_loss(logits, targets, target_lengths, frame_lengths, *, blank):
    if logits.ndim!=3 or targets.ndim!=1 or target_lengths.ndim!=1 or frame_lengths.ndim!=1:
        raise ValueError('Invalid CTC tensor dimensions')
    if len(target_lengths)!=len(logits) or len(frame_lengths)!=len(logits):raise ValueError('CTC batch lengths differ')
    if targets.dtype not in (torch.int32,torch.int64) or any(v.dtype not in (torch.int32,torch.int64)for v in (target_lengths,frame_lengths)):
        raise ValueError('CTC targets/lengths must be integers')
    if type(blank)is not int or not 0<=blank<logits.shape[-1]:raise ValueError('Invalid CTC blank')
    lengths=target_lengths.detach().cpu();frames=frame_lengths.detach().cpu()
    if (lengths<=0).any() or (frames<=0).any() or (frames>logits.shape[1]).any() or int(lengths.sum())!=len(targets):
        raise ValueError('Invalid CTC target/frame lengths')
    if ((targets<0)|(targets>=logits.shape[-1])|(targets==blank)).any():raise ValueError('Invalid target/blank phone')
    labels=targets.detach().cpu().tolist();offset=0
    for count,available in zip(lengths.tolist(),frames.tolist()):
        if available<ctc_min_frames(labels[offset:offset+count]):raise ValueError('Labels impossible within actual acoustic frames')
        offset+=count
    if not torch.isfinite(logits).all():raise ValueError('Nonfinite CTC logits')
    values=F.ctc_loss(logits.float().log_softmax(-1).transpose(0,1),targets.to(logits.device),
        frames,lengths,blank=blank,reduction='none',zero_infinity=False)
    return (values/lengths.to(logits.device)).mean()
