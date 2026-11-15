"""DEC068/PHN008..009: transient target-free local phoneme inference and help."""
from dataclasses import dataclass
import hashlib
from pathlib import Path
import numpy as np
import onnxruntime as ort
from .phoneme_decoder import decode_logits
from .phonetic_support import choose_phonetic_support

DECODER={'type':'ctc_prefix_beam','beam_width':5,'nonblank_top_k':8}
COMPOUNDS={'aj':('a','j'),'aʋ':('a','ʋ'),'kʂ':('k','ʂ')}


def valid_frames(samples):
    if type(samples)is not int or not 400<=samples<=48000:raise ValueError('Unsupported acoustic length')
    result=samples
    for kernel,stride in zip((10,3,3,3,3,2,2),(5,2,2,2,2,2,2)):result=(result-kernel)//stride+1
    return result


def decode_native_phones(logits,tokens):
    if len(tokens)!=39 or len(set(tokens))!=39 or tokens[0]!='<blank>':raise ValueError('Invalid backbone vocabulary')
    if logits.ndim!=2 or logits.shape[1]!=39 or not 1<=len(logits)<=149 or not np.isfinite(logits).all():
        raise ValueError('Invalid native logits')
    decoded=decode_logits(logits,DECODER)
    # Word separators disappear only after CTC, never collapse phone doubles twice.
    return tuple(unit for i in decoded if tokens[i]!='|'for unit in COMPOUNDS.get(tokens[i],(tokens[i],)))


@dataclass(frozen=True)
class PhonemeObservation:
    phones:tuple[str,...]
    valid_frames:int
    model_sha256:str
    supported:bool


class OnnxPhonemeRuntime:
    def __init__(self,model,tokens,*,expected_sha256,engineering_qualified=False):
        path=Path(model);digest=hashlib.sha256()
        with path.open('rb')as source:
            for block in iter(lambda:source.read(1024*1024),b''):digest.update(block)
        if digest.hexdigest()!=expected_sha256:raise ValueError('Acoustic model hash differs')
        if len(tokens)!=39 or len(set(tokens))!=39 or tokens[0]!='<blank>':raise ValueError('Invalid native vocabulary')
        self.tokens=tuple(tokens);self.model_sha256=expected_sha256;self.engineering_qualified=bool(engineering_qualified)
        self.known=frozenset(u for p in tokens for u in COMPOUNDS.get(p,(p,)))
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        options.enable_mem_pattern=False;options.enable_cpu_mem_arena=False
        options.add_session_config_entry('session.intra_op.allow_spinning','0')
        self.session=ort.InferenceSession(str(path),options,providers=['CPUExecutionProvider'])
        inputs={i.name:i for i in self.session.get_inputs()};outputs=self.session.get_outputs()
        if set(inputs)!={'waveform','attention_mask'} or len(outputs)!=1 or outputs[0].name!='logits':
            raise ValueError('Unexpected backbone input/output names')
        if inputs['waveform'].type!='tensor(float)'or inputs['attention_mask'].type!='tensor(int64)':
            raise ValueError('Unexpected backbone input dtypes')
        if any(len(i.shape)!=2 or i.shape[0]!=1 or not isinstance(i.shape[1],str)for i in inputs.values()):
            raise ValueError('Backbone requires dynamic batch1 audio/mask')
        output=outputs[0].shape
        if len(output)!=3 or (output[0]!=1 and not isinstance(output[0],str)) or output[2]!=39 or not isinstance(output[1],str):
            raise ValueError('Unexpected native output shape')

    def infer(self,samples):
        """Normalized actual audio only; caller retains and erases its original PCM."""
        wave=np.asarray(samples,dtype=np.float32)
        if wave.ndim!=1 or not np.isfinite(wave).all():raise ValueError('Finite mono audio required')
        frames=valid_frames(len(wave))
        values=np.ascontiguousarray(((wave-wave.mean())/np.sqrt(wave.var()+1e-7))[None,:],dtype=np.float32)
        mask=np.ones(values.shape,dtype=np.int64);logits=None
        try:
            logits=self.session.run(['logits'],{'waveform':values,'attention_mask':mask})[0]
            if logits.shape!=(1,frames,39):raise ValueError('Real acoustic frame count differs')
            phones=decode_native_phones(logits[0],self.tokens)
            supported=bool(phones)and all(p not in ('[UNK]','்','<blank>','[PAD]')for p in phones)
            return PhonemeObservation(phones,frames,self.model_sha256,supported)
        finally:
            values.fill(0);mask.fill(0)
            if logits is not None:logits.fill(0)

    def support(self,observation,reference,*,capture_valid=False,**constraints):
        """Reference comparison follows inference; no raw phones enter reports."""
        # Familiar token names establish lexical support, not acoustic confidence.
        # No target-independent uncertainty rule has been calibrated for this preview.
        valid=False
        return choose_phonetic_support(observation.phones,reference,known_tokens=self.known,
            evidence_valid=valid,model_qualified=self.engineering_qualified,**constraints)

    def close(self):self.session=None
    def __enter__(self):return self
    def __exit__(self,*_):self.close()
