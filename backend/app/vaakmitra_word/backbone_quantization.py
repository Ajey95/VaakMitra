"""DEC068/PHN008: official ORT dynamic INT8 math with bounded scratch placement."""
import os
import uuid
from pathlib import Path
import onnx
from onnxruntime.quantization.onnx_quantizer import ONNXQuantizer
from onnxruntime.quantization.quant_utils import QuantType,QuantizationMode,add_infer_metadata

PROFILE={'method':'onnxruntime_dynamic_integer_ops','weight_type':'QInt8','activation_type':'QUInt8',
    'per_channel':True,'reduce_range':True,'weight_range_bits':7,
    'op_types':['MatMul','Gemm'],'MatMulConstBOnly':True,'graph_preprocess':'shape_inference_only'}


def quantize_backbone_graph(source, target, *, scratch_dir=None):
    """Source is immutable. Only an owned transient inferred copy is removed.

    The ORT convenience wrapper infers beside the input, temporarily duplicating
    the1.26GB graph on E. Invoke the same ONNXQuantizer after official shape
    inference in explicit scratch storage; no quantization formulas are changed.
    """
    source=Path(source);target=Path(target);partial=target.with_name(target.name+'.partial')
    if target.exists() or partial.exists():raise FileExistsError('Quantization artifacts are immutable')
    parent=Path(scratch_dir)if scratch_dir is not None else target.parent
    parent.mkdir(parents=True,exist_ok=True)
    owned=(parent/('shape-'+uuid.uuid4().hex)).resolve();owned.mkdir(exist_ok=False)
    inferred=owned/'inferred.onnx'
    try:
        onnx.shape_inference.infer_shapes_path(str(source),str(inferred))
        model=onnx.load(str(inferred));add_infer_metadata(model)
    finally:
        # Exact owned temporary file only; never traverse/delete an input directory.
        if inferred.exists():inferred.unlink()
        owned.rmdir()
    quantizer=ONNXQuantizer(model,True,True,QuantizationMode.IntegerOps,False,
        QuantType.QInt8,QuantType.QUInt8,None,[],[],['MatMul','Gemm'],{'MatMulConstBOnly':True})
    quantizer.quantize_model();quantizer.model.save_model_to_file(str(partial),False)
    with partial.open('r+b')as stream:os.fsync(stream.fileno())
    partial.replace(target)
