"""DEC075/PHN016: small ONNX variants sharing authenticated immutable weight bytes."""
from pathlib import Path,PurePosixPath
import hashlib,mmap

def _sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()

def _varint(buf,pos,end):
    value=0
    for shift in range(0,70,7):
        if pos>=end:raise ValueError('Truncated protobuf integer')
        byte=buf[pos];pos+=1;value|=(byte&127)<<shift
        if byte<128:return value,pos
    raise ValueError('Unbounded protobuf integer')

def _fields(buf,start,end):
    pos=start
    while pos<end:
        tag,pos=_varint(buf,pos,end);number,wire=tag>>3,tag&7
        if not number:raise ValueError('Invalid protobuf field')
        if wire==2:
            length,pos=_varint(buf,pos,end);offset=pos;pos+=length
        elif wire==0:
            offset=pos;_,pos=_varint(buf,pos,end);length=pos-offset
        elif wire in (1,5):offset=pos;length=8 if wire==1 else 4;pos+=length
        else:raise ValueError('Unsupported protobuf wire type')
        if pos>end:raise ValueError('Protobuf field exceeds enclosing message')
        yield number,wire,offset,length

def tensor_raw_offsets(path):
    result={};seen_graph=False
    with Path(path).open('rb') as source:
        if not source.seek(0,2):raise ValueError('Empty model')
        source.seek(0)
        with mmap.mmap(source.fileno(),0,access=mmap.ACCESS_READ) as buf:
            for number,wire,start,length in _fields(buf,0,len(buf)):
                if number!=7:continue
                if wire!=2 or seen_graph:raise ValueError('Expected one ONNX graph')
                seen_graph=True
                for field,kind,a,size in _fields(buf,start,start+length):
                    if field!=5:continue
                    if kind!=2:raise ValueError('Invalid ONNX initializer')
                    name=None;raw=None
                    for key,typ,offset,count in _fields(buf,a,a+size):
                        if key==8 and typ==2:name=bytes(buf[offset:offset+count]).decode('utf-8')
                        elif key==9 and typ==2:
                            if raw is not None:raise ValueError('Duplicate raw tensor field')
                            raw=(offset,count)
                    if raw is not None:
                        if not name or name in result:raise ValueError('Unnamed or duplicate initializer')
                        result[name]=raw
    if not seen_graph:raise ValueError('Missing ONNX graph')
    return result

def patch_shared_model(source,output,patches,*,relative_base,expected_sha256):
    import numpy as np
    import onnx
    source=Path(source);output=Path(output)
    if (not isinstance(relative_base,str) or '\\' in relative_base or ':' in relative_base or
        PurePosixPath(relative_base).is_absolute() or any(p in {'','.','..'} for p in relative_base.split('/'))):raise ValueError('Unsafe shared weight location')
    if output.resolve()==source.resolve() or output.exists():raise ValueError('Preserve original and previous artifacts')
    if _sha(source)!=expected_sha256:raise ValueError('Pinned base graph checksum differs')
    offsets=tensor_raw_offsets(source);model=onnx.load_model(str(source),load_external_data=False);found=set()
    for tensor in model.graph.initializer:
        if tensor.data_location==onnx.TensorProto.EXTERNAL:raise ValueError('Source must be a single authenticated inline model')
        if tensor.name in patches:
            array=np.asarray(patches[tensor.name])
            if array.dtype!=np.float32 or tensor.data_type!=onnx.TensorProto.FLOAT or tuple(array.shape)!=tuple(tensor.dims) or not np.isfinite(array).all():raise ValueError('Patch shape/type/value mismatch')
            tensor.raw_data=array.tobytes(order='C');tensor.ClearField('external_data');tensor.data_location=onnx.TensorProto.DEFAULT;found.add(tensor.name)
        elif tensor.raw_data:
            if tensor.name not in offsets or len(tensor.raw_data)!=offsets[tensor.name][1]:raise ValueError('Raw tensor index mismatch')
            offset,length=offsets[tensor.name]
            onnx.external_data_helper.set_external_data(tensor,location=relative_base,offset=offset,length=length)
            tensor.ClearField('raw_data')
    if found!=set(patches):raise ValueError('Unknown patch initializer')
    serialized=model.SerializeToString()
    if len(serialized)>48*1024**2:raise ValueError('Shared graph exceeds bounded output size')
    # Avoid ONNX external-data writers: they must never modify the pinned base.
    with output.open('xb') as target:target.write(serialized)
    return {'base_sha256':expected_sha256,'output_sha256':_sha(output),'output_bytes':len(serialized),
            'relative_base':relative_base,'patched_initializers':sorted(found),'external_tensor_count':sum(t.data_location==onnx.TensorProto.EXTERNAL for t in model.graph.initializer)}
