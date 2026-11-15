"""DEC058: stable practice migration, train-only mass and strict nonregression gates."""
import copy
import pytest
from app.vaakmitra_word.focused_words import NEW_WORDS,FOCUS_IDS,sampling_weights,validate_extra_rows,metrics,eligible

def test_new_ids_and_focus_are_explicit_without_reindexing_original_words():
 assert [w['id']for w in NEW_WORDS]==['TA_WORD_0101','TA_WORD_0102','TA_WORD_0103','TA_WORD_0104','TA_WORD_0084','TA_WORD_0061']
 assert len(FOCUS_IDS)==18 and len(set(FOCUS_IDS))==18
 assert [w['tamil']for w in NEW_WORDS]==['என்ன','நான்','இது','எனக்கு','கை','வீடு']

def test_sampling_balances_words_then_speakers_not_duplicate_clip_counts():
 rows=[dict(split='train',practice_id='TA_WORD_0001',speaker='a')for _ in range(3)]+[dict(split='train',practice_id='TA_WORD_0001',speaker='b'),dict(split='train',practice_id='TA_WORD_0101',speaker='c'),dict(split='train',practice_id=None,speaker='d')]
 w=sampling_weights(rows,.75);assert sum(w)==pytest.approx(1);assert sum(w[:3])==pytest.approx(.1875);assert w[3]==pytest.approx(.1875);assert w[4]==pytest.approx(.375);assert w[5]==pytest.approx(.25)
 with pytest.raises(ValueError):sampling_weights([dict(rows[0],split='calibration'),rows[-1]],.75)

@pytest.mark.parametrize('field,value',[('speaker','reserved'),('source_utterance_id','reserved-parent'),('audio_sha256','heldout-hash')])
def test_extra_train_cannot_touch_reserved_identity_or_audio(field,value):
 base=[dict(split='calibration',speaker='reserved',source_utterance_id='reserved-parent',audio_sha256='heldout-hash')]
 extra=dict(split='train',speaker='new',source_utterance_id='new-parent',audio_sha256='new-hash');extra[field]=value
 with pytest.raises(ValueError):validate_extra_rows(base,[extra],[])
 assert base[0]['split']=='calibration'

def test_metrics_reject_length_mismatch_and_record_edits_and_denominators():
 rows=[dict(targets=[1,2],is_target=True,practice_id='TA_WORD_0001'),dict(targets=[1],is_target=False,practice_id='TA_WORD_0101')]
 m=metrics([[1],[1]],rows);assert m['focus18']['edits']==1 and m['focus18']['phones']==3;assert m['new6']['edits']==0
 with pytest.raises(ValueError):metrics([[1]],rows)

def test_selection_needs_real_focus_gain_and_preserves_both_existing_and_new_words():
 b={g:dict(phoneme_error_rate=.1,records=10,phones=100,edits=10)for g in ['all','old19','new6','focus18']}
 c=copy.deepcopy(b);assert not eligible(c,b,.5570071699025215)
 c['focus18']['phoneme_error_rate']=.09;assert eligible(c,b,.5570071699025215)
 for g in ['old19','new6']:
  bad=copy.deepcopy(c);bad[g]['phoneme_error_rate']=.11;assert not eligible(bad,b,.5570071699025215)
 bad=copy.deepcopy(c);bad['all']['phoneme_error_rate']=.56;assert not eligible(bad,b,.5570071699025215)
 bad=copy.deepcopy(c);bad['new6']['records']=0;assert not eligible(bad,b,.5570071699025215)
