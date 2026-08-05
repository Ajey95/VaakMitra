"""Parse ONNX Runtime's static mobile-usability checker output."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class NNAPISupport(BaseModel):
    """NNAPI compatibility extracted from one static checker run."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    supported_nodes: int = Field(ge=0)
    total_nodes: int = Field(gt=0)
    partition_count: int = Field(ge=0)
    partition_sizes: tuple[int, ...]
    unsupported_operator_node_count: int = Field(ge=0)
    unsupported_operators: tuple[str, ...]
    dynamic_shape_node_count: int = Field(ge=0)
    suitable_as_is: bool
    fixed_shape_supported_nodes: int = Field(ge=0)
    fixed_shape_partition_count: int = Field(ge=0)
    fixed_shape_partition_sizes: tuple[int, ...]
    suitable_with_fixed_shapes: bool

    @model_validator(mode="after")
    def validate_partition_totals(self) -> NNAPISupport:
        if len(self.partition_sizes) != self.partition_count:
            raise ValueError("partition sizes must match the as-is partition count")
        if sum(self.partition_sizes) != self.supported_nodes:
            raise ValueError("partition sizes must sum to the as-is supported node count")
        if len(self.fixed_shape_partition_sizes) != self.fixed_shape_partition_count:
            raise ValueError("partition sizes must match the fixed-shape partition count")
        if sum(self.fixed_shape_partition_sizes) != self.fixed_shape_supported_nodes:
            raise ValueError("partition sizes must sum to the fixed-shape supported node count")
        if self.supported_nodes > self.total_nodes:
            raise ValueError("as-is supported nodes cannot exceed total nodes")
        if self.fixed_shape_supported_nodes > self.total_nodes:
            raise ValueError("fixed-shape supported nodes cannot exceed total nodes")
        return self


class MobileUsabilityReport(BaseModel):
    """Hash-identified static graph evidence, never a device measurement."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1.0"] = "1.0"
    evidence_scope: Literal["static_mobile_compatibility_audit"] = (
        "static_mobile_compatibility_audit"
    )
    checker: Literal["onnxruntime.tools.check_onnx_model_mobile_usability"] = (
        "onnxruntime.tools.check_onnx_model_mobile_usability"
    )
    model_filename: str | None = None
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_size_bytes: int = Field(gt=0)
    nnapi: NNAPISupport
    recommended_execution_provider: Literal["CPUExecutionProvider"]
    physical_device_measured: Literal[False] = False
    limitations: tuple[str, ...] = (
        "static_graph_analysis_only",
        "no_physical_tablet_latency_memory_battery_or_thermal_measurement",
    )


def _normalized_output(text: str) -> str:
    without_prefixes = re.sub(r"(?m)^\s*INFO:\s*", "", text)
    single_line = re.sub(r"\s+", " ", without_prefixes).strip()
    return re.sub(r"ai\.onnx:\s+", "ai.onnx:", single_line)


def _partition_data(section: str) -> tuple[int, int, int, tuple[int, ...]]:
    summary = re.search(
        r"(\d+) partitions? with a total of (\d+)/(\d+) nodes can be handled",
        section,
    )
    sizes = re.search(r"Partition sizes:\s*\[([^]]*)\]", section)
    if summary is None or sizes is None:
        raise ValueError("NNAPI partition evidence is incomplete")
    partition_sizes = tuple(int(value.strip()) for value in sizes.group(1).split(",") if value)
    return int(summary.group(1)), int(summary.group(2)), int(summary.group(3)), partition_sizes


def _unsupported_operators(section: str) -> tuple[int, tuple[str, ...]]:
    count = re.search(r"Unsupported nodes due to operator=(\d+)", section)
    operators = re.search(
        r"Unsupported ops:\s*(.*?)(?=Caveats|Unsupported nodes due to input|Model should)",
        section,
    )
    if count is None or operators is None:
        raise ValueError("NNAPI unsupported-operator evidence is incomplete")
    values = tuple(value.strip() for value in operators.group(1).split(",") if value.strip())
    if not values or any(not value.startswith("ai.onnx:") for value in values):
        raise ValueError("NNAPI unsupported operator names are invalid")
    return int(count.group(1)), values


def _suitability(section: str, *, fixed_shapes: bool) -> bool:
    if fixed_shapes:
        pattern = r"Model should perform well with NNAPI if modified to have fixed input shapes: (YES|NO)"
    else:
        pattern = r"Model should perform well with NNAPI as is: (YES|NO)"
    match = re.search(pattern, section)
    if match is None:
        raise ValueError("NNAPI suitability evidence is incomplete")
    return match.group(1) == "YES"


def parse_mobile_checker_output(
    text: str,
    model_sha256: str,
    model_size_bytes: int,
    *,
    model_filename: str | None = None,
) -> MobileUsabilityReport:
    """Parse strict NNAPI evidence from official ONNX Runtime checker text."""

    normalized = _normalized_output(text)
    nnapi_match = re.search(r"Checking NNAPI(.*?)(?=Checking CoreML|$)", normalized)
    if nnapi_match is None:
        raise ValueError("NNAPI section is missing")
    nnapi_section = nnapi_match.group(1)
    section_parts = re.split(
        r"Checking if model will perform better if the dynamic shapes are fixed\.\.\.",
        nnapi_section,
        maxsplit=1,
    )
    if len(section_parts) != 2:
        raise ValueError("NNAPI fixed-shape section is missing")
    as_is_section, fixed_section = section_parts

    partition_count, supported_nodes, total_nodes, partition_sizes = _partition_data(
        as_is_section
    )
    fixed_count, fixed_supported, fixed_total, fixed_sizes = _partition_data(fixed_section)
    if fixed_total != total_nodes:
        raise ValueError("NNAPI as-is and fixed-shape node totals differ")
    unsupported_count, unsupported_operators = _unsupported_operators(as_is_section)
    dynamic_shape = re.search(
        r"Unsupported nodes due to input having a dynamic shape=(\d+)", as_is_section
    )
    if dynamic_shape is None:
        raise ValueError("NNAPI dynamic-shape evidence is missing")
    if "For optimal performance the model should be used with the CPU EP." not in normalized:
        raise ValueError("CPU provider recommendation is missing or unknown")

    nnapi = NNAPISupport(
        supported_nodes=supported_nodes,
        total_nodes=total_nodes,
        partition_count=partition_count,
        partition_sizes=partition_sizes,
        unsupported_operator_node_count=unsupported_count,
        unsupported_operators=unsupported_operators,
        dynamic_shape_node_count=int(dynamic_shape.group(1)),
        suitable_as_is=_suitability(as_is_section, fixed_shapes=False),
        fixed_shape_supported_nodes=fixed_supported,
        fixed_shape_partition_count=fixed_count,
        fixed_shape_partition_sizes=fixed_sizes,
        suitable_with_fixed_shapes=_suitability(fixed_section, fixed_shapes=True),
    )
    return MobileUsabilityReport(
        model_filename=model_filename,
        model_sha256=model_sha256,
        model_size_bytes=model_size_bytes,
        nnapi=nnapi,
        recommended_execution_provider="CPUExecutionProvider",
    )
