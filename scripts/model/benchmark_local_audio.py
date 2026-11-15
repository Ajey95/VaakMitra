"""DEC078/PHN019: public-adult, loopback-only Gemma benchmark; never a product route."""
from pathlib import Path,PurePosixPath
import argparse,collections,contextlib,copy,hashlib,io,json,math,os,secrets,shutil,subprocess,sys,tarfile,time,urllib.request,uuid,wave,zipfile

REPO=Path(__file__).resolve().parents[2]
OLD=Path(r'C:\Users\AJEYA\VaakMitraBuildTemp\adult-boundary-reference-20261113')
LAB=REPO/'.superpowers/sdd/2026-11-14-local-gemma-adult'
WEIGHTS=Path(r'E:\VaakMitraModelLab\20261112-phoneme-transfer')
SOURCE=Path(r'D:\VaakMitraData\manifests\mswc-ta-other.jsonl')
sys.path[:0]=[str(WEIGHTS/'deps'),str(REPO/'backend')]
GRID=[.5,.7,.8,.9,.95,.98,.99]
OUTPUT_CAP=10*1024**2
PROTOCOL_FILE='benchmark-protocol-v4.json'
FREEZE_FILE='freeze-v4.json'
DIAGNOSTIC=False

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def sha(path):
    with Path(path).open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def write(path,value):
    path=Path(path);encoded=json.dumps(value,ensure_ascii=False,indent=2).encode('utf8')
    if path.exists():
        if path.read_bytes()!=encoded:raise ValueError('immutable_artifact_exists: '+str(path))
        return
    if path.resolve().is_relative_to(LAB.resolve()):
        sources=[Path(__file__),REPO/'backend/app/vaakmitra_word/local_audio_research.py',REPO/'backend/tests/vaakmitra_word/test_local_audio_research.py']
        used=sum(p.stat().st_size for p in LAB.rglob('*') if p.is_file())+sum(p.stat().st_size for p in sources if p.exists())
        if used+len(encoded)>OUTPUT_CAP:raise OSError('10MiB_research_output_cap')
    path.parent.mkdir(parents=True,exist_ok=True)
    pending=path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.pending')
    with pending.open('xb') as stream:stream.write(encoded);stream.flush();os.fsync(stream.fileno())
    pending.rename(path)

def validate_case_rows(rows,cases):
    signature=lambda row:json.dumps({k:row[k] for k in ['reference','truth','interior']},sort_keys=True)
    expected=collections.Counter((row['id'],signature(ref)) for row in rows for ref in row['references'])
    actual=collections.Counter((row['id'],signature(row)) for row in cases)
    if expected!=actual or len({r['id'] for r in rows})!=len(rows):raise ValueError('source_denominator_or_reference_changed')

def volume_free(path):
    existing=Path(path).resolve()
    while not existing.exists():
        if existing==existing.parent:raise OSError('drive_unavailable')
        existing=existing.parent
    return shutil.disk_usage(existing).free

def storage_guard(root,reserve=2*1024**3):
    root=Path(root).resolve()
    if volume_free(root)<reserve:raise OSError('research_drive_reserve')
    if shutil.disk_usage('C:/').free<512*1024**2 or shutil.disk_usage('D:/').free<250*1024**2:
        raise OSError('C_or_D_reserve')

def download_assets(destination,manifest):
    destination=Path(destination).resolve()
    # This check precedes creating directories or performing any HTTP request.
    started=destination/'download-started.json';identity=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest()
    if not started.exists() and volume_free(destination)<manifest['initial_free_required']:raise OSError('need_8GiB_free_before_download')
    storage_guard(destination)
    destination.mkdir(parents=True,exist_ok=True)
    if started.exists() and read(started)['manifest_sha256']!=identity:raise ValueError('download_resume_identity')
    write(started,{'manifest_sha256':identity})
    receipt=[]
    for item in manifest['models']+manifest['runtime']:
        name=item['file']
        if Path(name).name!=name or '/' in name or '\\' in name or ':' in name:raise ValueError('asset_path')
        target=destination/name
        if not target.exists():
            partial=destination/(name+'.partial')
            if shutil.disk_usage(destination).free-item['bytes']<manifest['post_download_reserve']:raise OSError('projected_reserve')
            count=partial.stat().st_size if partial.exists() else 0
            if count>item['bytes']:raise ValueError('oversized_partial')
            request=urllib.request.Request(item['url'],headers={'Range':'bytes='+str(count)+'-'} if count else {})
            if count<item['bytes']:
              with urllib.request.urlopen(request,timeout=60) as response,partial.open('ab') as out:
                if count and (response.status!=206 or response.headers.get('Content-Range','').split('/')[0]!='bytes '+str(count)+'-'+str(item['bytes']-1)):
                    raise ValueError('server_did_not_honor_pinned_resume_range')
                while block:=response.read(1024*1024):
                    count+=len(block)
                    if count>item['bytes']:raise ValueError('asset_larger_than_manifest')
                    storage_guard(destination);out.write(block)
            if partial.stat().st_size!=item['bytes'] or sha(partial)!=item['sha256']:raise ValueError('download_identity')
            partial.rename(target)
        if target.stat().st_size!=item['bytes'] or sha(target)!=item['sha256']:raise ValueError('existing_asset_identity')
        receipt.append(dict(item,path=str(target)))
        print(json.dumps({'stage':'asset_verified','file':name,'bytes':item['bytes']}),flush=True)
    write(destination/'download-receipt.json',receipt)
    return receipt

def plain_path(path):
    path=Path(path).absolute()
    for part in [path]+list(path.parents):
        if part.exists() and getattr(part.lstat(),'st_file_attributes',0)&1024:raise ValueError('reparse_path_forbidden')

def extract_runtime(archive,destination):
    plain_path(Path(destination).absolute().parent)
    destination=Path(destination).resolve()
    plain_path(destination.parent)
    if destination.exists():raise ValueError('fresh_runtime_directory_required')
    archives=list(archive) if isinstance(archive,(list,tuple)) else [archive]
    with contextlib.ExitStack() as stack:
        sources=[stack.enter_context(zipfile.ZipFile(p)) for p in archives]
        entries=[(source,entry) for source in sources for entry in source.infolist()]
        for source,entry in entries:
            part=PurePosixPath(entry.filename.replace('\\','/'))
            if part.is_absolute() or '..' in part.parts or ':' in entry.filename or (entry.external_attr>>16)&0o170000==0o120000:
                raise ValueError('unsafe_runtime_archive')
        storage_guard(destination.parent)
        if shutil.disk_usage(destination.parent).free-sum(e.file_size for _,e in entries)<2*1024**3:raise OSError('runtime_extraction_reserve')
        destination.mkdir(parents=True,exist_ok=False)
        for source,entry in entries:
            target=destination.joinpath(*PurePosixPath(entry.filename.replace('\\','/')).parts)
            if entry.is_dir():target.mkdir(parents=True,exist_ok=True);continue
            target.parent.mkdir(parents=True,exist_ok=True)
            data=source.read(entry)
            if target.exists():
                if target.read_bytes()!=data:raise ValueError('runtime_file_collision')
            else:
                with target.open('xb') as out:out.write(data)

def prepare():
    from app.vaakmitra_word.local_audio_research import make_audio_payload
    from app.vaakmitra_word.real_adult_sound import units
    protocol=read(OLD/'protocol-final.json')
    rows=protocol['panels']['development_cached']+protocol['panels']['development_complete']
    cases=read(OLD/'corrected-final/development-selected-cases.json')
    validate_case_rows(rows,cases)
    if len(rows)!=159 or len(cases)!=565:raise ValueError('unexpected_development_panel')
    wanted={r['id']:r for r in rows if r['scope']=='keyword'};metadata={}
    with SOURCE.open(encoding='utf8') as stream:
        for line in stream:
            row=json.loads(line)
            if row['sample_id'] in wanted:
                if row['audio_sha256']!=wanted[row['sample_id']]['source_audio_sha256']:raise ValueError('source_hash_join')
                metadata[row['sample_id']]=row
    if set(metadata)!=set(wanted):raise ValueError('missing_audio_metadata')
    tokens=read(WEIGHTS/'native-bundle-fp32-v1/vocabulary.json')['tokens']
    buf=io.BytesIO()
    with wave.open(buf,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(bytes(32000))
    template=make_audio_payload(buf.getvalue(),units(tokens));template['messages'][0]['content'][1]['input_audio']['data']='<MEMORY_ONLY_WAV>'
    sources=[Path(__file__),REPO/'backend/app/vaakmitra_word/local_audio_research.py',
        REPO/'backend/app/vaakmitra_word/local_lattice_sound.py',REPO/'backend/app/vaakmitra_word/reference_boundaries.py',
        REPO/'backend/app/vaakmitra_word/boundary_release.py',REPO/'backend/app/vaakmitra_word/real_adult_sound.py',
        REPO/'backend/app/vaakmitra_word/adult_sound_evidence.py',REPO/'backend/app/vaakmitra_word/focused_words.py',OLD/'protocol-final.json',
        OLD/'corrected-final/model-frozen.json',OLD/'corrected-final/development-selected-cases.json',SOURCE,LAB/'download-manifest.json']
    old_protocol=read(Path(r'C:\Users\AJEYA\VaakMitraBuildTemp\real-adult-sound-20261113\final-layer-adapters\protocol.json'))
    frozen={'requirements':['DEC078','PHN019'],'rows':rows,'cases_path':str(OLD/'corrected-final/development-selected-cases.json'),
        'model_path':str(OLD/'corrected-final/model-frozen.json'),'tokens':tokens,'metadata':metadata,'threshold_grid':GRID,
        'request_template':template,'source_hashes':{str(p):sha(p) for p in sources},
        'keyword_archives':old_protocol['source_archives'],'complete_zip_root':r'D:\VaakMitraData\raw\openslr65',
        'case_count':565,'source_count':159,'audit_inference':False,'natural_error_truth':False,'mobile_active':False,
        'model_inference':'NOT_RUN','audio_external_upload':False,'diagnostic_after_failed_smoke':DIAGNOSTIC}
    parent_sha=None
    if DIAGNOSTIC:
        parent_path=LAB/'benchmark-protocol-v3.json';parent_anchor=LAB/'freeze-v3.json'
        if sha(parent_path)!=read(parent_anchor)['protocol_sha256']:raise ValueError('parent_freeze_changed')
        parent=read(parent_path);parent_sha=sha(parent_path)
        for path,digest in parent['source_hashes'].items():
            actual=LAB/'runner-v3-frozen.py' if Path(path)==Path(__file__) else Path(path)
            if sha(actual)!=digest:raise ValueError('parent_input_identity_changed')
        for key in ['rows','cases_path','model_path','tokens','metadata','threshold_grid','request_template']:
            if frozen[key]!=parent[key]:raise ValueError('diagnostic_must_use_identical_inputs')
        if read(LAB/'smoke-results.json')['structural_audio_smoke_passed'] or read(LAB/'benchmark-result.json')['status']!='NOT_RUN_FULL_PANEL':
            raise ValueError('diagnostic_requires_preserved_failed_smoke')
        for path in [parent_path,parent_anchor,LAB/'runner-v3-frozen.py',LAB/'smoke-results.json',LAB/'benchmark-result.json']:
            frozen['source_hashes'][str(path)]=sha(path)
        frozen['parent_protocol_sha256']=parent_sha
    write(LAB/PROTOCOL_FILE,frozen)
    write(LAB/FREEZE_FILE,{'protocol_sha256':sha(LAB/PROTOCOL_FILE),'pre_review_protocol_sha256':sha(LAB/'benchmark-protocol.json'),
        'pre_inference_v2_protocol_sha256':sha(LAB/'benchmark-protocol-v2.json')})
    if DIAGNOSTIC:
        current_sha=sha(LAB/PROTOCOL_FILE)
        for path in (LAB/'observations').glob('*.json'):
            record=read(path)
            if record.pop('protocol_sha256')!=parent_sha:raise ValueError('parent_observation_identity')
            identity=record.pop('id');value=record.pop('observation');elapsed=record.pop('elapsed_seconds')
            save_observation(identity,value,elapsed,current_sha,reused_from_protocol_sha256=parent_sha,**record)
    print(json.dumps({'stage':'prepared','sources':159,'references':565,'inference':'NOT_RUN'}),flush=True)

def original_audio(protocol,selected_ids):
    metadata=protocol['metadata'];wanted={metadata[i]['audio_path']:i for i in selected_ids if i in metadata};seen=set()
    for info in protocol['keyword_archives'].values():
        if not wanted:break
        with tarfile.open(info['path']) as archive:
            for member in archive:
                identity=wanted.get(member.name)
                if identity is None:continue
                if not member.isfile() or member.size>2000000:raise ValueError('audio_member_bounds')
                raw=archive.extractfile(member).read()
                if hashlib.sha256(raw).hexdigest()!=metadata[identity]['audio_sha256']:raise ValueError('original_audio_hash')
                seen.add(identity);wanted.pop(member.name);yield identity,raw
    for row in protocol['rows']:
        if row['id'] not in selected_ids or row['id'] in metadata:continue
        gender,name=row['audio_path'].split('/')
        with zipfile.ZipFile(Path(protocol['complete_zip_root'])/('ta_in_'+gender+'.zip')) as archive:raw=archive.read(name)
        if hashlib.sha256(raw).hexdigest()!=row['audio_sha256']:raise ValueError('complete_source_hash')
        seen.add(row['id']);yield row['id'],raw
    if seen!=set(selected_ids):raise ValueError('missing_audio_rows')

def to_wav(raw):
    import numpy as np
    import soundfile as sf
    from scipy.signal import resample_poly
    values,rate=sf.read(io.BytesIO(raw),dtype='float32')
    if values.ndim!=1 or not np.isfinite(values).all():raise ValueError('invalid_source_audio')
    if rate!=16000:
        divisor=math.gcd(rate,16000);resampled=resample_poly(values,16000//divisor,rate//divisor).astype(np.float32)
        values.fill(0);values=resampled
    if not 400<=len(values)<=48000:raise ValueError('source_duration_outside_contract')
    # Transport encoding only: preserve pauses/duration; do not normalize quiet speech.
    pcm=np.round(np.clip(values,-1,1)*32767).astype('<i2');values.fill(0)
    buffer=io.BytesIO()
    with wave.open(buffer,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(pcm.tobytes())
    pcm.fill(0)
    return buffer.getvalue()

def verify_protocol(path,anchor):
    if sha(path)!=read(anchor)['protocol_sha256']:raise ValueError('protocol_freeze_changed')
    protocol=read(path)
    for path,digest in protocol['source_hashes'].items():
        if sha(path)!=digest:raise ValueError('frozen_source_changed: '+path)
    return protocol

def save_observation(identity,observation,elapsed,protocol_sha,**metadata):
    record={'id':identity,'observation':observation,'elapsed_seconds':elapsed,'protocol_sha256':protocol_sha,**metadata}
    directory=LAB/('diagnostic-observations' if DIAGNOSTIC else 'observations')
    write(directory/(hashlib.sha256(identity.encode()).hexdigest()+'.json'),record)
    return record

def load_observations(protocol_sha):
    result={}
    for path in (LAB/('diagnostic-observations' if DIAGNOSTIC else 'observations')).glob('*.json'):
        row=read(path)
        if row['protocol_sha256']!=protocol_sha or row['id'] in result:raise ValueError('resume_observation_identity')
        result[row['id']]=row
    return result

def observe_source(raw,call):
    try:wav=to_wav(raw)
    except (ValueError,RuntimeError,OSError,TypeError):
        return {'observation':{'status':'invalid_observation','phones':[]},'elapsed_seconds':0.,'reason':'audio_decode_or_contract'}
    start=time.monotonic()
    try:return {'observation':call(wav),'elapsed_seconds':time.monotonic()-start,'samples':(len(wav)-44)//2}
    finally:del wav

def smoke_ready(rows,silences,padded):
    observed=lambda v:isinstance(v,dict) and v.get('status')=='observed' and bool(v.get('phones'))
    return (len(rows)==2 and all(observed(r['observation']) and r['repeat_equal'] for r in rows) and
        len({tuple(r['observation']['phones']) for r in rows})==2 and bool(silences) and
        all(r.get('status')=='uncertain' and r.get('phones')==[] for r in silences) and
        len(padded)==2 and all(observed(r) for r in padded) and len({tuple(r['phones']) for r in padded})==2)

def pcm_wav(pcm):
    out=io.BytesIO()
    with wave.open(out,'wb') as writer:
        writer.setnchannels(1);writer.setsampwidth(2);writer.setframerate(16000);writer.writeframes(pcm)
    return out.getvalue()

def memory_snapshot(pid):
    result={'gpu_status':'unavailable','ram_status':'unavailable','scope':'whole_GPU_snapshot_not_exact_peak'}
    try:
        value=subprocess.run(['nvidia-smi','--query-gpu=memory.used,memory.total','--format=csv,noheader,nounits'],capture_output=True,text=True,check=True,timeout=10).stdout.splitlines()[0]
        used,total=map(int,value.split(','));result.update(gpu_status='measured',gpu_used_mib=used,gpu_total_mib=total)
    except (OSError,ValueError,IndexError,subprocess.SubprocessError):pass
    try:
        import psutil
        result.update(ram_status='measured',server_rss_bytes=psutil.Process(pid).memory_info().rss)
    except Exception:pass  # Optional RAM telemetry cannot turn an observation into a detection.
    return result

def select_hybrid(choices,smoke_passed,diagnostic):
    if not smoke_passed or diagnostic:return None
    eligible=[r for r in choices if r['metrics']['own_target_alerts']==r['metrics']['wrong_attributions']==0]
    return max(eligible,key=lambda r:(r['metrics']['correct_differences'],r['threshold'])) if eligible else None

def run(assets):
    from app.vaakmitra_word.local_audio_research import local_audio_request,gemma_comparison,corroborate,make_audio_payload,owned_http_request,windows_peer_owner,ENDPOINT
    from app.vaakmitra_word.real_adult_sound import units
    from app.vaakmitra_word.boundary_release import summarize_sound_cases
    protocol=verify_protocol(LAB/PROTOCOL_FILE,LAB/FREEZE_FILE);protocol_sha=sha(LAB/PROTOCOL_FILE)
    if protocol.get('diagnostic_after_failed_smoke',False)!=DIAGNOSTIC:raise ValueError('run_mode_differs_from_freeze')
    known=units(protocol['tokens']);template=make_audio_payload(pcm_wav(bytes(32000)),known)
    template['messages'][0]['content'][1]['input_audio']['data']='<MEMORY_ONLY_WAV>'
    if template!=protocol['request_template']:raise ValueError('effective_request_changed')
    plain_path(assets);assets=Path(assets).resolve();storage_guard(assets)
    result_path=LAB/('diagnostic-development-result.json' if DIAGNOSTIC else 'benchmark-result.json')
    if result_path.exists():print(json.dumps({'stage':'completed_result_already_exists'}));return
    progress=load_observations(protocol_sha);manifest=read(LAB/'download-manifest.json')
    for item in manifest['models']+manifest['runtime']:
        path=assets/item['file']
        if not path.exists() or path.stat().st_size!=item['bytes'] or sha(path)!=item['sha256']:raise ValueError('missing_or_invalid_model_runtime')
    attempt=uuid.uuid4().hex;runtime=assets/('runtime-'+attempt)
    extract_runtime([assets/item['file'] for item in manifest['runtime']],runtime)
    binaries=list(runtime.rglob('llama-server.exe'))
    if len(binaries)!=1:raise ValueError('one_pinned_server_required')
    server=binaries[0];model=assets/manifest['models'][0]['file'];projector=assets/manifest['models'][1]['file'];token=secrets.token_urlsafe(32)
    command=[str(server),'-m',str(model),'--mmproj',str(projector),'--offline','--host','127.0.0.1','--port','8769',
        '--alias','local-gemma-audio','-ngl','all','-c','4096','-np','1','--no-cache-prompt','--no-webui',
        '--log-disable','--reasoning','off','-t','4','--api-key',token]
    env=os.environ.copy();env['PATH']=str(server.parent)+os.pathsep+env.get('PATH','')
    log=(LAB/('runtime-startup-'+attempt+'.log')).open('xb');process=subprocess.Popen(command,cwd=server.parent,env=env,stdout=log,stderr=subprocess.STDOUT)
    samples=[]
    def owner(sock):
        for _ in range(3):
            if process.poll() is not None:return False
            if windows_peer_owner(sock,process.pid):return True
            time.sleep(.01)
        return False
    def call(wav):
        result=local_audio_request(wav,known,auth_token=token,owner_check=owner)
        samples.append(memory_snapshot(process.pid))
        return result
    def observation(identity,wav):
        if identity not in progress:
            start=time.monotonic();value=call(wav)
            progress[identity]=save_observation(identity,value,time.monotonic()-start,protocol_sha)
        return progress[identity]['observation']
    try:
        for _ in range(120):
            if process.poll() is not None:raise RuntimeError('local_runtime_exited_before_ready')
            try:
                owned_http_request(ENDPOINT,token,owner,health=True);break
            except OSError:time.sleep(1)
        else:raise TimeoutError('local_runtime_load_timeout')
        gpu=subprocess.run(['nvidia-smi','--query-compute-apps=pid,used_gpu_memory','--format=csv,noheader'],capture_output=True,text=True,check=True).stdout
        if str(process.pid) not in {line.split(',')[0].strip() for line in gpu.splitlines()}:raise RuntimeError('server_not_visible_as_GPU_process')
        write(LAB/('runtime-proof-'+attempt+'.json'),{'command':command[:-1]+['<REDACTED>'],'pid':process.pid,
            'runtime_files':{str(p.relative_to(runtime)):sha(p) for p in runtime.rglob('*') if p.is_file()},'gpu_processes':gpu,
            'model_sha256':manifest['models'][0]['sha256'],'projector_sha256':manifest['models'][1]['sha256'],
            'protocol_sha256':protocol_sha,'offline_flag':True,'socket_peer_ownership_checked_before_body':True,'mobile_parity':False})
        first=[r['id'] for r in protocol['rows'] if r['scope']=='complete_utterance'][:2]
        if not (LAB/'smoke-results.json').exists():
            buffers={}
            for identity,raw in original_audio(protocol,first):
                try:buffers[identity]=to_wav(raw)
                except (ValueError,RuntimeError,OSError,TypeError):
                    if identity not in progress:progress[identity]=save_observation(identity,{'status':'invalid_observation','phones':[]},0.,protocol_sha,reason='audio_decode_or_contract')
            maximum=max(((len(wav)-44)//2 for wav in buffers.values()),default=0);smoke=[];silences=[];padded=[]
            for identity,wav in buffers.items():
                primary=observation(identity,wav);repeat=observation('__repeat__'+identity,wav)
                smoke.append({'id':identity,'observation':primary,'repeat_equal':primary==repeat})
                with wave.open(io.BytesIO(wav),'rb') as source:pcm=source.readframes(source.getnframes())
                silences.append(observation('__silence__'+identity,pcm_wav(bytes(len(pcm)))))
                padded.append(observation('__equal_duration__'+identity,pcm_wav(pcm+bytes(maximum*2-len(pcm)))))
            for identity in first:
                if identity not in buffers:smoke.append({'id':identity,'observation':progress[identity]['observation'],'repeat_equal':False})
            buffers.clear();ready=smoke_ready(smoke,silences,padded)
            write(LAB/'smoke-results.json',{'sources':smoke,'duration_matched_silences':silences,'equal_duration_speech':padded,
                'structural_audio_smoke_passed':ready,'proof_of_accuracy':False,'memory_samples':samples})
        else:ready=read(LAB/'smoke-results.json')['structural_audio_smoke_passed']
        if not ready and not DIAGNOSTIC:
            write(result_path,{'status':'NOT_RUN_FULL_PANEL','reason':'structural_audio_smoke_failed',
                'adult_sources_tested':len(first),'control_requests':6,'progress_records':len(progress),'memory_samples':samples,
                'mobile_active':False,'natural_error_validated':False,'audio_uploaded_externally':False});return
        remaining=[r['id'] for r in protocol['rows'] if r['id'] not in progress]
        for identity,raw in original_audio(protocol,remaining):
            storage_guard(assets);row=observe_source(raw,call)
            progress[identity]=save_observation(identity,row.pop('observation'),row.pop('elapsed_seconds'),protocol_sha,**row)
            del raw
            print(json.dumps({'stage':'observations','done':sum(r['id'] in progress for r in protocol['rows']),'total':len(protocol['rows'])}),flush=True)
        observations={r['id']:progress[r['id']]['observation'] for r in protocol['rows']}
        cases=read(protocol['cases_path']);model=read(protocol['model_path']);validate_case_rows(protocol['rows'],cases)
        metrics=lambda rows,key:summarize_sound_cases(rows,key)
        for row in cases:
            value=observations[row['id']];valid=row['fit_valid'];row['phoneme_only']=row['candidate']
            row['gemma_only']=gemma_comparison(row['reference'],value,row['scope']) if valid else {'status':'outside_input_contract'}
            for threshold in GRID:row[str(threshold)]=corroborate(row['evidence'],model,value,threshold) if valid else {'status':'outside_input_contract'}
        choices=[{'threshold':threshold,'metrics':metrics(cases,str(threshold))} for threshold in GRID]
        chosen=select_hybrid(choices,ready,DIAGNOSTIC)
        keys=['phoneme_only','gemma_only']+([str(v) for v in GRID] if DIAGNOSTIC else [str(chosen['threshold'])] if chosen else [])
        result={'status':'DIAGNOSTIC_AFTER_FAILED_SMOKE' if DIAGNOSTIC else 'DEVELOPMENT_ONLY',
            'structural_audio_smoke_passed':ready,'eligible_for_selection':not DIAGNOSTIC and ready,
            'phoneme_only':metrics(cases,'phoneme_only'),'gemma_only':metrics(cases,'gemma_only'),
            'choices':choices,'chosen':chosen,'sources':159,'references':565,'natural_error_validated':False,
            'clinical_assessment':False,'mobile_active':False,'android_parity':'NOT_RUN','memory_samples':samples,
            'observation_statuses':dict(collections.Counter(r['status'] for r in observations.values())),
            'benchmark_source_timings':{r['id']:progress[r['id']]['elapsed_seconds'] for r in protocol['rows']},
            'benchmark_source_request_seconds':sum(progress[r['id']]['elapsed_seconds'] for r in protocol['rows']),
            'timing_source_denominator':159,'control_requests_excluded_from_source_timing':True,
            'audio_uploaded_externally':False,'audio_files_written':False,'audit_inference':False}
        result['scope_metrics']={scope:{key:metrics([r for r in cases if r['scope']==scope],key) for key in keys} for scope in ['keyword','complete_utterance']}
        result['keyword_strata']={name:{key:metrics([r for r in cases if r['scope']=='keyword' and (r['truth'] is None or r['interior']==interior)],key) for key in keys} for name,interior in [('interior',True),('edge',False)]}
        compact=[{'index':i,'id':r['id'],**{key:r[key] for key in keys}} for i,r in enumerate(cases)]
        write(LAB/('diagnostic-matched-outputs.json' if DIAGNOSTIC else 'matched-outputs.json'),{'source_cases_sha256':sha(protocol['cases_path']),'rows':compact})
        write(result_path,result)
        print(json.dumps({'stage':'development_complete','chosen':chosen,'mobile_active':False}),flush=True)
    except Exception as exc:
        write(LAB/('incomplete-attempt-'+attempt+'.json'),{'status':'INCOMPLETE','error_type':type(exc).__name__,
            'completed_source_observations':sum(r['id'] in progress for r in protocol['rows']),
            'required_sources':159,'protocol_sha256':protocol_sha,'memory_samples':samples,'mobile_active':False})
        raise
    finally:
        if process.poll() is None:
            process.terminate()
            try:process.wait(timeout=15)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=5)
        log.close()

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf8')
    parser=argparse.ArgumentParser();parser.add_argument('phase',choices=['prepare','download','run']);parser.add_argument('--assets',type=Path)
    parser.add_argument('--diagnostic-after-failed-smoke',action='store_true')
    args=parser.parse_args()
    DIAGNOSTIC=args.diagnostic_after_failed_smoke
    if args.phase=='prepare':prepare()
    elif args.assets is None:parser.error('--assets is required for download/run')
    elif args.phase=='download':download_assets(args.assets,read(LAB/'download-manifest.json'))
    else:run(args.assets)
