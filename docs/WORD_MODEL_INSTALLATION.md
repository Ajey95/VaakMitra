# VaakMitra Tamil word-model installation

Status: operator runbook. Normative product requirements remain in [`VAAKMITRA_FINAL_SSOT.md`](../VAAKMITRA_FINAL_SSOT.md).

## Safety boundary

VaakMitra V1 is a supervised, non-diagnostic Tamil word-practice technical prototype for autistic children aged 7–14. The application must remain usable when scoring is unavailable. Never enable `PASS` from an unverified model, hand-written threshold, synthetic artifact, browser transcript, phoneme score, or voice-conversion output.

The application never downloads a model at runtime. Install all artifacts on the private GPU edge workstation before a session. Do not put child recordings in the artifact bundle.

## Required bundle

Create one operator-controlled directory outside Git, for example `D:\VaakMitraModels\ta-word-v1`:

```text
ta-word-v1/
  bundle.json
  MODEL_PROVENANCE.md
  upstream/
    README.md
    indicconformer_stt_ta_hybrid_rnnt_large.nemo
  vocabulary.json
  word-classifier.npz
  reference-bank.npz
  calibration.json
  dataset-manifest.jsonl
  canary-suite.json
  canary-run.json
```

The selected acoustic starting point is AI4Bharat's approximately 120M-parameter Tamil hybrid CTC/RNNT IndicConformer. The upstream project and model card identify it as MIT licensed, but access conditions and every third-party dependency/container license still apply. Record the exact upstream revision and archive its license beside the deployment evidence. Repository ownership only resolves rights to the reused application code; it does not waive third-party terms.

The checkpoint installed on 2026-09-06 is the 523,192,320-byte file from Hugging Face revision `8c31aa8d04964b8fc87e4eaaee7916f7d2c024da`, with SHA-256 `40a6fce3374ceb67daa2a071e92f0948c51c6a95b734d4881a3bcfe0b1bed32a`. Its local path is `D:\VaakMitraModels\ta-word-v1\upstream\indicconformer_stt_ta_hybrid_rnnt_large.nemo`; `MODEL_PROVENANCE.md` records the installation evidence. Artifact acquisition, CUDA restore, encoder execution, and one labeled adult Tamil smoke inference are now proven; see [`GPU_INFERENCE_EVIDENCE.md`](GPU_INFERENCE_EVIDENCE.md). This does not prove production-bundle readiness, child-speech accuracy, calibration, latency distribution, or clinical validity.

Install a CUDA-matched PyTorch build first in an isolated Linux Python 3.10 environment, then install `backend/requirements-core.txt` and `backend/requirements-model.txt`. The pinned AI4Bharat source declares Python 3.10 and depends on Linux-oriented GPU packages, so native Windows Python is not the supported edge runtime; use private WSL2 or a Linux CUDA container. The model card requires AI4Bharat's `nemo-v2` fork, so the model requirements pin branch revision `8dce88cf8e94963e2033c3137f7b9993b51db88a` instead of assuming stock NVIDIA NeMo compatibility. Freeze the working Python, driver, CUDA, PyTorch, NeMo, and GPU versions in the evidence ledger; do not upgrade them during a validated trial.

## Artifact formats

`vocabulary.json`:

```json
{
  "version": "ta-core-1.0.0",
  "words": {
    "TA_00021": "அம்மா",
    "TA_00022": "அப்பா"
  }
}
```

`word-classifier.npz` is loaded with `allow_pickle=false`. The current trainer stores `mean-std-v1` pooling, train-only feature means/scales, a calibrated temperature, stable labels containing every active word plus `OTHER`, and finite weights/bias. The classifier, vocabulary, and model hashes must agree.

`reference-bank.npz` is loaded with `allow_pickle=false` and preserves the accepted reference ID, speaker pseudonym, source ID, quality score, model hash, vocabulary hash, and dataset-manifest hash. An active word needs 32–64 approved adult references from at least eight speakers, no more than four per speaker. Only approved adult/reference embeddings belong here—never session-derived child embeddings.

`calibration.json` follows `CalibrationArtifact` in `backend/app/vaakmitra_word/calibration.py` and binds the exact model, vocabulary, classifier, reference-bank, and dataset-manifest hashes. Adult-only engineering calibration is always `approved: false`. Production requires a separate child-separated therapist-labelled artifact with `approved: true` after SSOT Sections 17–19 pass.

`canary-suite.json` covers every active word plus confusable and invalid-audio cases. Every entry binds its audio hash, exact expected decision/reason constraints, permitted-use basis, and reviewer. `canary-run.json` binds the exact suite hash, every result, and latency percentiles. Technical acceptance and human approval are independent; production requires both.

`bundle.json` contains only relative paths so a bundle cannot escape its own directory:

```json
{
  "schema_version": "vaakmitra-word-bundle-2",
  "deployment_mode": "engineering",
  "vocabulary_version": "ta-core-1.0.0",
  "artifacts": {
    "model": {"path": "upstream/indicconformer_stt_ta_hybrid_rnnt_large.nemo", "sha256": "40a6fce3374ceb67daa2a071e92f0948c51c6a95b734d4881a3bcfe0b1bed32a"},
    "vocabulary": {"path": "vocabulary.json", "sha256": "<64 hex>"},
    "classifier": {"path": "word-classifier.npz", "sha256": "<64 hex>"},
    "reference_bank": {"path": "reference-bank.npz", "sha256": "<64 hex>"},
    "calibration": {"path": "calibration.json", "sha256": "<64 hex>"},
    "dataset_manifest": {"path": "dataset-manifest.jsonl", "sha256": "<64 hex>"},
    "canary_manifest": {"path": "canary-suite.json", "sha256": "<64 hex>"},
    "canary_run": {"path": "canary-run.json", "sha256": "<64 hex>"}
  },
  "release": {
    "code_commit": "<40 lowercase hex>",
    "rollback_bundle_hash": "<64 lowercase hex>",
    "signing_input_sha256": "<computed by build_bundle.py>"
  }
}
```

Compute hashes locally in PowerShell:

```powershell
Get-FileHash -Algorithm SHA256 D:\VaakMitraModels\ta-word-v1\* | Format-Table Path, Hash
```

Populate internal cross-hashes first, then hash the completed files and populate `bundle.json`. Any later byte change intentionally invalidates the release.

## Verify and start

From `backend`:

```powershell
python scripts\verify_artifacts.py --config D:\VaakMitraModels\ta-word-v1\bundle.json --json --allow-engineering
$env:VAAKMITRA_BUNDLE_CONFIG = 'D:\VaakMitraModels\ta-word-v1\bundle.json'
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Without `--allow-engineering`, the verifier returns exit code `0` only for a structurally valid, internally compatible production bundle. The opt-in flag returns zero for an integrity-complete engineering bundle while its JSON still reports `ready=false`; it never activates the API service.

On startup, the server restores the local NeMo model, runs the hashed end-to-end canary, and refuses to attach the assessment service unless the canary returns `PASS`. Confirm both endpoints before any supervised session:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health/live
Invoke-RestMethod http://127.0.0.1:8000/health/scoring
```

Then run the wider approved adult canary set and record input hashes, outputs, latency, GPU/VRAM, and process logs. The startup canary is necessary but does not replace the release canary set, privacy packet capture, device integration, or target-child clinical validation.

## Rollback

Keep the prior immutable bundle in a sibling directory. To roll back, stop accepting sessions, stop the API, point `VAAKMITRA_BUNDLE_CONFIG` to the prior verified `bundle.json`, restart one worker, rerun both health checks and the canary set, and record the rollback. Never overwrite files inside an approved bundle.
