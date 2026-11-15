# Pretrained Phoneme Backbone Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use superpowers:executing-plans inline. No implementer agents. One fresh final source review; no rereview. User requests implementation on existing data and explicitly excludes the proposed child recordings.

**Goal:** deliver verified near-correct acoustic phoneme output and internal uncertainty-aware support, preserving the app session UX.

**Architecture:** frozen pretrained acoustic prefix with a supervised two-block tail, explicit phone-unit normalization and strict calibration selection; qualified full-model export/native verification, then separate phonetic support hypotheses.

**Tech Stack:** existing Torch2.6.0+cu124/RTX4060, isolated Transformers4.45.2/Numpy1.26.4 dependencies on E; ONNX/Android Kotlin.

**Spec:** docs/superpowers/specs/2026-11-12-phoneme-backbone-design.md.

## Global Constraints

SSOT3.3.55 DEC068 PHN008..009. No expected word in inference/decoder, no child/private/evaluation training, no public release or clinical score. Immutable old artifacts/splits. New Eworkspace with verified Darchive junctions; Efree>=2GiB,C>=512MiB,D>=250MiB; current precision-stage logical output cap11GiBexcluding weights/deps/tmp; earlier cache7.5/training10/firstprecision10.5GiBcaps remain historical. No simultaneous Gradle/training; no commit/merge/push/cleanup. Seed919,2tail blocks,8epochs/35min/patience6,batch64; layerLR5e-5/head1e-4,clean/tempo.75/.25,AdamW.01. First focus18.50control rejected; second all25.80control declared in spec before gradients, patience on calibration progress with identical eligibility gates. Only qualified frozen model may replace V7; preserve avatars/session/round rewards.

## Review Focus

- Compound tokens/affricates/geminates must not be conflated, guessed from the target or silently dropped.
- True acoustic lengths/masks must survive cache, CTC, quantization and native preprocessing without cropping.
- Calibrations and private/child audio must never enter gradients or data-dependent feature fitting.
- Model/source/cache/RNG/optimizer commits must remain authenticated through failure/resume; no historical rebinding.
- Recognizer mistakes/uncertainty must not become child defects, punitive rewards, diagnoses or false deployment/clinical claims.

### Task1: verified codec, preprocessing and frozen feature cache

Files: backend/app/vaakmitra_word/phoneme_backbone.py; backend/tests/vaakmitra_word/test_phoneme_backbone.py; backend/scripts/model/cache_phoneme_backbone.py.

Interfaces: canonicalize_phones(list[str])->list[str]; normalize_and_pad(list[np.ndarray])->(waveform,mask); feature_lengths(samples)->Tensor; split_backbone(full_model,tail_blocks=2)->(frozen_prefix,trainable_tail); immutable ragged feature metadata/cache manifest.

- [x] Write RED tests for compounds without affricate/geminate loss, exact normalization/rightmask/lengths, invalid clipping, tiny realHF prefix-tail parity and independent trainable state.
- [x] Implement helpers, GREEN scoped tests and actual CUDA parity on public train clips; snapshot source/dependencies/config before cache work.
- [x] Generate immutable prefix features: train original+safe deterministic tempo, full natural calibration and315tempo. Record mechanically impossible train rows, retain all calibration denominators, hash-complete cache before gradients.

### Task2: supervised tail adaptation and qualified deployment

Files: backend/scripts/model/train_phoneme_backbone.py; backend/app/vaakmitra_word/live_anchor_state.py reused atomic commit; new exporter/native codec/preprocessing tests after qualification.

Interfaces: consumes Task1 feature manifest; emits atomic committed tail/optimizer/RNG/scaler histories and calibration-only selection freeze; then full reconstructed model/manifest and exact native input/output contract.

- [x] RED/GREEN train-only mixed sampling, per-example valid CTC lengths and source/selection guards; actual CUDA finite update proof under frozen intent.
- [x] Run the fixed control to terminal calibration freeze, monitor GPU/storage/epochs. No private/reserved cohort inference during selection. Initial control rejected; amended all25 control qualified epoch8, as declared in spec/ledger before gradients.
- [ ] Qualified only: one bound reserved evaluation, FP32/INT8 export/parity, native public tests and measured resources; update main model only after gates. Otherwise continue diagnosis without calling a rejected model fixed. First INT8 rejected90.08%agreement; second hybrid rejected94.91%; third/final INT8 protects first+last2blocks/cap11GiB declared in spec before conversion, same95%agreement/original gates. Earlier10/10.5GiBcaps remain historical.

### Task3: internal phonetic-support policy and full phone check

Files/contracts depend on the actual qualified model observation schema; preserve existing session/avatars.

- [ ] RED/GREEN separation of acoustic evidence/reference alignment, normal gemination/vowel length, repeated/omitted/substituted candidate patterns, and unsupported/low-confidence neutral fallback; no correctness/diagnosis/storage fabrication.
- [ ] Wire bounded existing support actions into current native flow and backend contract; verify golden parity and existing UI/reward boundaries.
- [ ] One fresh final scoped source review/one Important correction pass, native/memory-only adult phone comparison with immutable source/APK binding; package actual model/evidence and update context. Recognition success is separate from tests executing.

