"""Local AI4Bharat/NeMo acoustic adapter boundary (MOD-001..008)."""

from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Protocol
import unicodedata

import numpy as np

from .contracts import ModelEvidence, WordCandidate


class ModelCapabilityError(RuntimeError):
    pass


class AcousticModel(Protocol):
    model_version: str
    model_hash: str
    ready: bool
    is_test_double: bool

    def infer(self, samples: np.ndarray, sample_rate: int, target_word: str) -> ModelEvidence: ...


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


class NeMoIndicConformerAdapter:
    """Lazy local adapter; model files are never downloaded by this class."""

    is_test_double = False

    def __init__(self, *, model_path: Path, expected_sha256: str, device: str = "cuda") -> None:
        self.model_path = Path(model_path)
        self.model_hash = expected_sha256.lower()
        self.device = device
        self.model_version = "ai4bharat-indicconformer-ta-hybrid-ctc-rnnt-large:ctc:ta"
        self._model = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    def load(self) -> None:
        if not self.model_path.is_file():
            raise ModelCapabilityError("model_unavailable: configured .nemo file does not exist")
        actual = sha256_file(self.model_path)
        if actual != self.model_hash:
            raise ModelCapabilityError("model_integrity_mismatch: configured SHA-256 does not match")
        try:
            import torch

            if self.device not in ("cpu", "cuda") or self.device == "cuda" and not torch.cuda.is_available():
                raise ModelCapabilityError("model_runtime_unavailable: configured execution device is unavailable")
            from nemo.collections.asr.models import ASRModel
        except ImportError as exc:
            raise ModelCapabilityError("model_runtime_unavailable: NVIDIA NeMo ASR is not installed") from exc
        except ModelCapabilityError:
            raise
        try:
            self._model = ASRModel.restore_from(str(self.model_path), map_location=self.device)
            self._model.to(self.device)
            self._model.eval()
        except Exception as exc:
            self._model = None
            raise ModelCapabilityError("model_load_failed: local NeMo restore failed") from exc

    def infer(self, samples: np.ndarray, sample_rate: int, target_word: str) -> ModelEvidence:
        if sample_rate != 16000:
            raise ModelCapabilityError("model_input_invalid: sample rate must be 16000 Hz")
        if self._model is None:
            self.load()
        audio = np.asarray(samples, dtype=np.float32)
        if audio.ndim != 1 or audio.size == 0 or not np.isfinite(audio).all():
            raise ModelCapabilityError("model_input_invalid: expected finite mono samples")
        try:
            self._model.eval()
            embeddings = self._encode(audio)
            # PRV-002: pinned NeMo's tensor transcription path accepts PCM arrays.
            # Avoid a recoverable temporary WAV containing the user's voice.
            self._model.cur_decoder = "ctc"
            hypotheses = self._model.transcribe(
                [audio], batch_size=1, logprobs=False, language_id="ta",
            )
            transcript = self._hypothesis_text(hypotheses[0] if hypotheses else "")
        except ModelCapabilityError:
            raise
        except Exception as exc:
            raise ModelCapabilityError("model_inference_failed: local NeMo inference failed") from exc
        finally:
            # NeMo unfreeze() calls train() on encoder/decoder during teardown.
            # Restore inference mode even if transcription failed (MOD-003).
            self._model.eval()

        normalized_target = unicodedata.normalize("NFC", target_word).strip()
        candidates = [WordCandidate(word=transcript, probability=1.0)] if transcript else []
        # Exact transcript identity is a categorical proxy, not a calibrated probability.
        # The calibration stage owns its interpretation and cannot run without other families.
        target_proxy = 1.0 if transcript and transcript == normalized_target else 0.0
        return ModelEvidence(
            candidates=candidates,
            target_probability=target_proxy,
            embeddings=embeddings,
            model_version=self.model_version,
            model_hash=self.model_hash,
        )

    def _encode(self, samples: np.ndarray) -> np.ndarray:
        try:
            import torch

            signal = torch.as_tensor(samples, dtype=torch.float32).unsqueeze(0)
            length = torch.tensor([signal.shape[1]], dtype=torch.long)
            device = next(self._model.parameters()).device
            signal, length = signal.to(device), length.to(device)
            with torch.inference_mode():
                processed, processed_length = self._model.preprocessor(
                    input_signal=signal,
                    length=length,
                )
                encoded, encoded_length = self._model.encoder(
                    audio_signal=processed,
                    length=processed_length,
                )
            frames = encoded[0, :, : int(encoded_length[0])].transpose(0, 1)
            return frames.detach().cpu().numpy().astype(np.float32, copy=False)
        except Exception as exc:
            raise ModelCapabilityError("model_embedding_failed: encoder representations unavailable") from exc

    @staticmethod
    def _hypothesis_text(hypothesis) -> str:
        if isinstance(hypothesis, (list, tuple)):
            for nested_hypothesis in hypothesis:
                text = NeMoIndicConformerAdapter._hypothesis_text(nested_hypothesis)
                if text:
                    return text
            return ""
        text = hypothesis if isinstance(hypothesis, str) else getattr(hypothesis, "text", "")
        return unicodedata.normalize("NFC", str(text)).strip()
