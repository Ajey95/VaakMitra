# Live Phoneme Anchor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. User authorizes the local training/fix and private-memory adult testing; preserve current workspace, no commit/merge/push/cleanup.

**Goal:** investigate and improve live phoneme robustness with existing data and the laptop GPU, delivering only verified improvement.
**Architecture:** clean-logit preservation and sparse paired tempo CTC; immutable mmap inputs, two bounded controls and calibration-only selection; native/live verification after freeze.
**Tech Stack:** verified installed Torch2.6.0+cu124/Python/ONNX/Kotlin, no new dependencies.
**Spec:** docs/superpowers/specs/2026-11-12-live-anchor-design.md

## Global Constraints
SSOT3.3.53 DEC067 PHN007; model remains unscorable/false/false; no forced target decoding/private training/new data downloads. Two declared configs,8epochs/12min/patience6 each. Coutput<=250MiB/free>=512MiB; Dfree>=250MiB. Serial GPU training/Gradle; original files and reserved evaluation remain immutable. Preserve avatars/session/round rewards and HEAD712de54 dirty workspace.

## Review Focus
- Calibration/evaluation/private audio never enters gradients or augmentation.
- Teacher is frozen, loss scaling finite, clean source and full speech retained.
- Selection cannot accept denominator changes, regressions or a fallback/no-winner as improved.
- Source/cache/decoder/checkpoint binding precedes gradients; no old-run rebinding.
- Export/mobile/live evidence remains distinct from child phonetic accuracy; no unexpected microphone start/storage.

## Task 1: Train-only clean anchor and bounded CUDA controls
Files: backend/app/vaakmitra_word/live_anchor.py; backend/scripts/model/train_live_anchor.py; backend/tests/vaakmitra_word/test_live_anchor.py; analysis/artifacts manifests.
Interfaces: clean_anchor_loss(student,teacher,temperature=2); eligible_anchor(candidate,baseline,tempo,baseline_tempo); fixed run intent and calibration freeze. Existing safe tempo/sampling/model/decoder helpers reused.
- [x] Write loss/teacher-detach/frame-averaging/nonregression/denominator tests and observe missing-module RED.
- [x] Implement helpers/runner, run scoped tests and actual CUDA forward/backward proof; freeze data/source/config before gradients.
- [x] Run both bounded controls, monitor actualGPU/metrics/checkpoints to terminal freeze, inspect results without accessing held-out inference.

## Task 2: Verify, deploy only qualified improvement, and run phone diagnosis
Consumes Task1 immutable decision. Preserve V7 if unqualified. Use memory-only operator diagnostic with user Record taps; never export speech/token strings. Existing phone app is modelV7 with round-only rewards.
- [x] For eligible selection: export/freeze/parity, held-out evaluation and native gates before deployment; otherwise retain/restate V7 and diagnose remaining boundary with existing fixtures.
- [x] Conduct user-available adult phone comparison within memory-only rules; report numeric prompt agreement separately from phonetic accuracy.
- [x] ONE final source review/one Important RED-GREEN pass, no rereview. Update context/report/ledger and freeze source/evidence/rollback provenance; no completion claim for an unproven fix.

Outcome: bounded protocol completed; no qualified model replacement. Actual paired live results5/15exactpromptmatches on both; model goal remains unresolved. No full evaluation-cohort run or main-model deployment. Details in verification report.

