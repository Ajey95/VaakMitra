# Training-First One-Week Delivery Design

**Date:** 2026-09-08

**Status:** Approved direction; pending written-spec review

**Primary owner:** Backend Member 2

**Deadline:** Seven calendar days

**Release ceiling without therapist-labelled child speech:** engineering research prototype

## 1. Decision

Model training is the critical path and starts before the three-member backend integration. The
first objective is a reproducible Tamil phoneme CTC reference model derived from the pinned
AI4Bharat Tamil IndicConformer encoder and OpenSLR 127 sentence recordings. The second objective is
to export and integrate the best evidence-backed reference checkpoint. A compact student is trained
only if the reference run, export, and remaining time pass explicit gates.

The existing notebook will not be launched unchanged for a multi-day run. It currently performs up
to three reference stages, corpus-wide teacher feature extraction, and two five-epoch student runs,
while reference and student training resume only at epoch boundaries. The deadline profile must make
reference training independently completable and recoverable within a Colab session.

OpenSLR supplies adult Tamil sentence audio and transcripts, not isolated phoneme recordings. The
transcripts are normalized and converted through the versioned Tamil pronunciation lexicon into
phoneme sequences. CTC learns the frame-to-phoneme alignment without hand-labelled phone boundaries.
This trains adult Tamil phoneme recognition; it does not establish child-domain or clinical validity.

## 2. One-week success definition

The week succeeds when all of the following exist:

1. A preflight-tested, deadline-safe Colab notebook with deterministic, within-epoch resume.
2. A completed CPU/small-GPU smoke run that exercises data preparation, training, evaluation,
   checkpoint reload, and export.
3. At least one completed real reference stage on the frozen speaker-disjoint OpenSLR manifests.
4. A selected checkpoint with hashes, configuration, vocabulary binding, validation/test phone error
   rate, and a stage-comparison report.
5. A loadable reference-model artifact or an explicit, reproducible export/operator failure report.
6. The existing Member 2 runtime can consume the selected model contract, with deterministic test
   fixtures retained for backend testing when the large model is unavailable.

Success does not require a particular phone error rate. A poor but correctly measured model is a
failed experiment, not a missing result. It must not be relabelled as clinically useful.

## 3. Priority order

Work proceeds in this order:

1. Freeze and validate corpus, split, vocabulary, lexicon, and upstream model bindings.
2. Make reference training interruption-safe.
3. Run a 30-60 minute throughput and memory canary on the assigned GPU.
4. Complete head-only training and immediately evaluate/export the best checkpoint.
5. Run top-encoder-block fine-tuning only if the head-only result is technically sound.
6. Run full-encoder fine-tuning only if the top-block stage improves validation PER by at least
   `0.005` and the remaining wall-clock budget is sufficient.
7. Train one compact student only after the reference deliverables are frozen.
8. Integrate Members 1 and 3 around the frozen model interface while longer GPU work runs.

Reference-model completion outranks distillation, INT8 optimization, broad ablations, and cosmetic
notebook reporting.

## 4. Training architecture

```text
OpenSLR 127 Tamil WAV + transcript
                |
                v
speaker-disjoint frozen manifests + normalized transcript
                |
                v
versioned Tamil lexicon -> expected phoneme token IDs
                |
                v
pinned AI4Bharat IndicConformer encoder + new phoneme CTC head
                |
                v
head-only -> top-block -> optional full-encoder stages
                |
                v
best checkpoint + phoneme vocabulary + preprocessing contract
                |
                v
PER/robustness evidence + model export -> VaakMitra acoustic runtime
```

The AI4Bharat text decoder is not used as a phoneme decoder. The new head predicts the project's
phoneme vocabulary, including an explicit CTC blank. The model output is frame-level phoneme log
probabilities for Member 1 forced alignment and Member 2 GOP/confidence scoring.

## 5. Notebook execution profiles

The notebook exposes three explicit profiles:

- `smoke`: a small bounded subset and one short stage; validates the entire pipeline cheaply.
- `deadline_7day`: trains the reference model first, enables time-budget controls, selects one
  student at most, and stops optional work when gates fail.
- `research_full`: preserves the exhaustive reference and two-student experiment for later work.

`deadline_7day` is the default for this delivery. Every output path includes a run ID derived from
the immutable data/model/config bindings so an incompatible prior checkpoint cannot be resumed.

## 6. Corpus and local-storage behavior

The source archive and durable metadata remain in Google Drive. At session start, required data is
copied or extracted to `/content` after free-space and integrity checks. Training reads sequentially
from local runtime storage rather than individual Drive-mounted audio files.

Google Drive stores only durable inputs, manifests, checkpoints, metrics, compact logs, and final
artifacts. Teacher feature shards are not generated until a student run is authorized. If generated,
they are built resumably and copied durably in coarse, hash-verified shards.

Speaker-disjoint train, validation, and test manifests remain frozen. Transcript normalization,
lexicon version, phoneme inventory ordering, blank index, upstream model revision, and manifest
digests are recorded in a run binding. A mismatch stops resume rather than silently mixing runs.

## 7. Interruption-safe training

Reference and student training checkpoints contain:

- model and optimizer state;
- automatic mixed-precision scaler state;
- stage, epoch, sampler epoch, next batch/update position, and global optimizer update;
- Python, NumPy, and Torch CPU/CUDA random-number states;
- best metric and early-stopping state;
- immutable run binding and checkpoint-format version.

Training saves atomically to local storage and then copies a verified checkpoint to Drive every 500
optimizer updates, at each epoch boundary, on validation improvement, and before a time-budget stop.
Only a fully written file replaces `last.pt`. Resume restores the sampler order and continues at the
next optimizer update without replaying an already applied update.

The loop accepts a maximum session wall time. It reserves enough time to finish the current optimizer
update, persist a checkpoint, write a run-status record, and exit cleanly. Non-finite loss or gradient
values stop the run and preserve a diagnostic checkpoint that excludes audio and transcripts.

## 8. Canary and stage gates

The first real GPU action is a 30-60 minute canary using the same model, data loader, precision,
gradient accumulation, validation sample policy, and checkpoint path as the deadline run. It records:

- assigned GPU, VRAM, CUDA/PyTorch versions, and mixed-precision mode;
- examples, audio seconds, frames, batches, and optimizer updates per minute;
- peak allocated/reserved GPU memory and host memory;
- local staging and checkpoint-copy throughput;
- projected duration for each mandatory and optional stage.

The canary must successfully save, reload, and resume from a mid-epoch checkpoint. If it cannot, the
multi-hour run does not start.

Stage promotion rules are:

- Head-only is mandatory and always produces an evaluated/export-attempted candidate.
- Top-block training starts when head-only has finite losses, a reloadable checkpoint, complete
  validation metrics, and a projected finish inside the deadline.
- Full-encoder training starts only when top-block validation PER improves by at least `0.005`, its
  checkpoint is better than head-only under the selection policy, and the projected run plus export
  fits the remaining budget.
- Student work starts only after the selected reference checkpoint, test report, and export attempt
  are frozen. Exactly one student architecture is selected for the deadline profile.

## 9. Evaluation and selection

Validation PER selects checkpoints within a stage and controls stage promotion. The frozen test set
is evaluated only for the final selected reference checkpoint and, if completed, the selected
student. Reports include phone error rate, insertion/deletion/substitution counts, loss, unscorable
records, duration buckets, and declared robustness slices.

The selection report compares head-only, top-block, and full-encoder candidates that actually ran.
It binds each metric to checkpoint, vocabulary, manifest, configuration, and environment hashes.
The existing `0.005` validation-PER improvement is a compute-promotion gate, not a clinical threshold.

An expert-reviewed phoneme contract remains preferred. If the approved contract is unavailable, a
provisional run may proceed only with the existing explicit research flag. Its checkpoints and
reports are labelled `provisional_research_only` and must be retrained after contract changes.

## 10. Export and backend handoff

Immediately after head-only and after final reference selection, the notebook attempts to produce a
portable artifact with:

- model weights or ONNX graph;
- ordered phoneme vocabulary and blank index;
- audio sample rate and normalization contract;
- frame/subsampling metadata;
- model/config/data hashes;
- a fixed parity fixture and expected output shape/statistics.

Export failure does not erase the trained checkpoint. It produces the failing operator list and a
native-PyTorch loading path so backend integration can continue. INT8 quantization and student export
are optional until the reference artifact and evidence are secure.

## 11. Error handling

- Missing gated model access stops before corpus preparation and never prints credentials.
- Missing or unsuitable CUDA runs only the smoke path and reports the exact blocker.
- Insufficient `/content` storage stops before extraction and reports required versus available
  bytes.
- Data, vocabulary, model, or checkpoint binding mismatch blocks resume.
- Unknown phonemes are counted and excluded under a recorded reason; excessive unknown coverage
  blocks the real run.
- Corrupt audio is quarantined in metadata without copying voice data into logs.
- Colab preemption is recovered from the latest verified Drive checkpoint.
- Drive write failure retains the local checkpoint and stops before further destructive progress.
- Out-of-memory triggers one controlled reduction in dynamic batch/frame budget, records the change,
  and restarts from the last verified checkpoint; repeated failure stops the stage.

## 12. Testing strategy

Notebook support code is moved into importable modules where practical and developed test-first.
Automated tests cover:

- deterministic run bindings and rejection of incompatible resumes;
- length-bucketed batching and speaker-disjoint manifests;
- exact mid-epoch resume without skipped or duplicated optimizer updates;
- RNG, optimizer, scaler, and best-metric restoration;
- atomic checkpoint promotion and corrupted-checkpoint fallback;
- time-budget graceful stopping;
- transcript-to-phoneme target generation and unknown-token reporting;
- CTC dimensions, blank handling, repeated phones, and finite loss;
- stage freeze/unfreeze policies and promotion gates;
- report/checkpoint hash consistency;
- export loading and fixed-fixture parity where supported.

The existing backend suite remains green. A notebook syntax/import check and smoke run are required
before any paid or limited GPU session is used.

## 13. Seven-day schedule

- **Day 1:** implement and test deadline profile, mid-epoch resume, local staging, run binding, and
  canary reporting; complete CPU smoke.
- **Day 2:** run GPU canary, fix measured bottlenecks, then start head-only training.
- **Day 3:** finish/evaluate head-only, freeze its checkpoint and export attempt; start top-block stage
  if gates pass.
- **Day 4:** finish/evaluate top-block; select/export the best reference; start optional full stage
  only if its gate passes.
- **Day 5:** finalize reference test evidence and integrate the artifact contract; start one student
  only if reference deliverables are complete.
- **Day 6:** finish optional student/export/quantization work or use the day for reference error
  analysis and backend integration.
- **Day 7:** rerun reproducibility checks, package artifacts and hashes, complete end-to-end tests,
  and document passed, failed, and deferred gates.

GPU execution and local integration may overlap, but no second training experiment displaces a
mandatory reference deliverable.

## 14. What breaks first

The highest-probability failure is an interrupted or slower-than-projected Colab session, followed
by Drive I/O, provisional lexicon errors, and reference-model export incompatibility. The canary,
local staging, within-epoch resume, early export, and native-checkpoint fallback directly address
those risks.

The largest product limitation is different: OpenSLR adult speech cannot calibrate clinically
correct child articulation decisions. Training completion therefore cannot remove the need for
ordinary child-Tamil evaluation and therapist-labelled calibration.

## 15. Explicit non-goals for this week

- Autism detection or diagnosis.
- Claiming child-speech accuracy from adult OpenSLR evaluation.
- Claiming therapist-valid PASS/COACH thresholds without therapist labels.
- Training both student architectures before the reference model is secured.
- Exhaustive VTLN or augmentation ablations before the deadline artifacts are complete.
- Guaranteeing a Colab GPU type or uninterrupted runtime.
- Treating an unexecuted notebook, a smoke checkpoint, or synthetic fixtures as a trained model.
