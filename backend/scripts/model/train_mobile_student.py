"""Train the DEC-028 raw-waveform word student on frozen adult/public data."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
from pathlib import Path
import random
import sys

import numpy as np
import torch
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler


BACKEND_ROOT = Path(__file__).resolve().parents[2]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.vaakmitra_word.mobile_student_data import (  # noqa: E402
    MOBILE_LABELS,
    MobileSample,
    TeacherTargetIndex,
    augment_mobile_channel,
    load_mobile_samples,
    preprocess_pcm16,
    read_pcm16_wav,
)
from app.vaakmitra_word.mobile_student_model import MobileWordStudent, student_loss  # noqa: E402


@dataclass(frozen=True)
class EpochResult:
    epoch: int
    train_loss: float
    calibration_accuracy: float


class WaveDataset(Dataset[tuple[torch.Tensor, torch.Tensor, torch.Tensor]]):
    def __init__(self, samples: list[MobileSample], teacher: TeacherTargetIndex, *, augment: bool) -> None:
        self.samples = samples
        self.teacher = teacher
        self.augment = augment
        self.label_index = {label: index for index, label in enumerate(MOBILE_LABELS)}

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        sample = self.samples[index]
        waveform = preprocess_pcm16(read_pcm16_wav(sample.audio_path))
        if self.augment:
            augmentation_seed = int(torch.randint(0, 2**31 - 1, (1,)).item())
            waveform = augment_mobile_channel(waveform, seed=augmentation_seed)
        teacher = self.teacher.probabilities_for(sample.sample_id)
        if teacher is None:
            teacher = np.zeros(len(MOBILE_LABELS), dtype=np.float32)
            teacher[self.label_index[sample.label]] = 1.0
        return (
            torch.from_numpy(waveform),
            torch.tensor(self.label_index[sample.label], dtype=torch.long),
            torch.from_numpy(teacher),
        )


def _seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    torch.use_deterministic_algorithms(True, warn_only=True)


@torch.no_grad()
def _accuracy(model: MobileWordStudent, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = total = 0
    for waveform, labels, _ in loader:
        predictions = model(waveform.to(device))[1].argmax(dim=1).cpu()
        correct += int((predictions == labels).sum())
        total += labels.numel()
    return correct / max(total, 1)


def _hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--audio-root", type=Path, required=True)
    parser.add_argument("--classifier", type=Path, required=True)
    parser.add_argument("--embedding-root", type=Path, required=True)
    parser.add_argument("--teacher-targets", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--epochs", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--learning-rate", type=float, default=0.002)
    parser.add_argument("--seed", type=int, default=1701)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    _seed_everything(args.seed)

    # The preparation gate already verified presence/hashes. Avoid 15k extra
    # cross-filesystem stat calls in WSL; decode still fails closed per sample.
    all_samples = load_mobile_samples(args.manifest, args.audio_root, verify_hashes=False, verify_files=False)
    teacher = (
        TeacherTargetIndex.load(args.teacher_targets)
        if args.teacher_targets is not None
        else TeacherTargetIndex.from_artifacts(args.classifier, sorted(args.embedding_root.glob("shard-*.npz")))
    )
    if teacher.labels != MOBILE_LABELS:
        raise RuntimeError("teacher_label_order_mismatch")
    train_samples = [sample for sample in all_samples if sample.split == "train"]
    calibration_samples = [sample for sample in all_samples if sample.split == "calibration"]
    counts = Counter(sample.label for sample in train_samples)
    sample_weights = [1.0 / counts[sample.label] for sample in train_samples]
    generator = torch.Generator().manual_seed(args.seed)
    sampler = WeightedRandomSampler(sample_weights, num_samples=len(train_samples), replacement=True, generator=generator)
    train_loader = DataLoader(
        WaveDataset(train_samples, teacher, augment=True),
        batch_size=args.batch_size,
        sampler=sampler,
        num_workers=args.workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=args.workers > 0,
    )
    calibration_loader = DataLoader(
        WaveDataset(calibration_samples, teacher, augment=False),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=args.workers,
        pin_memory=torch.cuda.is_available(),
        persistent_workers=args.workers > 0,
    )
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = MobileWordStudent().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=1e-4)
    history: list[EpochResult] = []
    best_accuracy = -1.0
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output_dir / "mobile_word_student.pt"
    for epoch in range(1, args.epochs + 1):
        model.train()
        running_loss = 0.0
        seen = 0
        for waveform, labels, teacher_probabilities in train_loader:
            waveform = waveform.to(device, non_blocking=True)
            labels = labels.to(device, non_blocking=True)
            teacher_probabilities = teacher_probabilities.to(device, non_blocking=True)
            optimizer.zero_grad(set_to_none=True)
            logits = model(waveform)[1]
            loss = student_loss(logits, labels, teacher_probabilities)
            loss.backward()
            optimizer.step()
            running_loss += float(loss.detach()) * labels.numel()
            seen += labels.numel()
        calibration_accuracy = _accuracy(model, calibration_loader, device)
        result = EpochResult(epoch, running_loss / max(seen, 1), calibration_accuracy)
        history.append(result)
        print(json.dumps(asdict(result), sort_keys=True), flush=True)
        if calibration_accuracy > best_accuracy:
            best_accuracy = calibration_accuracy
            torch.save({"model": model.state_dict(), "labels": MOBILE_LABELS, "seed": args.seed}, checkpoint)

    report = {
        "schema_version": "vaakmitra-mobile-student-training-2",
        "requirements": ["DEC-028", "DEC-029", "MST-003", "MST-004", "MST-011", "MST-012", "MST-013"],
        "device": str(device),
        "labels": list(MOBILE_LABELS),
        "seed": args.seed,
        "epochs": args.epochs,
        "batch_size": args.batch_size,
        "train_samples": len(train_samples),
        "calibration_samples": len(calibration_samples),
        "evaluation_opened": False,
        "architecture_version": "raw-wave-temporal8-dc-rms-v1",
        "augmentation_version": "mobile-channel-mild65-strong35-time75-225-echo400-v4",
        "best_calibration_accuracy": best_accuracy,
        "history": [asdict(item) for item in history],
        "checkpoint_sha256": _hash(checkpoint),
    }
    (args.output_dir / "training-report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
