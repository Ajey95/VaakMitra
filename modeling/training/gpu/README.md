# GPU execution runbook: Tamil phoneme transfer and distillation

This directory freezes the GPU strategy without claiming that GPU training has already run. The
current Windows host has no CUDA device, and the teacher repository is gated. A real run begins
only after the user accepts the model conditions, obtains the `.nemo` snapshot, and validates the
loaded module names against the adapter assumptions.

The upstream Tamil checkpoint is a 120M-parameter, 17-block, 512-dimensional hybrid CTC/RNNT
IndicConformer. Its published output is text, not phonemes. Therefore this project reuses encoder
representations, discards the text decoder for this experiment, and trains a new CTC head whose
index-zero blank and vocabulary come only from the expert-reviewed Tamil inventory. Text-posterior
KL distillation is prohibited.

## 1. Create the pinned environment

Use Linux, a Linux cloud instance, or WSL2 with an NVIDIA driver. The environment values follow the
AI4Bharat fork's Python/PyTorch requirements and the CUDA/PyTorch combination documented by
NVIDIA. `environment.yaml` uses JSON syntax, which is valid YAML and easy to validate exactly.

```bash
conda create -n vaakmitra-gpu python=3.10.12 -y
conda activate vaakmitra-gpu
conda install pytorch==2.2.0 torchaudio==2.2.0 pytorch-cuda=12.1 \
  -c pytorch -c nvidia -y
conda install ffmpeg libsndfile -c conda-forge -y

git clone https://github.com/AI4Bharat/NeMo.git external/ai4bharat-nemo
cd external/ai4bharat-nemo
git checkout --detach 8dce88cf8e94963e2033c3137f7b9993b51db88a
python -m pip install -e ".[asr]"
cd ../..
python -c "import torch,nemo; assert torch.cuda.is_available(); print(torch.cuda.get_device_name())"
```

Authenticate interactively with Hugging Face after accepting the Tamil model's access conditions.
Never put a token in a command, configuration, log, notebook, or repository. Confirm that revision
`8c31aa8d04964b8fc87e4eaaee7916f7d2c024da` can be downloaded, then save its file SHA-256 in the
private run manifest.

## 2. Stage the immutable inputs

Copy these private artifacts to encrypted GPU storage:

- expert-reviewed inventory JSON and SHA-256;
- frozen OpenSLR private train/validation/test manifests;
- aggregate frozen corpus index and SHA-256;
- locally computed source-archive SHA-256;
- the exact repository commit and a clean code snapshot.

Replace every `REQUIRED_PATH` and `REQUIRED_64_HEX` in a private copy of
`full-reference.yaml`. The launch script refuses placeholders, missing paths, digest mismatches,
absent gated-access acknowledgement, or `torch.cuda.is_available() == false`.

Before training, load one utterance and record the actual encoder module path, the 17 block names,
representation shape, padding-mask semantics, and checkpoint SHA. This adapter probe cannot be
completed accurately without access to the gated artifact; do not guess those internal names from
the model card.

## 3. Reference-model transfer schedule

Use `full-reference.yaml` without changing the predeclared split or promotion metric:

1. `head_only`: freeze the entire IndicConformer encoder and train the phoneme CTC head at `1e-3`.
2. `top_encoder_blocks`: unfreeze exactly the final four blocks; use encoder LR `1e-5` and head LR
   `1e-4`.
3. `full_encoder`: optional, only if validation PER improves by at least `0.005`; use encoder LR
   `1e-6` and head LR `5e-5`.

Use BF16 where the GPU supports it, FP16 otherwise, gradient norm clipping `1.0`, seed `17`, and
save last plus the best three validation-PER checkpoints every epoch. Resume only when code,
inventory, corpus-index, split, model, and optimizer hashes match the prior run manifest.

The PowerShell wrapper performs all non-model-specific gates and then calls the reviewed GPU driver:

```powershell
& modeling\training\gpu\run_stages.ps1 `
  -Config modeling\artifacts\gpu\full-reference.private.yaml `
  -Python python -AccessAuthorized `
  -GpuTrainingCommand modeling/training/gpu/train_reference_gpu.py
```

`train_reference_gpu.py` is intentionally not fabricated in this CPU deliverable: its encoder
adapter must be written and tested after the gated checkpoint probe reveals the real AI4Bharat NeMo
object contract. Everything before that boundary—data, hashes, vocabulary, stage schedule, gates,
and evaluation contract—is finalized here.

Engineering starting points are a 24 GB GPU for head/top-block work and a 40 GB GPU if full
unfreezing is needed. These are capacity estimates, not guarantees: begin with batch size 1,
gradient accumulation, and activation checkpointing, then record measured peak VRAM before raising
the batch size.

## 4. Teacher representations and students

After selecting the best validation-PER reference checkpoint, extract local-only encoder
representations for the same immutable utterance manifests. Each feature shard and the feature
manifest must bind teacher checkpoint SHA, inventory SHA, corpus-index SHA, split, layer, dtype,
shape, padding mask, and shard SHA. Do not upload audio-derived features to a public service.

Train both candidates with identical splits and objective weights:

- supervised phoneme CTC: `1.0`;
- masked Smooth-L1 representation matching: `0.5`;
- relational frame-similarity loss: `0.2`;
- sequence-consistency loss: `0.1`;
- text-posterior KL: disabled and prohibited.

```powershell
& modeling\training\gpu\run_distillation.ps1 `
  -FeatureManifest modeling\artifacts\gpu\teacher-features\manifest.json `
  -FeatureManifestSha256 <64-LOWERCASE-HEX> `
  -Python python `
  -GpuTrainingCommand modeling/training/gpu/train_student_gpu.py
```

Compare compact Conformer and Conv-BiGRU on adult-proxy test PER first. A candidate may proceed to
ONNX/INT8 evaluation only if its relative PER degradation versus the teacher is at most 10%. The
tie-breakers are quantized size and then physical-tablet P95. The 50 MB and 500 ms values are gates,
not results; they remain unpassed until a real quantized artifact and physical tablet report exist.

## 5. Metrics, recovery, and handoff

For every run, retain validation/test PER plus substitution, deletion, and insertion rates; epoch,
optimizer, scaler, RNG, and sampler state; stdout/stderr; `nvidia-smi`; package freeze; and SHA-256
for every checkpoint and result. Upload only encrypted private artifacts, verify their hashes after
transfer, and resume from `last` only after the run-manifest equality check.

If loss becomes non-finite, preserve the failing checkpoint and batch metadata without raw audio,
then stop. If CUDA OOM occurs, lower batch size before changing the architecture. If the full stage
does not clear its validation gate, keep the top-block checkpoint and do not force full unfreezing.
Adult Tamil PER is engineering evidence only; it cannot establish child/ASD accuracy, therapist
calibration, or clinical readiness.

## 6. Google Colab notebook

`notebooks/VaakMitra_GPU_Training_Colab.ipynb` is the Colab implementation of both GPU tracks. It
uses the pinned model, NeMo revision, staged learning rates, speaker-disjoint corpus evidence, and
student objectives from these configuration files. Expensive phases checkpoint to Google Drive
and resume after a Colab disconnect.

Before running it, upload the locally generated private metadata bundle
`modeling/artifacts/colab/vaakmitra-colab-private-metadata.zip` to
`MyDrive/VaakMitraGPU/inputs/`. Either upload the verified OpenSLR archive to the same directory or
allow the notebook to resume-download it from the frozen source URL. Accept the gated Hugging Face
model conditions and store the access token only in Colab Secrets as `HF_TOKEN`.

The notebook writes aggregate reference metrics, the private teacher-feature manifest, both
student reports, FP32/INT8 ONNX candidates, artifact hashes, and `vaakmitra-gpu-results.zip` under
`MyDrive/VaakMitraGPU/runs/`. Without an expert-reviewed inventory, every output is labelled
provisional and must be retrained after clinician review.

## 7. Training-first Colab launch for the seven-day deadline

The committed notebook defaults to `TRAINING_PROFILE_NAME="deadline_7day"`. That profile makes
the adult Tamil reference the mandatory result, limits student work to Compact Conformer, and
records Conv-BiGRU as deferred. It uses batch size 1, gradient accumulation 8, deterministic
length buckets, and a checkpoint every 500 optimizer updates. The full encoder stage is optional:
it runs only when the top-block stage improves validation PER by at least 0.005 and its projected
runtime fits the remaining session.

Before opening Colab, upload
`modeling/artifacts/colab/vaakmitra-colab-private-metadata.zip` to
`/content/drive/MyDrive/VaakMitraGPU/inputs/`. Put the pinned OpenSLR archive there too, or leave
download enabled. The notebook requires 13,803,410,250 archive bytes, 17,314,415,289 extracted
bytes, and a 10 GiB working reserve before it stages the corpus. It verifies the pinned archive
size and SHA-256 before extraction.

Accept the AI4Bharat model conditions first. Store `HF_TOKEN` only in Colab Secrets—never in the
notebook, Drive filenames, Git, or terminal output. Push the intended repository commit and set
`VAAKMITRA_REPOSITORY_REF` to that branch or commit. The repository cell clones into
`/content/vaakmitra-source`, resolves a 40-character commit, checks it out detached, rejects a
dirty tree, and writes the resolved commit into the run binding.

Select a Colab GPU runtime and execute from `configuration`. CondaColab intentionally restarts the
runtime once; after that restart, rerun from the configuration cell. Run through `gpu-canary`
before committing the remaining GPU time. The canary runs for at least 1,800 seconds under the
deadline profile, saves a durable checkpoint, reloads it, performs one more update, and writes
`canary-report.json`. Continue only when losses are finite, the checkpoint hash verifies, resume
passes, and the projected mandatory reference work fits the remaining deadline.

If Colab preempts the job, reconnect and rerun from the configuration cell. A compatible run
resumes at the next unapplied optimizer boundary; a binding mismatch fails closed. Inspect Drive
for `run-status.json`, the numbered checkpoint and sidecar hash before continuing. Never delete a
local checkpoint merely because its Drive copy failed.

The valid evidence ceiling is an adult Tamil engineering proxy. It is not child or clinical validation,
does not prove articulation-error thresholds, and must keep `production_ready=false`.
Download `vaakmitra-gpu-results.zip` for aggregate evidence and download the selected native
checkpoint separately; native weights intentionally stay outside the public evidence bundle.

Use the exact checklist in `docs/verification/training-first-colab-preflight.md` before spending
Colab credits.
