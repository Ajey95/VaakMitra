from __future__ import annotations

import json
import wave

import numpy as np
import pytest
import torch
from modeling.training.proxy_dataset import (
    load_mono_pcm16,
    proxy_phone_units,
    select_available_records,
)
from modeling.training.tiny_ctc import TinyWaveCtc, build_proxy_vocabulary
from modeling.training.train_proxy_ctc import export_proxy_onnx, greedy_ctc_decode


def test_proxy_phone_units_are_deterministic_and_remove_text_punctuation() -> None:
    length_mark = "\N{MODIFIER LETTER TRIANGULAR COLON}"
    units = proxy_phone_units(f"a{length_mark} m, t͡ʃ!")

    assert units == ("a", length_mark, "m", "t", "͡", "ʃ")


def test_proxy_vocabulary_has_stable_blank_unknown_and_sorted_units() -> None:
    length_mark = "\N{MODIFIER LETTER TRIANGULAR COLON}"
    vocabulary = build_proxy_vocabulary(("m a", f"a{length_mark}"))

    assert vocabulary.tokens == ("<blank>", "<unk>", "a", "m", length_mark)
    assert vocabulary.blank_index == 0
    assert vocabulary.encode("a x") == (2, 1)


def test_load_mono_pcm16_resamples_to_16khz_without_clipping(tmp_path) -> None:
    path = tmp_path / "fixture.wav"
    samples = (np.sin(np.linspace(0, 4 * np.pi, 2400)) * 12000).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(samples.tobytes())

    waveform = load_mono_pcm16(path, target_sample_rate=16000, max_duration_seconds=1.0)

    assert waveform.dtype == torch.float32
    assert waveform.shape == (1600,)
    assert float(waveform.abs().max()) <= 1.0


def test_load_mono_pcm16_rejects_audio_longer_than_configured_limit(tmp_path) -> None:
    path = tmp_path / "long.wav"
    samples = np.zeros(24001, dtype="<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(24000)
        output.writeframes(samples.tobytes())

    with pytest.raises(ValueError, match="maximum duration"):
        load_mono_pcm16(path, target_sample_rate=16000, max_duration_seconds=1.0)


def test_tiny_wave_ctc_output_lengths_match_forward_frames() -> None:
    model = TinyWaveCtc(vocabulary_size=5, channels=8, hidden_size=8)
    audio = torch.zeros((2, 3200), dtype=torch.float32)
    lengths = torch.tensor([3200, 2400], dtype=torch.long)

    logits = model(audio)
    output_lengths = model.output_lengths(lengths)

    assert logits.shape[0] == 2
    assert logits.shape[2] == 5
    assert output_lengths[0].item() == logits.shape[1]
    assert 0 < output_lengths[1].item() < output_lengths[0].item()


def test_tiny_wave_ctc_supports_finite_loss_and_backpropagation() -> None:
    torch.manual_seed(7)
    model = TinyWaveCtc(vocabulary_size=5, channels=8, hidden_size=8)
    audio = torch.randn((2, 3200), dtype=torch.float32) * 0.01
    input_lengths = torch.tensor([3200, 3200], dtype=torch.long)
    targets = torch.tensor([2, 3, 2, 4], dtype=torch.long)
    target_lengths = torch.tensor([2, 2], dtype=torch.long)
    logits = model(audio)
    log_probabilities = torch.log_softmax(logits, dim=-1).transpose(0, 1)
    loss = torch.nn.functional.ctc_loss(
        log_probabilities,
        targets,
        model.output_lengths(input_lengths),
        target_lengths,
        blank=0,
        zero_infinity=True,
    )

    loss.backward()

    assert torch.isfinite(loss)
    assert any(parameter.grad is not None for parameter in model.parameters())


def test_select_available_records_is_speaker_balanced_and_skips_missing_audio(tmp_path) -> None:
    audio_root = tmp_path / "audio"
    audio_root.mkdir()
    rows = []
    for speaker in ("a", "b"):
        for index in range(3):
            rel_path = f"{speaker}-{index}.wav"
            rows.append(
                {
                    "audio_rel_path": rel_path,
                    "phonemes": "a m",
                    "record_id": f"{speaker}-{index}",
                    "speaker": speaker,
                }
            )
            if index < 2:
                samples = np.zeros(1600, dtype="<i2")
                with wave.open(str(audio_root / rel_path), "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(16000)
                    output.writeframes(samples.tobytes())
    index_path = tmp_path / "index.jsonl"
    index_path.write_text("\n".join(json.dumps(row) for row in rows), encoding="utf-8")

    records = select_available_records(
        index_path,
        audio_root=audio_root,
        max_records_per_speaker=1,
        max_duration_seconds=1.0,
    )

    assert [(record.speaker, record.record_id) for record in records] == [
        ("a", "a-0"),
        ("b", "b-0"),
    ]


def test_greedy_ctc_decode_handles_blank_repeat_and_batch_lengths() -> None:
    token_ids = torch.tensor(
        [
            [0, 2, 2, 0, 2, 3],
            [3, 3, 0, 2, 0, 0],
        ],
        dtype=torch.long,
    )

    decoded = greedy_ctc_decode(token_ids, torch.tensor([6, 4]), blank_index=0)

    assert decoded == ((2, 2, 3), (3, 2))


def test_exported_proxy_model_runs_with_dynamic_raw_audio(tmp_path) -> None:
    torch.manual_seed(11)
    model = TinyWaveCtc(vocabulary_size=5, channels=8, hidden_size=8)
    output = tmp_path / "proxy.onnx"

    export_proxy_onnx(model, output, example_samples=3200)

    import onnxruntime as ort

    session = ort.InferenceSession(str(output), providers=["CPUExecutionProvider"])
    logits = session.run(
        ["logits"],
        {"audio": np.zeros((1, 4000), dtype=np.float32)},
    )[0]
    assert logits.shape[0] == 1
    assert logits.shape[2] == 5
    assert logits.shape[1] > 0
