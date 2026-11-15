"""DEC-058: process-released leases, immutable freeze and exactly-once test claims."""
from contextlib import contextmanager
import datetime,json,os,uuid
from pathlib import Path

def freeze_operation(root,identity):
 root=Path(root);path=root/'test-access-freeze.json';temporary=root/('freeze-'+uuid.uuid4().hex+'.tmp')
 try:
  with temporary.open('x',encoding='utf8')as f:
   json.dump(dict(identity,frozen_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()),f,sort_keys=True);f.flush();os.fsync(f.fileno())
  try:os.link(temporary,path)
  except FileExistsError:pass
 finally:temporary.unlink(missing_ok=True)
 stored=json.loads(path.read_text(encoding='utf8'))
 stored.pop('frozen_at_utc')
 if stored!=identity:raise ValueError('finalization freeze identity changed')
 return stored

def claim_evaluation(root,identity):
 path=Path(root)/'evaluation-ticket.json'
 try:fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL)
 except FileExistsError:return False
 with os.fdopen(fd,'w',encoding='utf8')as f:
  json.dump(identity,f,sort_keys=True);f.flush();os.fsync(f.fileno())
 return True

@contextmanager
def operation_lease(root):
 # OS locks release even when the process dies; a leftover lock file is harmless.
 with (Path(root)/'finalization.lock').open('a+b')as f:
  f.seek(0,os.SEEK_END)
  if f.tell()==0:f.write(b'0');f.flush()
  f.seek(0)
  try:
   if os.name=='nt':
    import msvcrt
    msvcrt.locking(f.fileno(),msvcrt.LK_NBLCK,1)
   else:
    import fcntl
    fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)
  except OSError as exc:raise RuntimeError('finalization already running')from exc
  try:yield
  finally:
   f.seek(0)
   if os.name=='nt':msvcrt.locking(f.fileno(),msvcrt.LK_UNLCK,1)
   else:fcntl.flock(f,fcntl.LOCK_UN)

def robustness_counts(source_clips,variants):
 return dict(source_clips=len(source_clips),distinct_source_utterances=len({r['source_utterance_id']for r in source_clips}),synthetic_derivatives=len(source_clips)*variants)
