"""DEC058: provisional practice vocabulary and train/calibration safety contracts."""
from collections import Counter
import math

NEW_WORDS=(
 dict(id='TA_WORD_0101',tamil='என்ன',latin='Enna',meaning='What',category='Communication',difficulty=1),
 dict(id='TA_WORD_0102',tamil='நான்',latin='Naan',meaning='I / me',category='Communication',difficulty=1),
 dict(id='TA_WORD_0103',tamil='இது',latin='Ithu',meaning='This',category='Communication',difficulty=1),
 dict(id='TA_WORD_0104',tamil='எனக்கு',latin='Enakku',meaning='For me / to me',category='Needs',difficulty=2),
 dict(id='TA_WORD_0084',tamil='கை',latin='Kai',meaning='Hand',category='Body',difficulty=1),
 dict(id='TA_WORD_0061',tamil='வீடு',latin='Veedu',meaning='Home',category='Places',difficulty=2),
)
CORE_IDS=('TA_WORD_0001','TA_WORD_0002','TA_WORD_0083','TA_WORD_0082','TA_WORD_0015','TA_WORD_0016','TA_WORD_0013','TA_WORD_0014','TA_WORD_0017','TA_WORD_0012','TA_WORD_0072','TA_WORD_0050')
NEW_IDS=frozenset(w['id']for w in NEW_WORDS)
FOCUS_IDS=CORE_IDS+tuple(w['id']for w in NEW_WORDS)

def sampling_weights(rows,fraction):
 if not 0<fraction<1 or any(r['split']!='train'for r in rows):raise ValueError('train-only fraction in (0,1) required')
 focus=[r for r in rows if r.get('practice_id')in FOCUS_IDS];other=len(rows)-len(focus)
 words={r['practice_id']for r in focus};speakers={w:{r['speaker']for r in focus if r['practice_id']==w}for w in words}
 counts=Counter((r['practice_id'],r['speaker'])for r in focus)
 if not words or not other:raise ValueError('focus and replay rows required')
 return [fraction/len(words)/len(speakers[r['practice_id']])/counts[r['practice_id'],r['speaker']]if r.get('practice_id')in words else(1-fraction)/other for r in rows]

def parent(r):return r.get('source_utterance_id')or r.get('parent_id')or r['audio_path'].rsplit('/',2)[-2]

def validate_extra_rows(base,extra,audit):
 reserved=[r for r in base if r['split']!='train']+list(audit)
 speakers={r['speaker']for r in reserved};parents={parent(r)for r in reserved}
 all_rows=base+list(audit)
 hashes={(r.get('audio_hash_kind','file'),r['audio_sha256'])for r in all_rows}
 source_hashes={r['source_audio_sha256']for r in all_rows if r.get('source_audio_sha256')}
 pcm_hashes={r['pcm_sha256']for r in all_rows if r.get('pcm_sha256')}
 for row in extra:
  identity=(row.get('audio_hash_kind','file'),row['audio_sha256'])
  if row['split']!='train' or row['speaker']in speakers or parent(row)in parents or identity in hashes or (row.get('source_audio_sha256')and row['source_audio_sha256']in source_hashes)or(row.get('pcm_sha256')and row['pcm_sha256']in pcm_hashes):raise ValueError('extra source overlaps reserved speaker/parent/audio')
  hashes.add(identity)
  if row.get('source_audio_sha256'):source_hashes.add(row['source_audio_sha256'])
  if row.get('pcm_sha256'):pcm_hashes.add(row['pcm_sha256'])

def distance(a,b):
 row=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  next_row=[i]
  for j,y in enumerate(b,1):next_row.append(min(next_row[-1]+1,row[j]+1,row[j-1]+(x!=y)))
  row=next_row
 return row[-1]

def metrics(predictions,rows):
 if len(predictions)!=len(rows):raise ValueError('prediction/row count mismatch')
 def group(pairs):
  phones=sum(len(r['targets'])for p,r in pairs);edits=sum(distance(r['targets'],p)for p,r in pairs)
  return dict(records=len(pairs),phones=phones,edits=edits,phoneme_error_rate=edits/max(1,phones),exact_sequence_accuracy=sum(p==r['targets']for p,r in pairs)/max(1,len(pairs)),empty_prediction_rate=sum(not p for p,r in pairs)/max(1,len(pairs)))
 pairs=list(zip(predictions,rows))
 return dict(all=group(pairs),old19=group([(p,r)for p,r in pairs if r['is_target']]),new6=group([(p,r)for p,r in pairs if r.get('practice_id')in NEW_IDS]),focus18=group([(p,r)for p,r in pairs if r.get('practice_id')in FOCUS_IDS]))

def eligible(candidate,baseline,broad_cap):
 for g in ('all','old19','new6','focus18'):
  if candidate[g]['records']!=baseline[g]['records'] or candidate[g]['phones']!=baseline[g]['phones']or candidate[g]['records']<=0 or not math.isfinite(candidate[g]['phoneme_error_rate']):return False
 return candidate['focus18']['phoneme_error_rate']<baseline['focus18']['phoneme_error_rate'] and all(candidate[g]['phoneme_error_rate']<=baseline[g]['phoneme_error_rate']for g in ['old19','new6']) and candidate['all']['phoneme_error_rate']<=broad_cap
