"""DEC-068/PHN-008: waveform-only backbone, explicit IPA units and valid lengths."""
from __future__ import annotations

import copy
from collections.abc import Sequence
import numpy as np
import torch
from torch import nn
from .phoneme_decoder import decode_logits

COMPOUNDS = {"aj": ("a", "j"), "aʋ": ("a", "ʋ"), "kʂ": ("k", "ʂ")}
KERNELS = (10, 3, 3, 3, 3, 2, 2)
STRIDES = (5, 2, 2, 2, 2, 2, 2)


def canonicalize_phones(phones: Sequence[str]) -> list[str]:
    if isinstance(phones, (str, bytes)) or not isinstance(phones, Sequence):
        raise ValueError("A sequence of phone units is required")
    if any(not isinstance(phone, str) or not phone for phone in phones):
        raise ValueError("Phone units must be nonempty strings")
    # Unit conversion is independent of any reference/word. Never collapse doubles here.
    return [unit for phone in phones for unit in COMPOUNDS.get(phone, (phone,))]


def normalize_and_pad(waves: Sequence[np.ndarray]) -> tuple[np.ndarray, np.ndarray]:
    if not waves:
        raise ValueError("Empty waveform batch")
    source = [np.asarray(wave, dtype=np.float32) for wave in waves]
    if any(wave.ndim != 1 or not 400 <= len(wave) <= 48000 or not np.isfinite(wave).all() for wave in source):
        raise ValueError("Invalid waveform or truncation would be required")
    samples = max(map(len, source))
    values = np.zeros((len(source), samples), dtype=np.float32)
    mask = np.zeros((len(source), samples), dtype=np.int64)
    for i, wave in enumerate(source):
        values[i, :len(wave)] = (wave - wave.mean()) / np.sqrt(wave.var() + 1e-7)
        mask[i, :len(wave)] = 1
    return values, mask


def feature_lengths(samples: torch.Tensor) -> torch.Tensor:
    if samples.ndim != 1 or not len(samples) or samples.dtype not in (torch.int32, torch.int64):
        raise ValueError("Integer sample lengths are required")
    if (samples < 400).any() or (samples > 48000).any():
        raise ValueError("Sample length is outside the declared backbone contract")
    result = samples.clone()
    for kernel, stride in zip(KERNELS, STRIDES):
        result = torch.div(result - kernel, stride, rounding_mode="floor") + 1
    return result


def map_target_ids(ids: Sequence[int], source_tokens: Sequence[str], native_vocab: dict[str, int]) -> list[int]:
    if not ids or any(type(i) is not int or not 0 < i < len(source_tokens) for i in ids):
        raise ValueError("Invalid/nonphone training target")
    try:
        mapped = [native_vocab[source_tokens[i]] for i in ids]
    except KeyError as exc:
        raise ValueError("Training unit is not in the acoustic model inventory") from exc
    if native_vocab.get("[PAD]") in mapped:
        raise ValueError("CTC blank cannot be a training target")
    return mapped


def ctc_min_frames(targets: Sequence[int]) -> int:
    if not targets:
        raise ValueError("CTC target cannot be empty")
    return len(targets) + sum(left == right for left, right in zip(targets, targets[1:]))


def decode_backbone_logits(logits: np.ndarray, native_vocab: dict[str, int], decoder: dict) -> list[str]:
    inverse = {i: phone for phone, i in native_vocab.items()}
    if set(inverse) != set(range(len(native_vocab))) or "[PAD]" not in native_vocab:
        raise ValueError("Incomplete acoustic vocabulary")
    if logits.ndim != 2 or logits.shape[1] != len(inverse) or not np.isfinite(logits).all():
        raise ValueError("Invalid acoustic logits")
    blank = native_vocab["[PAD]"]
    order = [blank] + [i for i in range(len(inverse)) if i != blank]
    path = decode_logits(logits[:, order], decoder)
    units = [inverse[order[i]] for i in path if inverse[order[i]] != "|"]
    return canonicalize_phones(units)


class PhonemeTail(nn.Module):
    def __init__(self, layers, norm, head, dropout):
        super().__init__()
        self.layers = nn.ModuleList(layers)
        self.norm = norm
        self.head = head
        self.dropout = dropout

    def forward(self, features: torch.Tensor, lengths: torch.Tensor) -> torch.Tensor:
        if features.ndim != 3 or lengths.ndim != 1 or len(lengths) != len(features):
            raise ValueError("Feature batch/length mismatch")
        if (lengths <= 0).any() or (lengths > features.shape[1]).any():
            raise ValueError("Invalid valid-frame lengths")
        time = features.shape[1]
        valid = torch.arange(time, device=features.device)[None, :] < lengths.to(features.device)[:, None]
        mask = (1.0 - valid[:, None, None, :].to(features.dtype)) * torch.finfo(features.dtype).min
        mask = mask.expand(len(features), 1, time, time)
        hidden = features
        for layer in self.layers:
            hidden = layer(hidden, attention_mask=mask, output_attentions=False)[0]
        return self.head(self.dropout(self.norm(hidden)))


def split_backbone(full_model, tail_blocks: int = 2):
    """Consumes an owned loaded model; returns frozen prefix and independent trainable tail."""
    encoder = full_model.wav2vec2.encoder
    if not full_model.config.do_stable_layer_norm or not 0 < tail_blocks < len(encoder.layers):
        raise ValueError("Unsupported prefix/tail architecture")
    tail = PhonemeTail(
        [copy.deepcopy(layer) for layer in encoder.layers[-tail_blocks:]],
        copy.deepcopy(encoder.layer_norm), copy.deepcopy(full_model.lm_head), copy.deepcopy(full_model.dropout),
    ).float().requires_grad_(True).eval()
    encoder.layers = nn.ModuleList(list(encoder.layers[:-tail_blocks]))
    encoder.layer_norm = nn.Identity()
    prefix = full_model.wav2vec2.requires_grad_(False).eval()
    return prefix, tail
