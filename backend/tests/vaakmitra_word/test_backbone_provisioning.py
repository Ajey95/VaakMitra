"""DEC068: USB can return success after a short write; no partial may become a model."""
import hashlib,subprocess,sys
from scripts.model.cache_phoneme_backbone import write
from scripts.model import provision_backbone_phone as provision


def test_short_usb_write_is_resumed_and_only_full_sha_verified_model_is_published(tmp_path,monkeypatch):
    payload=bytes(range(256))*12289;model=tmp_path/'model.onnx';model.write_bytes(payload)
    digest=hashlib.sha256(payload).hexdigest();bundle=tmp_path/'bundle';bundle.mkdir()
    write(bundle/'bundle.json',dict(model_delivery='authenticated_app_private_cache',model_file='phoneme.fp32.onnx',
        model_sha256=digest,model_bytes=len(payload)))
    remote={};writes=0;real_run=subprocess.run
    def fake(args,**kw):
        nonlocal writes
        args=list(map(str,args));code=0;output=''
        if 'get-state'in args:output='device'
        elif 'exec-in'in args:
            writes+=1
            pipe={key:kw[key]for key in('stdin','input')if key in kw}
            # Exercise the real host binary pipe, including NUL/nonUTF8 bytes, before fake USB delivery.
            delivered=real_run([sys.executable,'-c','import sys;sys.stdout.buffer.write(sys.stdin.buffer.read())'],capture_output=True,**pipe)
            data=delivered.stdout;filename=next(a[3:]for a in args if a.startswith('of='))
            seek=next((int(a[5:])for a in args if a.startswith('seek=')),0)*1048576
            if writes==1:data=data[:1048576//2]
            previous=remote.get(filename,b'');remote[filename]=previous[:seek]+data+previous[seek+len(data):]
        elif 'sha256sum'in args:
            if args[-1]not in remote:code=1
            else:output=hashlib.sha256(remote[args[-1]]).hexdigest()+'  '+args[-1]
        elif 'stat'in args:
            if args[-1]not in remote:code=1
            else:output=str(len(remote[args[-1]]))
        elif 'mv'in args:remote[args[-1]]=remote.pop(args[-2])
        elif 'chmod'in args or 'mkdir'in args or 'wait-for-device'in args:pass
        result=subprocess.CompletedProcess(args,code,output,'')
        if kw.get('check')and code:raise subprocess.CalledProcessError(code,args,output=output,stderr='missing')
        return result
    monkeypatch.setattr(provision.subprocess,'run',fake)
    output=tmp_path/'phone-proof.json'
    provision.main(tmp_path/'adb.exe','explicit-phone',model,bundle,output)
    final=f'no_backup/phoneme-models/{digest}.onnx'
    assert remote[final]==payload and writes>=2 and output.exists()
