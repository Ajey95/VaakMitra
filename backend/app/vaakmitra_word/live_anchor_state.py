"""DEC067/PHN007: verified public parity origins and atomic epoch commits."""
import hashlib,json,math,os,re,uuid
from pathlib import Path
from .live_anchor import eligible_anchor

def file_sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as source:
        for block in iter(lambda:source.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def verify_export_inputs(binding,paths):
    required={'focus_data','base_audio','extra_audio','tempo_manifest','tempo_audio'}
    if set(paths)!=required:raise ValueError('Incomplete export input inventory')
    for key,path in paths.items():
        if not isinstance(binding.get(key),str) or file_sha(path)!=binding[key]:
            raise ValueError(f'Export input changed: {key}')

def parity_origins(rows,calibration,tempo,fixture_sha):
    origins={}
    for row in rows:origins.setdefault(row['audio_sha256'],set()).add(row['split'])
    if any(r['split']!='calibration' or origins.get(r['audio_sha256'])!={'calibration'} for r in calibration):
        raise ValueError('Natural parity row is not calibration')
    if any(r['split']!='calibration' for r in tempo):raise ValueError('Tempo parity row is not calibration')
    source=origins.get(fixture_sha,set())
    if len(source)!=1 or not source<={'train','calibration','evaluation'}:raise ValueError('Unknown/ambiguous fixture origin')
    split=next(iter(source))
    return dict(natural_calibration_clips=len(calibration),tempo_calibration_clips=len(tempo),
        historical_fixture_clips=1,fixture_source_split=split,
        calibration_only=split=='calibration',evaluation_inference_accessed=split=='evaluation',
        full_evaluation_cohort_inferred=False)

def _atomic_json(path,value):
    path=Path(path);temporary=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    with temporary.open('x',encoding='utf-8') as f:
        json.dump(value,f,sort_keys=True);f.flush();os.fsync(f.fileno())
    os.replace(temporary,path)

def _load_epoch(out,entry,binding,config,history):
    import torch
    filename=entry.get('file','')
    if not re.fullmatch(r'epoch-\d{4}-[a-f0-9]{32}\.pt',filename):raise ValueError('Invalid committed filename')
    path=Path(out)/filename
    if file_sha(path)!=entry.get('sha256'):raise ValueError('Committed checkpoint hash differs')
    state=torch.load(path,map_location='cpu',weights_only=True)
    if state.get('anchor_binding')!=binding or state.get('anchor_config')!=config or state.get('epoch')!=entry['epoch'] or state.get('anchor_history')!=history:
        raise ValueError('Committed checkpoint/evidence mismatch')
    return state

def load_trial_commit(out,binding,config):
    path=Path(out)/'epoch-commit.json'
    if not path.exists():return None
    pointer=json.loads(path.read_text(encoding='utf-8'))
    if pointer.get('binding')!=binding or pointer.get('config')!=config:raise ValueError('Committed trial binding differs')
    entries=pointer.get('epochs')
    if not isinstance(entries,list) or not 1<=len(entries)<=8:raise ValueError('Invalid committed history')
    for epoch,entry in enumerate(entries,1):
        if type(entry.get('epoch'))is not int or entry['epoch']!=epoch or entry.get('record',{}).get('epoch')!=epoch:
            raise ValueError('Committed epochs are not contiguous')
    history=[e['record'] for e in entries]
    return dict(entries=entries,history=history,last=_load_epoch(out,entries[-1],binding,config,history))

def commit_epoch(out,state,record,binding,config):
    """Only one atomic pointer makes a complete model+evidence epoch authoritative."""
    import torch
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    previous=load_trial_commit(out,binding,config);entries=[] if previous is None else previous['entries']
    epoch=len(entries)+1
    if epoch>8 or state.get('epoch')!=epoch or record.get('epoch')!=epoch or state.get('anchor_binding')!=binding or state.get('anchor_config')!=config:
        raise ValueError('Cannot commit incompatible/nonconsecutive epoch')
    history=[e['record'] for e in entries]+[record]
    state=dict(state,anchor_history=history)
    filename=f'epoch-{epoch:04}-{uuid.uuid4().hex}.pt';path=out/filename
    with path.open('xb') as f:
        torch.save(state,f);f.flush();os.fsync(f.fileno())
    entry=dict(epoch=epoch,file=filename,sha256=file_sha(path),record=record)
    # A crash before this replacement leaves only an ignored orphan checkpoint.
    _atomic_json(out/'epoch-commit.json',dict(binding=binding,config=config,epochs=entries+[entry]))
    return entry

def select_trial_candidate(out,binding,config,baseline,tempo_baseline):
    committed=load_trial_commit(out,binding,config)
    if committed is None:return None
    candidates=[]
    for entry in committed['entries']:
        record=entry['record'];ok=eligible_anchor(record['calibration'],baseline,record['tempo'],tempo_baseline)
        if type(record.get('eligible'))is not bool or ok!=record['eligible']:raise ValueError('Committed eligibility differs')
        if ok:
            c=record['calibration'];t=record['tempo']
            score=.6*c['focus18']['edits']/c['focus18']['phones']+.2*c['all']['edits']/c['all']['phones']+.2*t['all']['edits']/t['all']['phones']
            if not math.isfinite(record['score']) or not math.isclose(score,record['score'],rel_tol=1e-9,abs_tol=1e-12):raise ValueError('Committed score differs')
            _load_epoch(out,entry,binding,config,committed['history'][:entry['epoch']])
            candidates.append(dict(entry,score=score))
    return min(candidates,key=lambda x:x['score']) if candidates else None
