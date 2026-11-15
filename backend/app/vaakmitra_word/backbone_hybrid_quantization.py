"""DEC068/PHN008: full-range INT8 prefix with untouched trained FP32 tail/head."""
import os,re,uuid
from pathlib import Path
import onnx
from onnxruntime.quantization.onnx_quantizer import ONNXQuantizer
from onnxruntime.quantization.quant_utils import QuantType,QuantizationMode,add_infer_metadata

PROFILE={'method':'onnxruntime_dynamic_integer_ops_hybrid','weight_type':'QInt8','activation_type':'QUInt8',
    'per_channel':True,'reduce_range':False,'weight_range_bits':8,'op_types':['MatMul','Gemm'],
    'MatMulConstBOnly':True,'float_modules':['feature_projection','last2_encoder_blocks','lm_head'],
    'expected_encoder_blocks':24,'float_tail_layers':[22,23],'float_prefix_layers':[],'graph_preprocess':'shape_inference_only',
    'laptop_avx_vnni_verified':True}


def quantize_hybrid_graph(source,target,*,scratch_dir,encoder_blocks=24,float_prefix_layers=0):
    if type(float_prefix_layers)is not int or not 0<=float_prefix_layers<encoder_blocks-2:
        raise ValueError('At least one encoder block must remain quantized')
    source=Path(source);target=Path(target);partial=target.with_name(target.name+'.partial')
    if target.exists() or partial.exists():raise FileExistsError('Quantization artifacts are immutable')
    parent=Path(scratch_dir);parent.mkdir(parents=True,exist_ok=True)
    owned=(parent/('shape-'+uuid.uuid4().hex)).resolve();owned.mkdir(exist_ok=False);inferred=owned/'inferred.onnx'
    try:
        onnx.shape_inference.infer_shapes_path(str(source),str(inferred))
        model=onnx.load(str(inferred));add_infer_metadata(model)
    finally:
        if inferred.exists():inferred.unlink()
        owned.rmdir()
    layer_ids={int(match.group(1))for node in model.graph.node if(match:=re.search(r'/encoder/layers\.(\d+)/',node.name))}
    if encoder_blocks<3 or layer_ids!=set(range(encoder_blocks)):raise ValueError('Unexpected encoder scopes')
    tail=[encoder_blocks-2,encoder_blocks-1]
    front=list(range(float_prefix_layers))
    def protected(name):return '/feature_projection/'in name or '/lm_head/'in name or any(f'/encoder/layers.{i}/'in name for i in front+tail)
    excluded=[node.name for node in model.graph.node if node.op_type in('MatMul','Gemm')and protected(node.name)]
    if not excluded or not any('/lm_head/'in n for n in excluded)or not any('/feature_projection/'in n for n in excluded):
        raise ValueError('Protected projection/head scopes missing')
    quantizer=ONNXQuantizer(model,True,False,QuantizationMode.IntegerOps,False,
        QuantType.QInt8,QuantType.QUInt8,None,[],excluded,['MatMul','Gemm'],{'MatMulConstBOnly':True})
    quantizer.quantize_model();quantizer.model.save_model_to_file(str(partial),False)
    with partial.open('r+b')as stream:os.fsync(stream.fileno())
    partial.replace(target)
    return dict(PROFILE,expected_encoder_blocks=encoder_blocks,float_tail_layers=tail,float_prefix_layers=front,excluded_nodes=excluded)
