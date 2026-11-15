"""DEC-058 final review: representation-safe leakage and consumer cache identity."""
import hashlib,json
from pathlib import Path
import numpy as np
import pytest
from app.vaakmitra_word.focused_words import validate_extra_rows
from scripts.model import focused_phoneme_update as run

def test_source_digest_collision_is_rejected_even_with_different_names_speakers_and_decoded_hashes():
 reserved=dict(split='evaluation',speaker='reserved',source_utterance_id='heldout',audio_sha256='wav-file-hash',source_audio_sha256='same-original-opus')
 extra=dict(split='train',speaker='different',source_utterance_id='different-name',audio_sha256='decoded-float-hash',source_audio_sha256='same-original-opus')
 with pytest.raises(ValueError):validate_extra_rows([], [extra], [reserved])

def test_padded_pcm_duplicate_is_rejected_across_different_file_encodings():
 base=dict(split='train',speaker='a',source_utterance_id='a',audio_sha256='wav',pcm_sha256='same-pcm')
 extra=dict(split='train',speaker='b',source_utterance_id='b',audio_sha256='opus-decoded',pcm_sha256='same-pcm')
 with pytest.raises(ValueError):validate_extra_rows([base],[extra],[])

def test_all_prepared_mswc_holdouts_are_reserved_with_original_source_digest():
 raw=dict(original_id='என்ன/common_voice_ta_123.opus',audio_sha256='source-opus')
 prepared=dict(raw,split='calibration',speaker_pseudonym='heldout',audio_sha256='prepared-wav')
 result=run.reserved_mswc_rows([prepared,dict(prepared,split='train')],[raw])
 assert len(result)==1 and result[0]['source_audio_sha256']=='source-opus'
 assert result[0]['source_utterance_id']=='commonvoice:ta:common_voice_ta_123'

def test_same_shape_parent_cache_change_is_rejected_at_consumer_entry(tmp_path,monkeypatch):
 base=tmp_path/'base';base.mkdir();root=tmp_path/'run';root.mkdir();monkeypatch.setattr(run,'BASE',base)
 (base/'dataset.json').write_text('{}');(base/'best.pt').write_bytes(b'checkpoint')
 np.save(base/'audio.npy',np.zeros((1,48000),dtype=np.float32));np.save(root/'extra-audio.npy',np.zeros((1,48000),dtype=np.float32))
 data=dict(parent_dataset_sha256=run.original.sha(base/'dataset.json'),base_audio_sha256=run.original.sha(base/'audio.npy'),extra_audio_sha256=run.original.sha(root/'extra-audio.npy'))
 run.original.write(root/'focus-data.json',data)
 run.original.write(root/'input-binding.json',dict(focus_data_sha256=run.original.sha(root/'focus-data.json'),base_checkpoint_sha256=run.original.sha(base/'best.pt'),script_sha256=run.original.sha(run.__file__),contract_sha256=run.original.sha(Path(run.__file__).parents[2]/'app/vaakmitra_word/focused_words.py')))
 run.validate_inputs(root)
 np.save(base/'audio.npy',np.ones((1,48000),dtype=np.float32))
 with pytest.raises(ValueError,match='cache'):run.validate_inputs(root)

def test_apk_practice_references_bind_all_25_ids_to_the_frozen_inventory():
 root=Path(__file__).parents[3]/'SpeakEasyAndroid/app/src/main/assets/vaakmitra/practice-words-v1'
 manifest=json.loads((root/'bundle.json').read_text());raw=(root/'references.json').read_bytes()
 assert hashlib.sha256(raw).hexdigest()==manifest['references_sha256']
 data=json.loads(raw);assert len(data['expected'])==25
 assert not data['expert_approved']and not data['approved_for_child_scoring']
 vocabulary=json.loads((root.parent/'phoneme-ta19-v1/vocabulary.json').read_text())
 assert data['tokens']==vocabulary['tokens']
 assert all(p in data['tokens']for phones in data['expected'].values()for p in phones)
