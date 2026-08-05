"""Train and export a small adult-Tamil proxy CTC technical prototype."""

from __future__ import annotations

import argparse
import json
import math
import random
import warnings
import wave
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
from itertools import pairwise
from pathlib import Path
from typing import Any

import torch
import torchaudio  # type: ignore[import-untyped]
from torch.nn.utils.rnn import pad_sequence
from vaakmitra.acoustic.metadata import ModelManifest

from modeling.artifacts import ArtifactRecord, describe_artifact
from modeling.data.corpus_manifest import CorpusManifest
from modeling.evaluation.ctc_metrics import edit_distance
from modeling.training.proxy_dataset import (
    ProxyIndexRecord,
    load_mono_pcm16,
    select_available_records,
)
from modeling.training.tiny_ctc import (
    ProxyPhoneVocabulary,
    TinyWaveCtc,
    build_proxy_vocabulary,
)


@dataclass(frozen=True, slots=True)
class TrainingConfig:
    epochs: int = 2
    batch_size: int = 4
    learning_rate: float = 0.001
    channels: int = 32
    hidden_size: int = 48
    max_duration_seconds: float = 8.0
    max_train_records_per_speaker: int = 10
    max_eval_records_per_speaker: int = 5
    cpu_threads: int = 8
    seed: int = 20260805

    def __post_init__(self) -> None:
        positive_integers = (
            self.epochs,
            self.batch_size,
            self.channels,
            self.hidden_size,
            self.max_train_records_per_speaker,
            self.max_eval_records_per_speaker,
            self.cpu_threads,
        )
        if any(value <= 0 for value in positive_integers):
            raise ValueError("training integer configuration values must be positive")
        if not math.isfinite(self.learning_rate) or self.learning_rate <= 0:
            raise ValueError("learning_rate must be finite and positive")
        if not math.isfinite(self.max_duration_seconds) or self.max_duration_seconds <= 0:
            raise ValueError("max_duration_seconds must be finite and positive")


@dataclass(frozen=True, slots=True)
class ProxyTrainingResult:
    checkpoint_path: Path
    onnx_path: Path
    manifest_path: Path
    vocabulary_path: Path
    report_path: Path

    def as_dict(self) -> dict[str, str]:
        return {field: str(value) for field, value in asdict(self).items()}


def greedy_ctc_decode(
    token_ids: torch.Tensor,
    lengths: torch.Tensor,
    *,
    blank_index: int,
) -> tuple[tuple[int, ...], ...]:
    """Collapse batched CTC argmax paths using explicit valid frame lengths."""

    if token_ids.ndim != 2 or lengths.ndim != 1 or token_ids.shape[0] != lengths.shape[0]:
        raise ValueError("token_ids must be [batch, frames] with one length per batch item")
    decoded: list[tuple[int, ...]] = []
    for row, raw_length in zip(token_ids, lengths, strict=True):
        length = int(raw_length.item())
        if length < 0 or length > row.shape[0]:
            raise ValueError("decode length exceeds available token frames")
        output: list[int] = []
        previous: int | None = None
        for raw_token in row[:length]:
            token = int(raw_token.item())
            if token != blank_index and token != previous:
                output.append(token)
            previous = token
        decoded.append(tuple(output))
    return tuple(decoded)


def export_proxy_onnx(
    model: TinyWaveCtc,
    output_path: str | Path,
    *,
    example_samples: int = 16000,
) -> ArtifactRecord:
    """Export raw-waveform logits with dynamic sample and frame axes."""

    output = Path(output_path)
    if output.exists():
        raise ValueError("proxy ONNX output exists; refusing to overwrite")
    if example_samples < 400:
        raise ValueError("example_samples must be at least 400")
    output.parent.mkdir(parents=True, exist_ok=True)
    model = model.cpu().eval()
    example = torch.zeros((1, example_samples), dtype=torch.float32)
    with torch.no_grad(), warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=torch.jit.TracerWarning)
        warnings.filterwarnings(
            "ignore",
            message="Exporting a model to ONNX with a batch_size other than 1.*",
            category=UserWarning,
        )
        torch.onnx.export(
            model,
            (example,),
            str(output),
            input_names=["audio"],
            output_names=["logits"],
            dynamic_axes={
                "audio": {0: "batch", 1: "samples"},
                "logits": {0: "batch", 1: "frames"},
            },
            opset_version=17,
            do_constant_folding=True,
            dynamo=False,
        )
    return describe_artifact(output)


def _ctc_required_frames(target: Sequence[int]) -> int:
    repeats = sum(first == second for first, second in pairwise(target))
    return len(target) + repeats


def _filter_ctc_compatible(
    records: Sequence[ProxyIndexRecord],
    *,
    audio_root: Path,
    vocabulary: ProxyPhoneVocabulary,
) -> tuple[ProxyIndexRecord, ...]:
    compatible: list[ProxyIndexRecord] = []
    for record in records:
        with wave.open(str(audio_root / Path(record.audio_rel_path)), "rb") as source:
            target_samples = round(source.getnframes() * 16000 / source.getframerate())
        output_frames = int(
            TinyWaveCtc.output_lengths(torch.tensor([target_samples], dtype=torch.long))[0].item()
        )
        if output_frames >= _ctc_required_frames(vocabulary.encode(record.phonemes)):
            compatible.append(record)
    if not compatible:
        raise ValueError("no selected records satisfy the CTC input/target length constraint")
    return tuple(compatible)


def _load_batch(
    records: Sequence[ProxyIndexRecord],
    *,
    audio_root: Path,
    vocabulary: ProxyPhoneVocabulary,
    max_duration_seconds: float,
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor, torch.Tensor]:
    waveforms = [
        load_mono_pcm16(
            audio_root / Path(record.audio_rel_path),
            max_duration_seconds=max_duration_seconds,
        )
        for record in records
    ]
    targets = [torch.tensor(vocabulary.encode(record.phonemes), dtype=torch.long) for record in records]
    return (
        pad_sequence(waveforms, batch_first=True),
        torch.tensor([waveform.numel() for waveform in waveforms], dtype=torch.long),
        torch.cat(targets),
        torch.tensor([target.numel() for target in targets], dtype=torch.long),
    )


def _batches(
    records: Sequence[ProxyIndexRecord], batch_size: int
) -> tuple[tuple[ProxyIndexRecord, ...], ...]:
    return tuple(
        tuple(records[start : start + batch_size])
        for start in range(0, len(records), batch_size)
    )


def _train_epoch(
    model: TinyWaveCtc,
    optimizer: torch.optim.Optimizer,
    records: Sequence[ProxyIndexRecord],
    *,
    audio_root: Path,
    vocabulary: ProxyPhoneVocabulary,
    config: TrainingConfig,
) -> float:
    model.train()
    total_loss = 0.0
    batch_count = 0
    for batch in _batches(records, config.batch_size):
        audio, input_lengths, targets, target_lengths = _load_batch(
            batch,
            audio_root=audio_root,
            vocabulary=vocabulary,
            max_duration_seconds=config.max_duration_seconds,
        )
        optimizer.zero_grad(set_to_none=True)
        logits = model(audio)
        loss = torch.nn.functional.ctc_loss(
            torch.log_softmax(logits, dim=-1).transpose(0, 1),
            targets,
            model.output_lengths(input_lengths),
            target_lengths,
            blank=vocabulary.blank_index,
            zero_infinity=True,
        )
        if not torch.isfinite(loss):
            raise RuntimeError("proxy CTC training produced a non-finite loss")
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=5.0)
        optimizer.step()
        total_loss += float(loss.detach().item())
        batch_count += 1
    return total_loss / batch_count


def _evaluate_model(
    model: TinyWaveCtc,
    records: Sequence[ProxyIndexRecord],
    *,
    audio_root: Path,
    vocabulary: ProxyPhoneVocabulary,
    config: TrainingConfig,
) -> dict[str, int | float]:
    model.eval()
    total_errors = 0
    total_reference = 0
    exact = 0
    with torch.no_grad():
        for batch in _batches(records, config.batch_size):
            audio, input_lengths, targets, target_lengths = _load_batch(
                batch,
                audio_root=audio_root,
                vocabulary=vocabulary,
                max_duration_seconds=config.max_duration_seconds,
            )
            logits = model(audio)
            predictions = greedy_ctc_decode(
                logits.argmax(dim=-1),
                model.output_lengths(input_lengths),
                blank_index=vocabulary.blank_index,
            )
            target_offset = 0
            for prediction, raw_target_length in zip(predictions, target_lengths, strict=True):
                target_length = int(raw_target_length.item())
                reference = tuple(
                    int(value.item())
                    for value in targets[target_offset : target_offset + target_length]
                )
                target_offset += target_length
                errors = edit_distance(reference, prediction)
                total_errors += errors
                total_reference += len(reference)
                exact += int(errors == 0)
    return {
        "record_count": len(records),
        "reference_units": total_reference,
        "total_errors": total_errors,
        "phone_unit_error_rate": total_errors / total_reference,
        "exact_sequence_accuracy": exact / len(records),
    }


def train_proxy_model(
    *,
    train_index: str | Path,
    validation_index: str | Path,
    test_index: str | Path,
    audio_root: str | Path,
    output_dir: str | Path,
    report_path: str | Path,
    corpus_manifest_digest: str,
    dataset_revision: str,
    config: TrainingConfig,
    progress: Callable[[dict[str, Any]], None] | None = None,
) -> ProxyTrainingResult:
    """Train, evaluate, checkpoint, and export a bounded CPU proxy experiment."""

    if len(corpus_manifest_digest) != 64:
        raise ValueError("corpus_manifest_digest must be a SHA-256 hex digest")
    root = Path(audio_root)
    selected_train = select_available_records(
        train_index,
        audio_root=root,
        max_records_per_speaker=config.max_train_records_per_speaker,
        max_duration_seconds=config.max_duration_seconds,
    )
    selected_validation = select_available_records(
        validation_index,
        audio_root=root,
        max_records_per_speaker=config.max_eval_records_per_speaker,
        max_duration_seconds=config.max_duration_seconds,
    )
    selected_test = select_available_records(
        test_index,
        audio_root=root,
        max_records_per_speaker=config.max_eval_records_per_speaker,
        max_duration_seconds=config.max_duration_seconds,
    )
    vocabulary = build_proxy_vocabulary(tuple(record.phonemes for record in selected_train))
    train_records = _filter_ctc_compatible(
        selected_train, audio_root=root, vocabulary=vocabulary
    )
    validation_records = _filter_ctc_compatible(
        selected_validation, audio_root=root, vocabulary=vocabulary
    )
    test_records = _filter_ctc_compatible(selected_test, audio_root=root, vocabulary=vocabulary)

    output = Path(output_dir)
    result = ProxyTrainingResult(
        checkpoint_path=output / "ta-proxy-phone-ctc.pt",
        onnx_path=output / "ta-proxy-phone-ctc-fp32.onnx",
        manifest_path=output / "ta-proxy-phone-ctc.manifest.json",
        vocabulary_path=output / "ta-proxy-phone-vocabulary.json",
        report_path=Path(report_path),
    )
    if any(path.exists() for path in asdict(result).values()):
        raise ValueError("proxy training output exists; use a clean output/report path")
    output.mkdir(parents=True, exist_ok=True)
    result.report_path.parent.mkdir(parents=True, exist_ok=True)

    torch.manual_seed(config.seed)
    torch.set_num_threads(config.cpu_threads)
    model = TinyWaveCtc(
        len(vocabulary.tokens),
        channels=config.channels,
        hidden_size=config.hidden_size,
    )
    optimizer = torch.optim.Adam(model.parameters(), lr=config.learning_rate)
    training_records = list(train_records)
    history: list[dict[str, int | float]] = []
    for epoch in range(1, config.epochs + 1):
        random.Random(config.seed + epoch).shuffle(training_records)
        train_loss = _train_epoch(
            model,
            optimizer,
            training_records,
            audio_root=root,
            vocabulary=vocabulary,
            config=config,
        )
        validation = _evaluate_model(
            model,
            validation_records,
            audio_root=root,
            vocabulary=vocabulary,
            config=config,
        )
        epoch_record: dict[str, int | float] = {
            "epoch": epoch,
            "train_ctc_loss": train_loss,
            "validation_phone_unit_error_rate": validation["phone_unit_error_rate"],
        }
        history.append(epoch_record)
        if progress is not None:
            progress(epoch_record)

    validation_report = _evaluate_model(
        model,
        validation_records,
        audio_root=root,
        vocabulary=vocabulary,
        config=config,
    )
    test_report = _evaluate_model(
        model,
        test_records,
        audio_root=root,
        vocabulary=vocabulary,
        config=config,
    )
    torch.save(
        {
            "state_dict": model.state_dict(),
            "training_config": asdict(config),
            "vocabulary": vocabulary.tokens,
            "model_evidence_scope": "trained_proxy_tamil_phoneme_model",
        },
        result.checkpoint_path,
    )
    onnx_record = export_proxy_onnx(model, result.onnx_path)
    manifest = ModelManifest(
        schema_version="1.0",
        model_version="ta-proxy-phone-ctc-0.1.0",
        vocabulary_version="ta-proxy-phone-units-0.1.0",
        sha256=onnx_record.sha256,
        sample_rate=16000,
        frame_shift_ms=20.0,
        blank_index=vocabulary.blank_index,
        vocabulary_size=len(vocabulary.tokens),
        input_name="audio",
        output_name="logits",
        output_kind="logits",
    )
    result.manifest_path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2), encoding="utf-8"
    )
    result.vocabulary_path.write_text(
        json.dumps(
            {
                "version": manifest.vocabulary_version,
                "blank_token": "<blank>",
                "unknown_token": "<unk>",
                "tokens": list(vocabulary.tokens),
                "unit_type": "unicode_codepoint_proxy_not_expert_phoneme_inventory",
                "review_status": "not_tamil_expert_approved",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    report = {
        "schema_version": "1.0",
        "evidence_scope": "engineering_proxy",
        "model_evidence_scope": "trained_proxy_tamil_phoneme_model",
        "population": "adult_tamil_proxy",
        "calibration_status": "not_therapist_calibrated",
        "dataset_revision": dataset_revision,
        "corpus_manifest_digest": corpus_manifest_digest,
        "training_config": asdict(config),
        "torch_version": torch.__version__,
        "torchaudio_version": torchaudio.__version__,
        "device": "cpu",
        "architecture": "raw-waveform-conv-bigru-ctc",
        "parameter_count": sum(parameter.numel() for parameter in model.parameters()),
        "vocabulary_size": len(vocabulary.tokens),
        "unit_type": "unicode_codepoint_proxy_not_expert_phoneme_inventory",
        "split_counts": {
            "train": len(train_records),
            "validation": len(validation_records),
            "test": len(test_records),
        },
        "split_speaker_counts": {
            "train": len({record.speaker for record in train_records}),
            "validation": len({record.speaker for record in validation_records}),
            "test": len({record.speaker for record in test_records}),
        },
        "history": history,
        "validation": validation_report,
        "test": test_report,
        "onnx_sha256": onnx_record.sha256,
        "onnx_size_bytes": onnx_record.size_bytes,
        "limitations": [
            "adult proxy speech only",
            "small bounded subset",
            "proxy Unicode units are not a Tamil-expert-approved phoneme inventory",
            "no therapist calibration or target-user validation",
            "no target-tablet measurements",
        ],
    }
    result.report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Train a bounded CPU Tamil proxy phone-unit CTC technical prototype."
    )
    parser.add_argument("--prepared-dir", required=True, type=Path)
    parser.add_argument("--audio-root", required=True, type=Path)
    parser.add_argument("--corpus-manifest", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=0.001)
    parser.add_argument("--channels", type=int, default=32)
    parser.add_argument("--hidden-size", type=int, default=48)
    parser.add_argument("--max-duration-seconds", type=float, default=8.0)
    parser.add_argument("--max-train-records-per-speaker", type=int, default=10)
    parser.add_argument("--max-eval-records-per-speaker", type=int, default=5)
    parser.add_argument("--cpu-threads", type=int, default=8)
    parser.add_argument("--seed", type=int, default=20260805)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    corpus = CorpusManifest.from_json(args.corpus_manifest)
    if corpus.evidence_scope != "engineering_proxy":
        raise ValueError("this command accepts only engineering_proxy corpus manifests")
    config = TrainingConfig(
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.learning_rate,
        channels=args.channels,
        hidden_size=args.hidden_size,
        max_duration_seconds=args.max_duration_seconds,
        max_train_records_per_speaker=args.max_train_records_per_speaker,
        max_eval_records_per_speaker=args.max_eval_records_per_speaker,
        cpu_threads=args.cpu_threads,
        seed=args.seed,
    )
    result = train_proxy_model(
        train_index=args.prepared_dir / "train.index.jsonl",
        validation_index=args.prepared_dir / "validation.index.jsonl",
        test_index=args.prepared_dir / "test.index.jsonl",
        audio_root=args.audio_root,
        output_dir=args.output_dir,
        report_path=args.report,
        corpus_manifest_digest=corpus.digest(),
        dataset_revision=corpus.revision,
        config=config,
        progress=lambda record: print(json.dumps(record), flush=True),
    )
    print(json.dumps(result.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
