"""DEC068/PHN008: disk guards for retained local research and qualified exports."""
import math
import shutil
from pathlib import Path


def storage_guard(root, *, max_output_gib=10.):
    if not math.isfinite(max_output_gib) or max_output_gib<=0:raise ValueError('Positive finite output budget required')
    free={drive:shutil.disk_usage(drive+':/').free for drive in ('C','D','E')}
    if free['C']<512*1024**2 or free['D']<250*1024**2 or free['E']<2*1024**3:
        raise OSError('Backbone storage reserve reached; free_bytes='+str(free))
    total=sum(p.stat().st_size for top in Path(root).iterdir()if top.name not in ('models','deps','tmp')
        for p in ([top]if top.is_file()else top.rglob('*'))if p.is_file())
    if total>max_output_gib*1024**3:raise OSError('Backbone output budget reached')
    return free
