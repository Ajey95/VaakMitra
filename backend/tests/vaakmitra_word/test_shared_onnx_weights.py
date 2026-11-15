"""DEC075/PHN016: external slices address exact pinned ONNX raw tensor bytes."""
import hashlib
import numpy as np
import pytest
import onnx
from onnx import helper,numpy_helper,TensorProto
from app.vaakmitra_word.shared_onnx_weights import tensor_raw_offsets,patch_shared_model

def make(path):
    weight=np.arange(6,dtype=np.float32).reshape(2,3)
    graph=helper.make_graph([helper.make_node('MatMul',['x','w'],['y'])],'tiny',
        [helper.make_tensor_value_info('x',TensorProto.FLOAT,[1,2])],[helper.make_tensor_value_info('y',TensorProto.FLOAT,[1,3])],
        [numpy_helper.from_array(weight,name='w')])
    model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',17)]);model.ir_version=9;onnx.save_model(model,path)
    return weight,hashlib.sha256(path.read_bytes()).hexdigest()

def test_phn016_offsets_point_to_exact_raw_initializer(tmp_path):
    path=tmp_path/'base.onnx';weight,_=make(path);offsets=tensor_raw_offsets(path);start,length=offsets['w']
    assert path.read_bytes()[start:start+length]==weight.tobytes()

def test_phn016_shared_graph_executes_original_and_changed_weights(tmp_path):
    import onnxruntime as ort
    path=tmp_path/'base.onnx';weight,digest=make(path)
    out=tmp_path/'shared.onnx';patch_shared_model(path,out,{},relative_base='base.onnx',expected_sha256=digest)
    result=ort.InferenceSession(str(out),providers=['CPUExecutionProvider']).run(None,{'x':np.ones((1,2),dtype=np.float32)})[0]
    np.testing.assert_allclose(result,weight.sum(0,keepdims=True))
    changed=tmp_path/'changed.onnx';patch_shared_model(path,changed,{'w':weight+1},relative_base='base.onnx',expected_sha256=digest)
    result=ort.InferenceSession(str(changed),providers=['CPUExecutionProvider']).run(None,{'x':np.ones((1,2),dtype=np.float32)})[0]
    np.testing.assert_allclose(result,(weight+1).sum(0,keepdims=True))

def test_phn016_invalid_digest_paths_shapes_and_protobuf_fail_closed(tmp_path):
    path=tmp_path/'base.onnx';weight,digest=make(path)
    with pytest.raises(ValueError):patch_shared_model(path,tmp_path/'bad.onnx',{},relative_base='../escape.onnx',expected_sha256=digest)
    with pytest.raises(ValueError):patch_shared_model(path,tmp_path/'bad.onnx',{},relative_base='base.onnx',expected_sha256='0'*64)
    with pytest.raises(ValueError):patch_shared_model(path,tmp_path/'bad.onnx',{'w':np.ones(2,dtype=np.float32)},relative_base='base.onnx',expected_sha256=digest)
    malformed=tmp_path/'invalid';malformed.write_bytes(b'\x3a\xff')
    with pytest.raises(ValueError):tensor_raw_offsets(malformed)
