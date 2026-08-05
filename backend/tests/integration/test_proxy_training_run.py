from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np
from modeling.training.train_proxy_ctc import TrainingConfig, train_proxy_model


def _write_wave(path: Path, frequency: float) -> None:
    time = np.arange(0, 0.25, 1 / 16000, dtype=np.float32)
    samples = (np.sin(2 * np.pi * frequency * time) * 8000).astype("<i2")
    with wave.open(str(path), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(16000)
        output.writeframes(samples.tobytes())


def _write_index(path: Path, rows: list[dict[str, str]]) -> None:
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n", encoding="utf-8")


def test_proxy_training_writes_runnable_onnx_and_aggregate_report(tmp_path) -> None:
    audio_root = tmp_path / "audio"
    audio_root.mkdir()
    split_indices: dict[str, Path] = {}
    for split_index, split in enumerate(("train", "validation", "test")):
        rows = []
        for item_index, phonemes in enumerate(("a", "m")):
            filename = f"{split}-{item_index}.wav"
            _write_wave(audio_root / filename, 220 + split_index * 40 + item_index * 20)
            rows.append(
                {
                    "audio_rel_path": filename,
                    "phonemes": phonemes,
                    "record_id": f"{split}-{item_index}",
                    "speaker": f"speaker-{split}",
                }
            )
        index_path = tmp_path / f"{split}.jsonl"
        _write_index(index_path, rows)
        split_indices[split] = index_path

    result = train_proxy_model(
        train_index=split_indices["train"],
        validation_index=split_indices["validation"],
        test_index=split_indices["test"],
        audio_root=audio_root,
        output_dir=tmp_path / "model",
        report_path=tmp_path / "training-report.json",
        corpus_manifest_digest="d" * 64,
        dataset_revision="1d6a78e02c6c21d8da30eb57dd4dc02b4ed765f5",
        config=TrainingConfig(
            epochs=1,
            batch_size=2,
            learning_rate=0.001,
            channels=4,
            hidden_size=4,
            max_duration_seconds=1.0,
            max_train_records_per_speaker=2,
            max_eval_records_per_speaker=2,
            seed=17,
        ),
    )

    assert result.onnx_path.is_file()
    assert result.manifest_path.is_file()
    assert result.vocabulary_path.is_file()
    report = json.loads(result.report_path.read_text(encoding="utf-8"))
    assert report["model_evidence_scope"] == "trained_proxy_tamil_phoneme_model"
    assert report["evidence_scope"] == "engineering_proxy"
    assert report["population"] == "adult_tamil_proxy"
    assert report["split_counts"] == {"train": 2, "validation": 2, "test": 2}
    assert report["test"]["reference_units"] == 2
    assert "record_id" not in result.report_path.read_text(encoding="utf-8")

    import onnxruntime as ort

    session = ort.InferenceSession(str(result.onnx_path), providers=["CPUExecutionProvider"])
    logits = session.run(
        ["logits"],
        {"audio": np.zeros((1, 4000), dtype=np.float32)},
    )[0]
    assert logits.shape[0] == 1
    assert logits.shape[2] == report["vocabulary_size"]
