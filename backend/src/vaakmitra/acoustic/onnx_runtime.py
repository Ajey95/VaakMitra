"""ONNX Runtime adapter for a packaged Tamil phoneme CTC model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from vaakmitra.acoustic.metadata import ModelManifest, verify_model_integrity
from vaakmitra.contracts.acoustic import AcousticOutput


class ModelRuntimeConfigurationError(ValueError):
    """Raised when the manifest and installed ONNX runtime cannot form a session."""


class OnnxAcousticModelRuntime:
    """Run a hash-verified ONNX model locally with explicit execution providers."""

    def __init__(
        self,
        model_path: str | Path,
        manifest: ModelManifest,
        *,
        providers: tuple[str, ...] = ("CPUExecutionProvider",),
    ) -> None:
        if not providers:
            raise ModelRuntimeConfigurationError("at least one execution provider is required")
        verify_model_integrity(model_path, manifest)
        try:
            import onnxruntime as ort  # type: ignore[import-untyped]
        except ImportError as error:
            raise ModelRuntimeConfigurationError(
                "onnxruntime is required; install the model extra"
            ) from error

        available = set(ort.get_available_providers())
        unavailable = [provider for provider in providers if provider not in available]
        if unavailable:
            raise ModelRuntimeConfigurationError(
                f"requested execution provider is unavailable: {', '.join(unavailable)}"
            )
        options = ort.SessionOptions()
        options.log_severity_level = 3
        try:
            session = ort.InferenceSession(
                str(Path(model_path)),
                sess_options=options,
                providers=list(providers),
            )
        except Exception as error:
            raise ModelRuntimeConfigurationError("unable to load ONNX model") from error

        input_names = {model_input.name for model_input in session.get_inputs()}
        output_names = {model_output.name for model_output in session.get_outputs()}
        if manifest.input_name not in input_names:
            raise ModelRuntimeConfigurationError("manifest input_name is absent from model")
        if manifest.output_name not in output_names:
            raise ModelRuntimeConfigurationError("manifest output_name is absent from model")

        self._session: Any = session
        self._manifest = manifest

    @property
    def providers(self) -> tuple[str, ...]:
        """Return the actual execution providers in priority order."""

        return tuple(self._session.get_providers())

    def infer(self, audio: np.ndarray, sample_rate: int) -> AcousticOutput:
        """Run one mono waveform and normalize model output to `[frames, vocabulary]`."""

        if sample_rate != self._manifest.sample_rate:
            raise ValueError("ONNX acoustic runtime requires 16000 Hz audio")
        if not isinstance(audio, np.ndarray) or audio.ndim != 1:
            raise ValueError("audio must be a mono NumPy array")
        if audio.size == 0:
            raise ValueError("audio must be non-empty")
        if not np.issubdtype(audio.dtype, np.floating) or not np.isfinite(audio).all():
            raise ValueError("audio must contain finite floating-point samples")

        batch = np.asarray(audio, dtype=np.float32)[None, :]
        raw = self._session.run(
            [self._manifest.output_name],
            {self._manifest.input_name: batch},
        )[0]
        values = np.asarray(raw, dtype=np.float32)
        if values.ndim == 3 and values.shape[0] == 1:
            values = values[0]
        if values.ndim != 2:
            raise ValueError("ONNX output must have shape [batch, frames, vocabulary]")
        if values.shape[0] == 0 or values.shape[1] != self._manifest.vocabulary_size:
            raise ValueError("ONNX output shape does not match model manifest")
        if not np.isfinite(values).all():
            raise ValueError("ONNX output contains non-finite values")
        if self._manifest.output_kind == "logits":
            values = _log_softmax(values)

        return AcousticOutput(
            log_probabilities=values,
            frame_shift_ms=self._manifest.frame_shift_ms,
            model_version=self._manifest.model_version,
            vocabulary_version=self._manifest.vocabulary_version,
            blank_index=self._manifest.blank_index,
            vocabulary_size=self._manifest.vocabulary_size,
        )


def _log_softmax(logits: np.ndarray) -> np.ndarray:
    maximum = np.max(logits, axis=1, keepdims=True)
    shifted = logits - maximum
    return shifted - np.log(np.exp(shifted).sum(axis=1, keepdims=True))
