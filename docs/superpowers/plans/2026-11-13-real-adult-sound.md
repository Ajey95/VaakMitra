# Real Adult Sound Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: superpowers:executing-plans. Execute inline; one fresh scoped final review. User explicitly requests continued implementation.

**Goal:** Improve missing/substituted-sound evidence with real adult data and GPU fitting, preserving independent recognition and neutral feedback.
**Architecture:** Unique decoded differences plus local CTC acoustic features and a learned logistic confidence assessor. Separate original training, development and held-out adult speakers; no expected-word decoding.
**Tech Stack:** Existing numpy/PyTorch CUDA, Kotlin/Compose if qualified.
**Spec:** ../specs/2026-11-13-real-adult-sound-design.md

## Global Constraints
SSOT3.3.65 DEC073/PHN014. No child/TTS audio,1665cohort,held-out tuning, LLM recordings/features, scoring/clinical claims, avatar/session change, E outputs, cleanup or commit/push. Preserve old APK/model and owner-deferred phone checks.

## Review Focus
- Wrong free recognition must not automatically become a sound correction.
- Native compound/geminate semantics and unknown/blank/tied evidence must match across Python/Kotlin.
- Both kind and sound identities matter; lexical labels are provisional, not verified speech-error truth.
- Zero denominator, missing artifacts, unseen schema or nonfinite coefficients fail closed.
- Only the selected frozen model may affect neutral coaching; silence/uncertainty/accepted variants never become wrong scoring.

### Task1: Bounded assessor and metadata split
- [ ] RED tests for unique proposals, geminates, compounds, accepted variants, unknown/ties, empty/nonfinite inputs and frozen learned schema.
- [ ] Implement backend/app/vaakmitra_word/real_adult_sound.py; GREEN.
- [ ] Select/hash metadata identities without inference, enforcing audio/speaker separation and exclusions; create immutable protocol.

### Task2: Real adult GPU fit and evaluation
- [ ] Infer fit/development only; fit standardizer/logistic layer on fit only and select fixed-grid threshold on development only.
- [ ] Freeze model/threshold before held-out inference; measure clean primary and timing/quiet secondary separately against strict baseline.
- [ ] Publish all denominators/errors/abstentions and apply all class-specific gates without post-result tuning.

### Task3: Qualified mobile integration or explicit inactive result
- [ ] If qualified port tiny scorer/asset, test native numeric parity, trusted-evidence-only voice focus and buffer erasure while keeping UI unchanged.
- [ ] One scoped final review, one material fix pass, applicable backend/native verification and build if changed.
- [ ] Deliver exact evidence/APK if built, update context/ledger/report and list unresolved real-mic/child validity gates. No automatic install/device actions.

### Task4: Acoustic-output adaptation after failed confidence gates
Spec: ../specs/2026-11-13-acoustic-output-adapter.md; SSOT3.3.67 DEC074/PHN015 overrides literal no-evaluation-rows only for the distinct never-used MSWC test source, never the1665cohort.
- [ ] RED→GREEN compact adapter numeric/identity/unknown/bounds tests in test_acoustic_logit_adapter.py.
- [ ] Freeze existing MSWC source metadata/archives and parent/speaker/hash exclusions;600train+all132dev+173test encodable metadata,300oldtrain retention and160olddev retention.
- [ ] Infer fit/development only; GPU CTC-fit diagonal and posterior-mixing adapters12epochs snapshots4/8/12, fixed regularization/selection. Select or identity; freeze.
- [ ] Fit new confidence assessor from adapted real train evidence and development-only threshold; freeze before fresh MSWC test inference.
- [ ] One fresh source test; report raw accuracy and independent correction gates separately; no test tuning. Native preview only if raw and parity gates pass, sound cues only if correction gate passes.
- [ ] Include this phase in final one scoped review and source-stable verification/report/context.

### Task5: Final-layer acoustic adapters and shared graph
Spec: ../specs/2026-11-13-final-layer-adapters.md; SSOT3.3.68 DEC075/PHN016.
- [x]6RED→GREEN tests for low-rank identity/merge/trainable scope and shared ONNX offset/digest/path/shape/runtime behavior.
- [ ] Freeze source identities/new parent-disjoint utterance audit and novel-speaker stratum; preserve173exposed test quarantine.
- [ ] Cache FP32 prefix features and fit rank8 final2layer query/value+head12epochs onGPU; select only development/retention, then freeze confidence.
- [ ] One untouched utterance audit; publish separate raw/sound gates, all strata/errors/abstentions without tuning.
- [ ] If qualified, match/merge exact tensors into bounded shared-weight graph and prove desktop/native parity before changing app.
- [ ] Final one scoped review/material-fix pass, applicable verification/delivery/context. If no correction gate passes, leave corrections inactive and state unresolved acoustic-truth limitation.

### Task6: Final competing-hypothesis sound assessor
Spec ../specs/2026-11-13-contrastive-sound.md, SSOT3.3.69 DEC076/PHN017.
- [x]7testsRED→GREEN contrastive hypotheses/unknown/ties/acceptedvariants/body-boundnetwork/unsupported contrast.
- [ ] Fit two fixed-body16hiddenconfidence models on900train; choose body/cutoff from132dev only, freeze before reading400auditoutcomes.
- [ ] One declared400audit evaluation with fixed strict baseline and full sound/raw/strata gates; no further tuning after outcomes.
- [ ] Qualified-only native/voice integration or explicit inactive result; final one scoped review/fix pass and verified report/delivery.

## Execution disposition (13 November)

All declared fitting/selection/audits completed, with failed/rejected results preserved and no historical1665 repeat or post-audit tuning. Raw LoRA improved400utterance PER30.42→26.25%; final sound assessor failed development/coverage (129/734correct,1ownalert). Therefore no correction/voice integration is qualified; all correction assessors inactive. Debug-only raw shared graph is packaged under SSOT3.3.70 delivery ruling, android_verified=false; normal baseline retained. Device checks remain owner-deferred.18clip local actual-sound review pending owner completion, not independent test.

One scoped final review/one fix pass completed: consonant-geminate guard, native nonempty pinned fixture contract, nonblank phonetic review provenance; factual log-probability unit corrected. Pre-fix extractor snapshots bind the published GPU metrics; fixed helpers are not re-evaluated on the exposed audit.72backend and4inline-JS cases passed; final270JVM/APKs/lint build passed6m44s,0fail/error/skip,lint0errors(8warnings/10info). Ledger and ROOT/ADULT_SOUND_UPDATE_REPORT.md are the detailed evidence/handoff. Task goal of dependable sound-error correction remains unresolved; do not equate completed experiments with goal completion. Keep branch/workspace, no commit/push/cleanup.
