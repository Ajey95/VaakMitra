"""PHN-001/003: audio-only CTC decoding, without a word or language model."""

from __future__ import annotations

import math

import numpy as np

NEG = -float("inf")


def validate_decoder(config, vocabulary_size):
    if not isinstance(config, dict) or vocabulary_size < 2:
        raise ValueError("invalid decoder metadata")
    if config == {"type": "greedy"}:
        return dict(config)
    if (
        set(config) != {"type", "beam_width", "nonblank_top_k"}
        or config["type"] != "ctc_prefix_beam"
    ):
        raise ValueError("unknown decoder or unexpected parameters")
    width, top = config["beam_width"], config["nonblank_top_k"]
    if (
        type(width) is not int
        or type(top) is not int
        or not 1 <= width <= 10
        or not 1 <= top <= min(60, vocabulary_size - 1)
    ):
        raise ValueError("invalid bounded decoder integers")
    return dict(config)


def log_add(a, b):
    if a == NEG:
        return b
    if b == NEG:
        return a
    return max(a, b) + math.log1p(math.exp(-abs(a - b)))


def decode_logits(logits, decoder=None):
    values = np.asarray(logits, dtype=np.float64)
    if values.ndim != 2 or values.shape[1] < 2 or not np.isfinite(values).all():
        raise ValueError("invalid CTC logits")
    config = validate_decoder(
        {"type": "greedy"} if decoder is None else decoder, values.shape[1]
    )
    if config["type"] == "greedy":
        out = []
        previous = -1
        for token in values.argmax(-1):
            if token != 0 and token != previous:
                out.append(int(token))
            previous = token
        return out
    active = {(): (0.0, NEG)}
    for raw in values:
        shifted = raw - np.max(raw)
        frame = shifted - math.log(sum(math.exp(float(v)) for v in shifted))
        labels = sorted(range(1, len(frame)), key=lambda c: (-frame[c], c))[
            : config["nonblank_top_k"]
        ]
        next_states = {}

        def push(prefix, blank=NEG, nonblank=NEG, states=next_states):
            old = states.get(prefix, (NEG, NEG))
            states[prefix] = (log_add(old[0], blank), log_add(old[1], nonblank))

        for prefix, (blank, nonblank) in active.items():
            push(prefix, blank=log_add(blank, nonblank) + float(frame[0]))
            for label in labels:
                score = float(frame[label])
                if prefix and label == prefix[-1]:
                    push(prefix, nonblank=nonblank + score)
                    push(prefix + (label,), nonblank=blank + score)
                else:
                    push(prefix + (label,), nonblank=log_add(blank, nonblank) + score)
        active = dict(
            sorted(next_states.items(), key=lambda item: (-log_add(*item[1]), item[0]))[
                : config["beam_width"]
            ]
        )
    return list(min(active, key=lambda p: (-log_add(*active[p]), p)))
