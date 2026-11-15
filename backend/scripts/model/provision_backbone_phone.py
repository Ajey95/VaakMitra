"""Provision one authenticated public model to the explicitly selected debug phone; no microphone."""
import argparse,subprocess,time,hashlib
from pathlib import Path
from scripts.model.cache_phoneme_backbone import read,write,sha

PACKAGE='com.team96.speakeasy'


def main(adb,serial,source,bundle,out):
    header=read(bundle/'bundle.json');digest=header['model_sha256']
    if header.get('model_delivery')!='authenticated_app_private_cache'or header['model_file']!='phoneme.fp32.onnx':raise ValueError('Not a declared cache-provisioned model')
    if len(digest)!=64 or any(c not in '0123456789abcdef'for c in digest):raise ValueError('Invalid model identity')
    if source.stat().st_size!=header['model_bytes']or sha(source)!=digest:raise ValueError('Source model differs')
    command=[str(adb),'-s',serial]
    def run(*args,timeout=30):
        return subprocess.run(command+list(args),check=True,capture_output=True,text=True,timeout=timeout).stdout.strip()
    if run('get-state')!='device':raise ValueError('Selected phone not authorized')
    remote='no_backup/phoneme-models';destination=f'{remote}/{digest}.onnx';partial=f'{remote}/{digest}.provision.partial'
    run('shell','run-as',PACKAGE,'mkdir','-p',remote)
    existing=subprocess.run(command+['shell','run-as',PACKAGE,'sha256sum',destination],capture_output=True,text=True,timeout=45)
    if existing.returncode==0 and existing.stdout.split()[0]==digest:
        print('Authenticated model already provisioned',flush=True);return
    started=time.monotonic();print(dict(stage='model_transfer_started',serial=serial,bytes=source.stat().st_size),flush=True)
    block_size=1048576;chunk_size=8*block_size
    def resume_offset():
        size_result=subprocess.run(command+['shell','run-as',PACKAGE,'stat','-c','%s',partial],capture_output=True,text=True,timeout=30)
        if size_result.returncode:
            if run('get-state')!='device':raise RuntimeError('Phone unavailable')
            return 0
        size=int(size_result.stdout.strip())
        if not 0<=size<=header['model_bytes']:raise ValueError('Invalid private partial length')
        expected=hashlib.sha256()
        with source.open('rb')as stream:
            remaining=size
            while remaining:
                data=stream.read(min(1048576,remaining));expected.update(data);remaining-=len(data)
        if run('shell','run-as',PACKAGE,'sha256sum',partial,timeout=90).split()[0]!=expected.hexdigest():
            raise ValueError('Private partial is not a source prefix; refusing to resume')
        return size//block_size*block_size
    offset=resume_offset();retries=0
    # Each binary chunk is bounded; a transport can report success after writing only a prefix.
    # Validate length after every chunk, source-prefix SHA on reconnect and full SHA before rename.
    with source.open('rb')as stream:
        while offset<header['model_bytes']:
            stream.seek(offset);data=stream.read(min(chunk_size,header['model_bytes']-offset))
            try:
                result=subprocess.run(command+['exec-in','run-as',PACKAGE,'dd',f'of={partial}',f'bs={block_size}',
                    f'seek={offset//block_size}','conv=notrunc'],input=data,capture_output=True,timeout=30)
                if result.returncode:raise RuntimeError('USB chunk transfer failed')
                size=int(run('shell','run-as',PACKAGE,'stat','-c','%s',partial))
                if size!=offset+len(data):raise RuntimeError('USB chunk write was short')
                offset=size;retries=0
                print(dict(stage='model_transfer_progress',verified_length=offset,total=header['model_bytes']),flush=True)
            except (subprocess.SubprocessError,RuntimeError):
                retries+=1
                if retries>6:raise RuntimeError('Repeated USB failures; private partial retained, no model published')
                run('wait-for-device',timeout=15);offset=resume_offset()
                print(dict(stage='model_transfer_resumed',source_prefix_verified_bytes=offset,retry=retries),flush=True)
    measured=run('shell','run-as',PACKAGE,'sha256sum',partial,timeout=90).split()[0]
    size=int(run('shell','run-as',PACKAGE,'stat','-c','%s',partial))
    if measured!=digest or size!=header['model_bytes']:raise ValueError('Phone model readback differs; partial not published')
    run('shell','run-as',PACKAGE,'chmod','600',partial)
    run('shell','run-as',PACKAGE,'mv',partial,destination)
    proof=dict(model_sha256=digest,model_bytes=size,serial=serial,package=PACKAGE,remote_private_path=destination,
        source_path=str(source),bundle_sha256=sha(bundle/'bundle.json'),elapsed_seconds=time.monotonic()-started,
        phone_sha256_readback_verified=True,no_audio_recorded=True,offline_after_provisioning=True)
    write(out,proof);print(proof,flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser()
    for key in('adb','source','bundle','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--serial',required=True)
    a=p.parse_args();main(a.adb,a.serial,a.source,a.bundle,a.output)
