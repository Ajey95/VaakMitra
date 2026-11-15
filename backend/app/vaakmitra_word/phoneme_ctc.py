"""Transferred mobile acoustic encoder and provisional phoneme CTC contract."""

from __future__ import annotations

import hashlib
import math
from pathlib import Path

import numpy as np
import torch
from torch import nn

from .mobile_student_model import MobileWordStudent

SAMPLES = 48_000


def checkpoint_frame_shift(state):
    value = state.get("frame_shift_ms", 40)
    if value not in (20, 40):
        raise ValueError("unsupported phoneme frame shift")
    return value


class MobilePhonemeCtc(nn.Module):
    def __init__(
        self, vocabulary_size: int, encoder_blocks: int = 7, frame_shift_ms: int = 40
    ):
        super().__init__()
        if vocabulary_size < 2:
            raise ValueError("vocabulary must include blank and phones")
        if encoder_blocks not in (5, 7):
            raise ValueError("encoder_blocks must be 5 or 7")
        self.encoder = MobileWordStudent().encoder[:encoder_blocks]
        self.frame_shift_ms = checkpoint_frame_shift({"frame_shift_ms": frame_shift_ms})
        if self.frame_shift_ms == 20:
            self.encoder[4].layers[0].stride = (1,)
        # Preserve transferred kernels but retain enough frames for repeated phones.
        if encoder_blocks == 7:
            self.encoder[5].layers[0].stride = (1,)
            self.encoder[6].layers[0].stride = (1,)
        self.sequence = nn.GRU(
            64 if encoder_blocks == 5 else 96,
            96,
            2,
            batch_first=True,
            bidirectional=True,
            dropout=0.1,
        )
        self.head = nn.Linear(192, vocabulary_size)

    def load_encoder(self, state):
        source = {
            k.removeprefix("encoder."): v
            for k, v in state.items()
            if k.startswith("encoder.")
            and k.removeprefix("encoder.") in self.encoder.state_dict()
        }
        self.encoder.load_state_dict(source, strict=True)

    def forward(self, waveform):
        x = waveform.unsqueeze(1)
        x = x - x.mean(dim=2, keepdim=True)
        rms = torch.sqrt(torch.mean(x * x, dim=2, keepdim=True) + 1e-8)
        x = torch.clamp(x / rms.clamp_min(1e-4) * 0.08, -0.95, 0.95)
        hidden = self.encoder(x).transpose(1, 2)
        hidden, _ = self.sequence(hidden)
        return self.head(hidden)


class MobilePhonemeEnsemble(nn.Module):
    """DEC-048: two small acoustic models; no word or language-model input."""

    def __init__(self, vocabulary_size, encoder_blocks=5, frame_shift_ms=40):
        super().__init__()
        if encoder_blocks != 5 or frame_shift_ms != 40:
            raise ValueError("posterior ensemble supports only five-block 40ms members")
        self.members = nn.ModuleList(
            [MobilePhonemeCtc(vocabulary_size, 5, 40) for _ in range(2)]
        )

    def forward(self, waveform):
        probabilities = torch.stack(
            [member(waveform).log_softmax(-1) for member in self.members], dim=0
        )
        return torch.logsumexp(probabilities, dim=0) - math.log(2.0)


def model_from_checkpoint(state, vocabulary_size):
    """PHN-001/006: reconstruct only an explicitly supported bound architecture."""
    kind = state.get("model_kind", "single")
    if kind == "single":
        model = MobilePhonemeCtc(
            vocabulary_size,
            state.get("encoder_blocks", 7),
            frame_shift_ms=checkpoint_frame_shift(state),
        )
    elif kind == "posterior_mean_2":
        if (
            type(state.get("ensemble_members")) is not int
            or state["ensemble_members"] != 2
            or state.get("ensemble_weights") != [0.5, 0.5]
            or type(state.get("encoder_blocks")) is not int
            or state["encoder_blocks"] != 5
            or type(state.get("frame_shift_ms")) is not int
            or state["frame_shift_ms"] != 40
            or state.get("architecture_source_sha256")
            != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        ):
            raise ValueError(
                "unsupported ensemble contract or changed architecture source"
            )
        model = MobilePhonemeEnsemble(vocabulary_size)
    else:
        raise ValueError("unsupported phoneme model kind")
    model.load_state_dict(state["model"])
    return model.eval()


def ctc_decode(path, blank=0):
    result, previous = [], None
    for token in path:
        token = int(token)
        if token != blank and token != previous:
            result.append(token)
        previous = token
    return result


def choose_quantization(
    fp32_per, int8_per, agreement, target_fp32_per, target_int8_per, target_agreement
):
    accepted = agreement >= 0.98 and int8_per <= fp32_per + 0.01
    accepted = (
        accepted
        and target_agreement >= 0.98
        and target_int8_per <= target_fp32_per + 0.01
    )
    return "int8" if accepted else "fp32"


def prepare_waveform(audio, length=SAMPLES):
    source = np.asarray(audio, dtype=np.float32)
    if (
        source.ndim != 1
        or not np.isfinite(source).all()
        or len(source) > length
        or len(source) == 0
    ):
        raise ValueError("invalid waveform or cropping would lose phonemes")
    result = np.zeros(length, dtype=np.float32)
    offset = (length - len(source)) // 2
    result[offset : offset + len(source)] = source
    return result


def validate_splits(rows):
    speakers, hashes = {}, {}
    for row in rows:
        split = row["split"]
        if split not in ("train", "calibration", "evaluation"):
            raise ValueError("invalid split")
        for key, seen in [("speaker", speakers), ("audio_sha256", hashes)]:
            value = row[key]
            if value in seen and seen[value] != split:
                raise ValueError(f"{key} leakage across splits")
            seen[value] = split


def stress_waveform(audio, kind, seed):
    source = np.asarray(audio, dtype=np.float32)
    random = np.random.default_rng(seed)
    rms = float(np.sqrt(np.mean(source * source) + 1e-12))
    if kind.startswith("noise"):
        snr = float(kind.removeprefix("noise"))
        out = source + random.normal(0, rms / 10 ** (snr / 20), source.shape)
    elif kind == "echo":
        out = source.copy()
        delay = 960
        out[delay:] += 0.25 * source[:-delay]
    elif kind == "lowpass":
        out = np.convolve(source, np.ones(5) / 5, mode="same")
    elif kind == "quiet":
        out = source * 0.2
    else:
        raise ValueError("unknown stress transform")
    return np.clip(out, -1, 1).astype(np.float32)
