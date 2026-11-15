# Mobile Phoneme Implementation Plan

> Execute inline with superpowers:executing-plans; authorization was given in this chat.

**Goal:** Fine-tune the saved mobile encoder for audio-derived phoneme tokens on the local GPU, test synthetic robustness, and integrate the ONNX candidate into Android.
**Architecture:** Transferred convolutional encoder with reduced strides, BiGRU CTC, fixed 48,000-sample waveform and logits output. Preserve source speaker splits and provisional labels.
**Tech Stack:** Python 3.12, PyTorch 2.6 CUDA 12.4, NumPy, soundfile, ONNX Runtime; Kotlin/Compose/Android ORT.
**Spec:** ../specs/2026-11-11-mobile-phoneme-design.md

## Global Constraints
- Keep datasets, weights, generated WAVs and environment on D: outside Git.
- Preserve all unrelated dirty lab files; existing worktree codex/backend-verification-lab is isolated from main.
- Predictions must be derived from audio, not expected-word lookup; no child scoring approval.
- No evaluation examples or derivatives used for training or selection.

## Tasks
- [x] Add failing Python tests for transferred weights, temporal output, repeat/blank CTC decoding, label coverage, split leakage, normalization and synthetic determinism.
- [x] Implement backend/app/vaakmitra_word/phoneme_ctc.py and scripts/model/finetune_mobile_phoneme.py, run tests, install isolated CUDA environment and verify backward pass.
- [x] Freeze dataset/vocabulary/run configuration, train selected checkpoint, record calibration and held-out token metrics; generate and evaluate synthetic WAVs.
- [x] Export ONNX variants, compare decoded sequences and select mobile artifact with hash-bound bundle.json.
- [x] Add Android PhonemeCtcDecoder and OnnxMobilePhoneme, tests, integrate transient token results into existing local practice path without changing score approvals.
- [x] Run focused backend tests, Android unit/lint/build and device execution when available; update SSOT and project context with actual evidence and limitations.

## Review Focus
Audio/target leakage; syllable length and repeated token decoding; invalid/silent input; missing/corrupt bundle; mismatch between desktop and Android preprocessing.

