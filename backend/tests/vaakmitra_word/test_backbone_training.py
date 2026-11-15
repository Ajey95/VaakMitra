"""DEC068/PHN008: gradients use train rows and true acoustic frame limits."""
import numpy as np
import pytest
import torch
from app.vaakmitra_word.backbone_training import mixed_sampling_weights,length_aware_ctc_loss

def rows():
    return [dict(split='train',kind=kind,source_row=i,practice_id=word,speaker=f'voice-{i%2}')for i,word in enumerate(('TA_WORD_0001','TA_WORD_0002','OTHER','OTHER'))for kind in ('train_clean','train_tempo')]

def test_focus_and_clean_mixture_mass_is_independent_of_record_counts():
    rs=rows();w=mixed_sampling_weights(rs,focus_fraction=.5,clean_fraction=.75)
    assert np.isclose(sum(w),1.)
    assert np.isclose(sum(x for r,x in zip(rs,w)if r['practice_id']!='OTHER'),.5)
    assert np.isclose(sum(x for r,x in zip(rs,w)if r['kind']=='train_clean'),.75)

def test_calibration_and_duplicate_feature_rows_cannot_enter_training_sampler():
    rs=rows();rs[0]['split']='calibration'
    with pytest.raises(ValueError):mixed_sampling_weights(rs)
    rs=rows();rs.append(rs[0])
    with pytest.raises(ValueError):mixed_sampling_weights(rs)

def test_explicit_all_practice_scope_balances_words_while_preserving_broad_replay():
    rs=rows()+[dict(split='train',kind=kind,source_row=4,practice_id='BROAD',speaker='other-voice')for kind in ('train_clean','train_tempo')]
    w=mixed_sampling_weights(rs,focus_fraction=.8,focus_ids=('TA_WORD_0001','TA_WORD_0002','OTHER'))
    for word in ('TA_WORD_0001','TA_WORD_0002','OTHER'):
        assert np.isclose(sum(x for r,x in zip(rs,w)if r['practice_id']==word),.8/3)
    assert np.isclose(sum(x for r,x in zip(rs,w)if r['practice_id']=='BROAD'),.2)
    assert np.isclose(sum(x for r,x in zip(rs,w)if r['kind']=='train_clean'),.75)

def test_ctc_loss_never_uses_padded_silence_to_make_impossible_labels_feasible():
    logits=torch.randn(1,10,4,requires_grad=True)
    with pytest.raises(ValueError):length_aware_ctc_loss(logits,torch.tensor([0,1,2]),torch.tensor([3]),torch.tensor([2]),blank=3)
    with pytest.raises(ValueError):length_aware_ctc_loss(logits,torch.tensor([1,1]),torch.tensor([2]),torch.tensor([2]),blank=3)

def test_ctc_gradient_is_zero_past_each_examples_valid_acoustic_length():
    logits=torch.randn(2,7,4,requires_grad=True)
    loss=length_aware_ctc_loss(logits,torch.tensor([0,1,1]),torch.tensor([2,1]),torch.tensor([6,3]),blank=3)
    assert torch.isfinite(loss)
    loss.backward()
    assert torch.isfinite(logits.grad).all()
    assert torch.count_nonzero(logits.grad[0,6:])==0
    assert torch.count_nonzero(logits.grad[1,3:])==0
