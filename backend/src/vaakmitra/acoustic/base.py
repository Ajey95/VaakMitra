"""Dependency-inversion boundary for local Tamil acoustic inference."""

from __future__ import annotations

from typing import Any, Protocol

import numpy as np
import numpy.typing as npt

from vaakmitra.contracts.acoustic import AcousticOutput


class AcousticModelRuntime(Protocol):
    """Runtime implemented by ONNX or deterministic integration fixtures."""

    def infer(
        self,
        audio: npt.NDArray[np.floating[Any]],
        sample_rate: int,
    ) -> AcousticOutput:
        """Convert validated mono 16 kHz audio into phoneme log probabilities."""
        ...
