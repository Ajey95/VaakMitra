# VaakMitra

VaakMitra is the ASD-Edge-ST 2.0 offline-first Tamil speech-practice project.

This branch implements only Backend Member 2's local speech-intelligence scope:

- Tamil-aware acoustic-model runtime contracts;
- phoneme-level CTC probability validation;
- GOP, confidence, and syllable scoring;
- ONNX model integrity and local inference support;
- edge export, quantization, benchmark, and model-card tooling;
- explicit test-only Member 1 alignment and Member 3 action mocks;
- provisional Tamil IPA, research-source preflight, and teacher-feature preparation; and
- structured ONNX Runtime mobile-usability auditing.

See `docs/superpowers/specs/2026-08-02-member2-speech-intelligence-design.md` for the approved design.

## Training-first Colab handoff

The seven-day path prioritizes a resumable AI4Bharat IndicConformer phoneme-head reference model
before optional student distillation. The committed Colab notebook runs a measured GPU canary,
head-only training and export, gated adaptive stages, and write-once reference evidence. Start with
`docs/verification/training-first-colab-preflight.md`. Local tests prove orchestration and exact
resume behavior; they do not prove that the external Colab GPU run or clinical validation is done.

## Repository layout

```text
backend/      Runtime package, contracts, scoring logic, and automated tests
modeling/     Training boundary, export adapters, quantization, and comparison tools
benchmarks/   Reproducible latency and memory benchmark runner and reports
docs/         Architecture, integration contracts, design, and implementation plan
```

## Development setup

```powershell
py -3.11 -m venv .venv
& .\.venv\Scripts\python.exe -m pip install -e '.\backend[dev,model]'
& .\.venv\Scripts\python.exe -m pytest backend\tests -q
```

## Quality gates

```powershell
& .\.venv\Scripts\python.exe -m ruff check backend\src backend\tests modeling benchmarks
& .\.venv\Scripts\python.exe -m mypy backend\src modeling benchmarks
& .\.venv\Scripts\python.exe -m build backend
```

## Model lifecycle commands

All commands run locally. Model and audio artifacts are ignored by Git.

```powershell
# Export through an approved project adapter implementing (checkpoint_path, output_path) -> None
& .\.venv\Scripts\python.exe -m modeling.export.export_onnx `
  --adapter package.module:export_function `
  --checkpoint modeling\artifacts\teacher.nemo `
  --output modeling\artifacts\ta-phoneme-ctc-fp32.onnx

# Create a separate dynamic INT8 model
& .\.venv\Scripts\python.exe -m modeling.quantization.quantize_onnx `
  --input modeling\artifacts\ta-phoneme-ctc-fp32.onnx `
  --output modeling\artifacts\ta-phoneme-ctc-int8.onnx

# Benchmark synthetic or separately approved non-sensitive audio
& .\.venv\Scripts\python.exe -m benchmarks.run_benchmark `
  --model modeling\artifacts\ta-phoneme-ctc-fp32.onnx `
  --manifest modeling\artifacts\ta-phoneme-ctc.manifest.json `
  --audio-npy benchmarks\fixtures\approved_word.npy `
  --output benchmarks\reports\development-laptop.json
```

## Proxy-data fallback

When therapist-labelled child recordings and the target tablet are unavailable, the repository can
still produce honest engineering evidence:

```powershell
# Install the pinned CPU training stack
& .\.venv\Scripts\python.exe -m pip install `
  --requirement modeling\training\requirements-cpu.txt

# Validate and re-split the CC0 adult-Tamil manifests without speaker leakage
& .\.venv\Scripts\python.exe -m modeling.data.prepare_tamil_tts_proxy --help

# Train/export the bounded adult proxy experiment
& .\.venv\Scripts\python.exe -m modeling.training.train_proxy_ctc --help

# Reproduce the fully synthetic FP32/INT8/runtime/benchmark evidence chain
& .\.venv\Scripts\python.exe -m modeling.fixtures.run_prototype_flow --help

# Exercise Member 2 between explicit test-only Member 1 and Member 3 mocks
& .\.venv\Scripts\python.exe -m modeling.team_mocks.run_mocked_pipeline `
  --report benchmarks\reports\member2-mocked-three-member-evidence.json

# Generate a provisional Epitran-based inventory from an approved UTF-8 word list
& .\.venv\Scripts\python.exe -m modeling.inventory.generate_inventory --help

# Audit the current ONNX graph statically for mobile execution-provider compatibility
& .\.venv\Scripts\python.exe -m modeling.mobile.usability_audit `
  --model modeling\artifacts\proxy-trained-small-v1\ta-proxy-phone-ctc-int8.onnx `
  --output benchmarks\reports\proxy-int8-mobile-usability.json
```

Recorded aggregate evidence is under `benchmarks/reports/`. Real audio, checkpoints, ONNX weights,
waveform arrays, speaker-level indices, and probability matrices remain ignored by Git. The current
adult proxy model has a 98.20% phone-unit error rate and therefore must not score child speech.

The mocked three-member command validates contract plumbing only. Its deterministic alignment and
action adapters are non-production fixtures; they do not prove forced-alignment accuracy, adaptive
therapy behavior, persistence, synchronization, clinical validity, or teammate acceptance.

`modeling/configs/tamil_research_sources.json` pins IndicVoices, Vistaar, and IISc-MILE/OpenSLR 127
research metadata and
fails closed on gated access, adult-only claims, and unresolved dataset licensing. The pinned
IndicConformer configuration and teacher-feature cache package preserve local-only, hash-linked
feature tensors; they do not download data or claim direct phoneme posterior support.

The checked-in mobile audit is static graph analysis, not a tablet benchmark. The current INT8
model has only 8 of 51 nodes supported by NNAPI as-is across 5 partitions, so the recorded
recommendation is `CPUExecutionProvider`. Physical-tablet latency, memory, battery, and thermal
measurements remain unavailable.

The checked-in phoneme vocabulary and model configuration are contract examples. They are not a
Tamil-expert-approved production inventory or a clinically validated pronunciation model.

## Dual-track CPU implementation

Everything that does not require a real CUDA training job is implemented and executable locally.
Strategy 1 is the distilled edge student; Strategy 2 is the full IndicConformer reference. Run the
credential-safe environment gate and deterministic CPU smokes with:

```powershell
& .\.venv\Scripts\python.exe -m modeling.teacher.run_preflight `
  --config modeling\configs\indicconformer_teacher.json --mode cpu_smoke
& .\.venv\Scripts\python.exe -m modeling.training.smoke_full_track `
  --output benchmarks\reports\full-track-cpu-smoke.json
& .\.venv\Scripts\python.exe -m modeling.training.smoke_student_track `
  --output benchmarks\reports\student-track-cpu-smoke.json
& .\.venv\Scripts\python.exe -m modeling.release.compare_dual_tracks `
  --input modeling\manifests\dual-track-cpu-comparison.example.json `
  --output benchmarks\reports\dual-track-cpu-comparison.json
```

The recorded comparison intentionally selects no model: adult-Tamil quality/calibration metrics,
the real teacher checkpoint, CUDA training, INT8 PER/GOP evidence, and physical Android timing are
not measured. Missing evidence is represented as `not_measured`, never as a pass.
