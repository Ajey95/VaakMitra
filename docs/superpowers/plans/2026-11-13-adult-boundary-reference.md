# Adult Reference and Boundary Repair Implementation Plan

> REQUIRED SUB-SKILL: superpowers:executing-plans, inline execution; one fresh final reviewer, no implementer agents.

**Goal:** Repair reference scope and context attribution, then evaluate adult sound evidence with existing data/GPU.
**Architecture:** Versioned partial references, independent free-token alignment, identical-context CTC comparison and bounded learned confidence; unchanged acoustic/raw/app path.
**Tech Stack:** Existing Python/numpy/PyTorch CUDA; no new dependencies.
**Spec:** ../specs/2026-11-13-adult-boundary-reference.md

## Global constraints
DEC077/PHN018,SSOT3.3.71; old400/173/1665audits immutable; no child/TTS/LLM/phone/UI work. Original labels/audio preserved. Cnew80MiB,C>=512MiB,D>=250MiB,Eread-only. Keep branch/oldAPK/model; no cleanup/commit/push.

## Review Focus
- Partial keyword context must not silently become a complete spoken reference or erase an actual error.
- Multiple equally plausible placements and native compounds must not produce a forced sound identity.
- Owner-reviewed existing predictions must not become an independent100percent test or silently change frozen metrics.
- New audit metadata exclusions/speaker exposure/unsupported denominators must remain explicit; no post-audit tuning.
- Classifier scope/body/schema/numeric failures must fail closed without altering raw phones or product UX.

### Task1: Reference contracts and raw alignment
- Create backend/app/vaakmitra_word/reference_boundaries.py and tests/test_reference_boundaries.py.
- [ ] RED tests: keywordscope notCTCwholeclipfit; owneractual separate; extra-context exacttarget neutral; complete scope no trimming; interior omission/substitution; keyword edges abstain; compoundcut/tiedplacements/unknown/nonfinite failclosed.
- [ ] Implement build_reference_record(row,phones,review=None), free_unit_spans(p,tokens,decoded), word_windows(reference,decoded,scope); GREEN.
- [ ] Freeze metadata-only new96audit and confidencefit speaker exclusions, distinct reference manifest and protocol before audio inference.

### Task2: Identical-context evidence and GPU calibration
- Create contextual_sound.py and tests/test_contextual_sound.py; C artifact runner run_boundary_reference.py.
- [ ] RED tests score comparison uses same context, selects most plausible reference placement, ties/unknown/unsupported schema abstain and rawbuffer unchanged.
- [ ] Implement extract_contextual_evidence(p,tokens,reference,decoded,scope,body_id,score_paths=None), feature_names(tokens), apply_contextual_gate(evidence,model); GREEN.
- [ ] Fit on priortrain/development only, preserveclassregistry and thresholds; freeze before new96test inference. No acousticweights changed.
- [ ] Once frozen, one new audit with strictbaseline and separate clean/interior/full/quiet/pause accounting. No audit-driven changes.

### Task3: Review and verified disposition
- [ ] One fresh read-only review exactcurrentfiles/spec/protocol/evidence; one Importantfixpass withRED→GREEN, no re-review.
- [ ] Run relevant backend suites; no Androidbuild when Androidsourceunchanged. Recordsourceproof and artifacthashes.
- [ ] Report actual improvements/failures, scope/phonetictruth limits; update context/ledger. No product activation/phoneaction withoutvalidity/nativegates. Overallgoal mayremainunresolved despite completedexperiment.
