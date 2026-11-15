"""DEC078/PHN019: inactive public-adult local-audio benchmark contracts.

No product route imports this module. Model agreement is research evidence,
not correctness, and never grants child, clinical or mobile qualification.
"""
import base64
import copy
import ctypes
import http.client
import io
import json
import math
import re
import socket
import struct
import sys
import urllib.error
import urllib.request
import wave

ENDPOINT='http://127.0.0.1:8769/v1/chat/completions'
GRID=(.5,.7,.8,.9,.95,.98,.99)
KINDS={'possible_omission','possible_substitution'}
MAX_RESPONSE=64*1024


def validate_endpoint(endpoint):
    match=re.fullmatch(r'http://127\.0\.0\.1:([1-9][0-9]{3,4})/v1/chat/completions',endpoint) if isinstance(endpoint,str) else None
    if not match or not 1024<=int(match[1])<=65535:raise ValueError('literal_loopback_only')
    return endpoint


def _check_units(units):
    if (not isinstance(units,(list,tuple)) or not 1<=len(units)<=80 or len(set(units))!=len(units) or
        any(not isinstance(u,str) or not 1<=len(u)<=16 or u.startswith('<') or u.startswith('[') for u in units)):
        raise ValueError('invalid_canonical_units')


def make_audio_payload(wav_bytes,units):
    _check_units(units)
    if not isinstance(wav_bytes,bytes) or len(wav_bytes)>200000:raise ValueError('bounded_wav_required')
    try:
        with wave.open(io.BytesIO(wav_bytes),'rb') as source:
            if (source.getnchannels()!=1 or source.getframerate()!=16000 or source.getsampwidth()!=2 or
                not 400<=source.getnframes()<=48000 or source.getcomptype()!='NONE'):
                raise ValueError('audio_contract')
            if len(source.readframes(source.getnframes()))!=source.getnframes()*2:raise ValueError('truncated_audio')
    except (wave.Error,EOFError) as exc:raise ValueError('invalid_wav') from exc
    prompt=('Listen to the audio. Report the actual pronounced Tamil phone sequence, not the word you think was intended. '
            'Do not repair pronunciation, infer missing sounds, or convert a guessed spelling into phones. '
            'Preserve repeated consonants and vowel length. Use only these canonical IPA units: '+json.dumps(list(units),ensure_ascii=False)+'. '
            'Use <unk> for an unidentifiable sound. If you cannot reliably transcribe actual phones, return '
            '{"status":"uncertain","phones":[]}. Otherwise return {"status":"observed","phones":[...]} only. '
            'Silence or non-speech must be uncertain. Do not output a transcript, explanation or score.')
    schema={'type':'object','properties':{'status':{'type':'string','enum':['observed','uncertain']},
        'phones':{'type':'array','items':{'type':'string','enum':list(units)+['<unk>']},'maxItems':96}},
        'required':['status','phones'],'additionalProperties':False}
    return {'model':'local-gemma-audio','temperature':0,'seed':20261114,'max_tokens':384,'stream':False,
        'chat_template_kwargs':{'enable_thinking':False},
        'response_format':{'type':'json_schema','json_schema':{'name':'actual_phones','strict':True,'schema':schema}},
        'messages':[{'role':'user','content':[{'type':'text','text':prompt},
            {'type':'input_audio','input_audio':{'data':base64.b64encode(wav_bytes).decode('ascii'),'format':'wav'}}]}]}


def _unique_object(pairs):
    result={}
    for key,value in pairs:
        if key in result:raise ValueError('duplicate_json_key')
        result[key]=value
    return result


def parse_observation(raw,units):
    bad={'status':'invalid_observation','phones':[]}
    try:
        _check_units(units)
        if not isinstance(raw,str) or len(raw.encode('utf8'))>16384:return bad
        obj=json.loads(raw,object_pairs_hook=_unique_object)
        if not isinstance(obj,dict) or set(obj)!={'status','phones'}:return bad
        phones=obj['phones'];status=obj['status']
        if not isinstance(status,str) or status not in {'observed','uncertain'} or not isinstance(phones,list) or len(phones)>96:return bad
        if any(not isinstance(p,str) or p not in set(units)|{'<unk>'} for p in phones):return bad
        if status=='uncertain':return {'status':'uncertain','phones':[]} if not phones else bad
        if not phones:return bad
        if '<unk>' in phones:return {'status':'uncertain','phones':phones.copy()}
        return {'status':'observed','phones':phones.copy()}
    except (ValueError,TypeError,UnicodeError,RecursionError):return bad


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):return None


def parse_completion(body,units):
    try:
        choices=body['choices']
        if not isinstance(choices,list) or len(choices)!=1 or choices[0].get('finish_reason')!='stop':raise ValueError()
        return parse_observation(choices[0]['message']['content'],units)
    except (KeyError,IndexError,TypeError,ValueError,AttributeError):
        return {'status':'invalid_observation','phones':[],'reason':'incomplete_completion_envelope'}


def tcp_peer_matches(rows,client,peer,pid):
    return any(r['state']==5 and r['pid']==pid and r['local']==peer and r['remote']==client for r in rows)


def windows_peer_owner(sock,pid):
    """Bind the established TCP socket before transmitting headers or PCM.

    The server-side established tuple, not a separate listening-port probe,
    prevents a different process taking over the port between check and send.
    """
    if sys.platform!='win32':return False
    class Row(ctypes.Structure):
        _fields_=[(name,ctypes.c_uint32) for name in ['state','local_addr','local_port','remote_addr','remote_port','pid']]
    try:
        query=ctypes.WinDLL('iphlpapi').GetExtendedTcpTable
        query.argtypes=[ctypes.c_void_p,ctypes.POINTER(ctypes.c_uint32),ctypes.c_bool,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32]
        query.restype=ctypes.c_uint32;size=ctypes.c_uint32(0)
        if query(None,ctypes.byref(size),False,2,5,0) not in (0,122):return False
        for _ in range(4):
            if not 4<=size.value<=16*1024**2:return False
            buffer=ctypes.create_string_buffer(size.value);result=query(buffer,ctypes.byref(size),False,2,5,0)
            if result==122:continue
            if result!=0:return False
            count=ctypes.c_uint32.from_buffer(buffer).value
            if 4+count*ctypes.sizeof(Row)>len(buffer):return False
            rows=[]
            for index in range(count):
                row=Row.from_buffer_copy(buffer,4+index*ctypes.sizeof(Row))
                address=lambda value:socket.inet_ntoa(struct.pack('=I',value))
                rows.append({'state':row.state,'pid':row.pid,
                    'local':(address(row.local_addr),socket.ntohs(row.local_port&65535)),
                    'remote':(address(row.remote_addr),socket.ntohs(row.remote_port&65535))})
            return tcp_peer_matches(rows,sock.getsockname(),sock.getpeername(),pid)
        return False
    except (OSError,ValueError,TypeError,AttributeError):return False


def owned_http_request(endpoint,auth_token,owner_check,body=None,health=False):
    validate_endpoint(endpoint)
    if not isinstance(auth_token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{32,128}',auth_token) or not callable(owner_check):
        raise ValueError('authenticated_process_binding_required')
    port=int(endpoint.split(':')[2].split('/')[0])
    connection=http.client.HTTPConnection('127.0.0.1',port,timeout=120)
    try:
        connection.connect()
        if not owner_check(connection.sock):raise PermissionError('connected_socket_owner_mismatch')
        connection.request('GET' if health else 'POST','/health' if health else '/v1/chat/completions',body=body,
            headers={'Content-Type':'application/json','Authorization':'Bearer '+auth_token})
        response=connection.getresponse();raw=response.read(MAX_RESPONSE+1)
        if response.status!=200 or len(raw)>MAX_RESPONSE:raise OSError('invalid_local_http_response')
        return raw
    finally:connection.close()


def local_audio_request(wav_bytes,units,endpoint=ENDPOINT,*,auth_token=None,owner_check=None):
    validate_endpoint(endpoint)
    payload=make_audio_payload(wav_bytes,units)
    try:
        raw=owned_http_request(endpoint,auth_token,owner_check,json.dumps(payload,ensure_ascii=False).encode('utf8'))
        body=json.loads(raw,object_pairs_hook=_unique_object)
        return parse_completion(body,units)
    except (http.client.HTTPException,OSError,ValueError,KeyError,IndexError,TypeError,RecursionError):
        return {'status':'invalid_observation','phones':[],'reason':'local_request_failed'}
    finally:
        payload.clear()


def _neutral(status='insufficient_evidence'):
    return {'status':status,'expected_sounds':[],'alternative_sounds':[],'confirmed':False,
        'clinical_assessment':False,'approved_for_child_scoring':False,'mobile_active':False}


def gemma_comparison(reference,observation,scope):
    from .reference_boundaries import word_windows
    if isinstance(observation,dict) and observation.get('status')=='invalid_observation':return _neutral('invalid_observation')
    if (not isinstance(observation,dict) or observation.get('status')!='observed' or
        not isinstance(observation.get('phones'),list) or not 1<=len(observation['phones'])<=96 or
        any(not isinstance(p,str) or p.startswith('<') or p.startswith('[') for p in observation['phones'])):
        return _neutral()
    result=word_windows(reference,observation['phones'],scope)
    if result['status']!='candidates':return _neutral(result['status'])
    placements={(r['start'],r['end'],tuple(r['reference'])) for r in result['candidates']}
    if len(placements)!=1:return _neutral('ambiguous_placement')
    signatures={(r['kind'],tuple(r['expected_sounds']),tuple(r['alternative_sounds'])) for r in result['candidates']}
    if len(signatures)!=1:return _neutral('ambiguous_placement')
    kind,expected,alternative=signatures.pop()
    return dict(_neutral(kind),expected_sounds=list(expected),alternative_sounds=list(alternative))


def corroborate(evidence,model,observation,threshold):
    from .local_lattice_sound import apply_lattice_gate
    from .real_adult_sound import units
    if type(threshold) not in (float,int) or not math.isfinite(threshold) or threshold not in GRID:return _neutral('invalid_model')
    candidate=copy.deepcopy(model)
    if not isinstance(candidate,dict):return _neutral('invalid_model')
    candidate['threshold']=threshold
    result=apply_lattice_gate(evidence,candidate)
    if result['status'] not in KINDS:return result
    try:
        parsed=parse_observation(json.dumps(observation,ensure_ascii=False),units(evidence['tokens']))
        if parsed['status']!='observed' or parsed['phones']!=evidence['alternative_full']:return _neutral()
    except (KeyError,TypeError,ValueError):return _neutral()
    return dict(result,corroborated=True,confirmed=False,mobile_active=False)
