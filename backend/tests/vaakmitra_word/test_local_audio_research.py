"""DEC078/PHN019: public-adult research; no product/audio-cloud path."""
import copy
import io
import json
import wave
import pytest
from app.vaakmitra_word.local_audio_research import (
    validate_endpoint, make_audio_payload, parse_observation, gemma_comparison,
    corroborate, local_audio_request,
)

UNITS=['a','aː','m','p','k','s','j']

def wav():
    data=io.BytesIO()
    with wave.open(data,'wb') as out:
        out.setnchannels(1);out.setsampwidth(2);out.setframerate(16000);out.writeframes(bytes(1600))
    return data.getvalue()

@pytest.mark.parametrize('url',[
    'https://example.com/v1/chat/completions','http://localhost:8769/v1/chat/completions',
    'http://127.0.0.1.evil:8769/v1/chat/completions','http://127.0.0.1:8769/v1/chat/completions?url=evil',
    'http://user@127.0.0.1:8769/v1/chat/completions','http://127.0.0.1:80/v1/chat/completions',
    'http://127.0.0.1:8769/v1/chat/completions\n',
])
def test_phn019_only_literal_loopback(url):
    with pytest.raises(ValueError):validate_endpoint(url)

def test_phn019_payload_is_target_blind_and_keeps_uncertainty():
    payload=make_audio_payload(wav(),UNITS)
    assert payload['temperature']==0 and payload['seed']==20261114
    content=payload['messages'][0]['content']
    assert content[1]['type']=='input_audio'
    assert 'expected_word' not in json.dumps(payload)
    assert 'uncertain' in content[0]['text'] and 'actual' in content[0]['text']
    assert payload['response_format']['type']=='json_schema'
    with pytest.raises(ValueError):make_audio_payload(b'not wav',UNITS)

@pytest.mark.parametrize('raw',[
    '{"status":"observed","phones":["a"],"transcript":"Amma"}',
    '{"status":"PASS","phones":["a"]}',
    '{"status":"observed","phones":["x"]}',
    '{"status":"observed","phones":[]}',
    '{"status":"uncertain","phones":["m"]}',
    '{"status":"observed","phones":["a"],"status":"uncertain"}',
    '```json\n{"status":"observed","phones":["a"]}\n```',
])
def test_phn019_invalid_outputs_never_become_phonetic_evidence(raw):
    assert parse_observation(raw,UNITS)['status']=='invalid_observation'

def test_phn019_unknown_abstains_without_collapsing_doubles_or_length():
    assert parse_observation('{"status":"observed","phones":["a","<unk>"]}',UNITS)['status']=='uncertain'
    value=parse_observation('{"status":"observed","phones":["a","m","m","aː"]}',UNITS)
    assert value['phones']==['a','m','m','aː']

def test_phn019_comparison_scopes_edges_and_sound_identity():
    value={'status':'observed','phones':['k','a','p','a','s']}
    result=gemma_comparison(['a','m','a'],value,'keyword')
    assert result['status']=='possible_substitution' and result['expected_sounds']==['m'] and result['alternative_sounds']==['p']
    assert gemma_comparison(['a','m','a'],{'status':'observed','phones':['a','a']},'complete_utterance')['status']=='possible_omission'
    assert gemma_comparison(['a','m'],{'status':'observed','phones':['a','p']},'keyword')['status']=='boundary_uncertain'
    assert gemma_comparison(['a','m','a'],{'status':'observed','phones':['k','a','m','a','s']},'keyword')['status']=='sequence_supported'
    assert gemma_comparison(['a','m','a'],value,'complete_utterance')['status']!='possible_substitution'

def test_phn019_model_corroboration_keeps_raw_and_existing_body_gate():
    from app.vaakmitra_word.local_lattice_sound import MODEL_SCHEMA,lattice_feature_names
    tokens=['<blank>','a','m','p','k','s','j','[UNK]']; names=lattice_feature_names(tokens);n=len(names)
    e={'status':'proposal','body_id':'b'*64,'tokens':tokens,'scope':'complete_utterance','feature_names':names,
       'features':[0.]*n,'kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['p'],
       'alternative_full':['a','p','a'],'raw_phones':['a','k','a']}
    m={'schema':MODEL_SCHEMA,'reference_policy':'partial_keyword_v2','body_id':'b'*64,'tokens':tokens,'feature_names':names,
       'mean':[0.]*n,'scale':[1.]*n,'w1':[[0.]*n for _ in range(16)],'b1':[0.]*16,'w2':[0.]*16,'b2':2.,'threshold':.99,
       'trained_scopes':['complete_utterance'],'trained_contrasts':[{'scope':'complete_utterance','kind':'possible_substitution','expected_sounds':['m'],'alternative_sounds':['p']}],
       'approved_for_child_scoring':False,'clinical_assessment':False}
    before=copy.deepcopy((e,m));obs={'status':'observed','phones':['a','p','a']}
    assert corroborate(e,m,obs,.7)['status']=='possible_substitution'
    assert corroborate(e,m,obs,.99)['status']=='insufficient_evidence'
    assert corroborate(e,m,{'status':'observed','phones':['a','m','a']},.7)['status']=='insufficient_evidence'
    broken=copy.deepcopy(m);broken['body_id']='c'*64
    assert corroborate(e,broken,obs,.7)['status']=='invalid_model'
    assert (e,m)==before
    assert corroborate({'status':'possible_substitution'},m,obs,.7)['status']=='invalid_evidence'

def test_phn019_client_disables_proxy_and_redirect_and_bounds_output(monkeypatch):
    from app.vaakmitra_word import local_audio_research as module
    events=[]
    class Response:
        status=200
        def read(self,n):return b'{"choices":[{"finish_reason":"stop","message":{"content":"{\\"status\\":\\"uncertain\\",\\"phones\\":[]}"}}]}'
    class Connection:
        sock=object()
        def __init__(self,host,port,timeout):assert host=='127.0.0.1' and port==8769 and timeout==120
        def connect(self):events.append('connect')
        def request(self,*args,**kwargs):events.append('send');assert kwargs['headers']['Authorization']=='Bearer '+('a'*40)
        def getresponse(self):return Response()
        def close(self):events.append('close')
    monkeypatch.setattr(module.http.client,'HTTPConnection',Connection)
    monkeypatch.setattr(module.urllib.request,'urlopen',lambda *a,**k:pytest.fail('proxy-capable client used'))
    def owner(sock):events.append('owner');return True
    assert local_audio_request(wav(),UNITS,auth_token='a'*40,owner_check=owner)['status']=='uncertain'
    assert events==['connect','owner','send','close']
    events.clear()
    assert local_audio_request(wav(),UNITS,auth_token='a'*40,owner_check=lambda sock:False)['status']=='invalid_observation'
    assert events==['connect','close']

@pytest.mark.parametrize('envelope',[
    {'choices':[{'finish_reason':'length','message':{'content':'{"status":"observed","phones":["a"]}'}}]},
    {'choices':[{'message':{'content':'{"status":"observed","phones":["a"]}'}}]},
    {'choices':[{'finish_reason':'stop','message':{'content':'{"status":"observed","phones":["a"]}'}}]*2},
])
def test_phn019_incomplete_or_multiple_completions_are_invalid(envelope):
    from app.vaakmitra_word.local_audio_research import parse_completion
    assert parse_completion(envelope,UNITS)['status']=='invalid_observation'

def test_phn019_two_keyword_occurrences_are_not_one_sound_identity():
    obs={'status':'observed','phones':['a','p','a','s','s','a','p','a']}
    assert gemma_comparison(['a','m','a'],obs,'keyword')['status']=='ambiguous_placement'

def test_phn019_tcp_owner_must_match_established_reverse_tuple():
    from app.vaakmitra_word.local_audio_research import tcp_peer_matches
    row={'local':('127.0.0.1',8769),'remote':('127.0.0.1',50001),'pid':123,'state':5}
    assert tcp_peer_matches([row],('127.0.0.1',50001),('127.0.0.1',8769),123)
    assert not tcp_peer_matches([row],('127.0.0.1',50001),('127.0.0.1',8769),124)
    assert not tcp_peer_matches([row],('127.0.0.1',50002),('127.0.0.1',8769),123)
    assert not tcp_peer_matches([dict(row,state=2)],('127.0.0.1',50001),('127.0.0.1',8769),123)

def test_phn019_freeze_detects_protocol_edit_before_inference(tmp_path):
    module=runner();source=tmp_path/'source';source.write_text('pinned')
    protocol=tmp_path/'p.json';protocol.write_text(json.dumps({'source_hashes':{str(source):module.sha(source)},'rows':[]}))
    anchor=tmp_path/'f.json';anchor.write_text(json.dumps({'protocol_sha256':module.sha(protocol)}))
    module.verify_protocol(protocol,anchor)
    protocol.write_text(json.dumps({'source_hashes':{},'rows':[{'id':'changed'}]}))
    with pytest.raises(ValueError):module.verify_protocol(protocol,anchor)

@pytest.mark.parametrize('silence',[{'status':'observed','phones':['a']},{'status':'invalid_observation','phones':[]}])
def test_phn019_smoke_cannot_ignore_silence(silence):
    module=runner()
    assert not module.smoke_ready([{'observation':{'status':'observed','phones':['a']},'repeat_equal':True},
        {'observation':{'status':'observed','phones':['m']},'repeat_equal':True}],
        [silence], [{'status':'observed','phones':['a']},{'status':'observed','phones':['m']}])

def test_phn019_atomic_output_cap_and_progress_binding(tmp_path,monkeypatch):
    module=runner();monkeypatch.setattr(module,'LAB',tmp_path);monkeypatch.setattr(module,'OUTPUT_CAP',10)
    with pytest.raises(OSError):module.write(tmp_path/'big.json',{'large':'x'*100})
    assert not list(tmp_path.iterdir())
    monkeypatch.setattr(module,'OUTPUT_CAP',100000)
    module.save_observation('clip',{'status':'uncertain','phones':[]},.3,'a'*64)
    assert module.load_observations('a'*64)['clip']['elapsed_seconds']==.3
    with pytest.raises(ValueError):module.load_observations('b'*64)

def test_phn019_existing_runtime_tree_is_rejected(tmp_path):
    import zipfile
    module=runner();archive=tmp_path/'ok.zip'
    with zipfile.ZipFile(archive,'w') as out:out.writestr('safe.dll','valid')
    destination=tmp_path/'runtime';destination.mkdir();(destination/'extra.dll').write_text('unknown')
    with pytest.raises(ValueError):module.extract_runtime(archive,destination)

def test_phn019_hash_verified_bad_audio_is_a_neutral_source_failure():
    module=runner()
    result=module.observe_source(b'undecodable',lambda data:pytest.fail('invalid audio sent'))
    assert result['observation']['status']=='invalid_observation'
    assert result['reason']=='audio_decode_or_contract'

def test_phn019_download_resumes_exact_pinned_bytes(monkeypatch,tmp_path):
    import hashlib
    module=runner();monkeypatch.setattr(module,'LAB',tmp_path)
    monkeypatch.setattr(module.shutil,'disk_usage',lambda path:type('Disk',(),{'free':12*1024**3})())
    (tmp_path/'model.gguf.partial').write_bytes(b'ab')
    class Reply:
        status=206;headers={'Content-Range':'bytes 2-3/4'};remaining=b'cd'
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def read(self,n):data=self.remaining;self.remaining=b'';return data
    def fetch(request,timeout):assert request.get_header('Range')=='bytes=2-';return Reply()
    monkeypatch.setattr(module.urllib.request,'urlopen',fetch)
    manifest={'initial_free_required':8*1024**3,'post_download_reserve':2*1024**3,'runtime':[],
        'models':[{'file':'model.gguf','bytes':4,'sha256':hashlib.sha256(b'abcd').hexdigest(),'url':'https://example.invalid/model'}]}
    module.download_assets(tmp_path,manifest)
    assert (tmp_path/'model.gguf').read_bytes()==b'abcd'

def test_phn019_real_windows_connected_socket_ownership():
    import os,sys,threading,time
    from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
    from app.vaakmitra_word.local_audio_research import windows_peer_owner
    if sys.platform!='win32':pytest.skip('Windows peer-ownership implementation')
    requests=[]
    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            requests.append(self.rfile.read(int(self.headers['Content-Length'])))
            body=b'{"choices":[{"finish_reason":"stop","message":{"content":"{\\"status\\":\\"uncertain\\",\\"phones\\":[]}"}}]}'
            self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
        def log_message(self,*args):pass
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    def owner(sock):
        for _ in range(5):
            if windows_peer_owner(sock,os.getpid()):return True
            time.sleep(.01)
        return False
    try:
        endpoint=f'http://127.0.0.1:{server.server_address[1]}/v1/chat/completions'
        assert local_audio_request(wav(),UNITS,endpoint,auth_token='a'*40,owner_check=owner)['status']=='uncertain'
        assert len(requests)==1
        assert local_audio_request(wav(),UNITS,endpoint,auth_token='a'*40,owner_check=lambda sock:windows_peer_owner(sock,os.getpid()+100000))['status']=='invalid_observation'
        assert len(requests)==1
    finally:server.shutdown();server.server_close();thread.join(timeout=2)

def test_phn019_run_passes_verified_archive_paths_to_extraction(monkeypatch,tmp_path):
    module=runner();monkeypatch.setattr(module,'LAB',tmp_path)
    monkeypatch.setattr(module,'storage_guard',lambda *a,**k:None)
    from app.vaakmitra_word.local_audio_research import make_audio_payload
    from app.vaakmitra_word.real_adult_sound import units
    tokens=['<blank>','a','m','p'];template=make_audio_payload(module.pcm_wav(bytes(32000)),units(tokens))
    template['messages'][0]['content'][1]['input_audio']['data']='<MEMORY_ONLY_WAV>'
    protocol={'tokens':tokens,'request_template':template}
    monkeypatch.setattr(module,'verify_protocol',lambda *a:protocol)
    (tmp_path/getattr(module,'PROTOCOL_FILE','benchmark-protocol-v2.json')).write_text('{}')
    assets=tmp_path/'assets';assets.mkdir();items=[]
    for name in ['model.gguf','projector.gguf','first.zip','second.zip']:
        path=assets/name;path.write_bytes(b'pinned');items.append({'file':name,'bytes':6,'sha256':module.sha(path)})
    (tmp_path/'download-manifest.json').write_text(json.dumps({'models':items[:2],'runtime':items[2:]}))
    def boundary(paths,destination):
        assert paths==[assets/'first.zip',assets/'second.zip']
        raise RuntimeError('verified_extraction_boundary_reached')
    monkeypatch.setattr(module,'extract_runtime',boundary)
    with pytest.raises(RuntimeError,match='verified_extraction_boundary_reached'):module.run(assets)

def test_phn019_failed_smoke_diagnostic_never_selects_winner():
    module=runner()
    choices=[{'threshold':.99,'metrics':{'own_target_alerts':0,'wrong_attributions':0,'correct_differences':100}}]
    assert module.select_hybrid(choices,smoke_passed=True,diagnostic=False)==choices[0]
    assert module.select_hybrid(choices,smoke_passed=False,diagnostic=False) is None
    assert module.select_hybrid(choices,smoke_passed=False,diagnostic=True) is None
    assert module.select_hybrid(choices,smoke_passed=True,diagnostic=True) is None

def runner():
    import importlib.util
    from pathlib import Path
    spec=importlib.util.spec_from_file_location('gemma_benchmark',Path(__file__).parents[3]/'scripts/model/benchmark_local_audio.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    return module

def test_phn019_freeze_keeps_all_source_ids_and_denominators():
    module=runner()
    rows=[{'id':'one','references':[{'reference':['a'],'truth':None,'interior':True}]}]
    cases=[{'id':'one','reference':['a'],'truth':None,'interior':True}]
    module.validate_case_rows(rows,cases)
    with pytest.raises(ValueError):module.validate_case_rows(rows,[])
    with pytest.raises(ValueError):module.validate_case_rows(rows,cases+cases)
    changed=copy.deepcopy(cases);changed[0]['reference']=['p']
    with pytest.raises(ValueError):module.validate_case_rows(rows,changed)

def test_phn019_download_is_blocked_before_any_network_or_model_write(monkeypatch,tmp_path):
    module=runner()
    monkeypatch.setattr(module.shutil,'disk_usage',lambda path:type('Disk',(),{'free':1024})())
    monkeypatch.setattr(module.urllib.request,'urlopen',lambda *a,**k:pytest.fail('download before reserve'))
    with pytest.raises(OSError):module.download_assets(tmp_path,{'initial_free_required':8*1024**3,'models':[],'runtime':[]})
    assert not list(tmp_path.iterdir())

def test_phn019_archive_cannot_escape_research_runtime(tmp_path):
    import zipfile
    module=runner();archive=tmp_path/'hostile.zip'
    with zipfile.ZipFile(archive,'w') as out:out.writestr('../escape.txt','no')
    with pytest.raises(ValueError):module.extract_runtime(archive,tmp_path/'runtime')
    assert not (tmp_path/'escape.txt').exists()

def test_phn019_storage_probe_accepts_a_not_yet_created_asset_folder(monkeypatch,tmp_path):
    module=runner();seen=[]
    def probe(path):
        from pathlib import Path
        candidate=Path(path);seen.append(candidate)
        assert candidate.exists() or str(candidate) in {'C:', 'C:\\', 'C:/', 'D:', 'D:\\', 'D:/'}
        return type('Disk',(),{'free':12*1024**3})()
    monkeypatch.setattr(module.shutil,'disk_usage',probe)
    module.storage_guard(tmp_path/'not-created'/'assets')
    assert not (tmp_path/'not-created').exists()
