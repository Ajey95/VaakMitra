# Veshti Reward Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. User has authorized implementation of the preceding proposed reward design. Keep existing dirty branch/workspace; no commit/merge/push/cleanup.

**Goal:** automatic original Tamil reward sticker and existing child-name praise after practice, preserving avatar/session UX.
**Architecture:** replace the illustration slot inside EncouragementPanel with one bundled PNG; reuse existing ticket, speaker, caption and short settling scale animation.
**Tech Stack:** existing Kotlin/Compose/Android, no new dependency.
**Spec:** docs/superpowers/specs/2026-11-12-veshti-reward-design.md

## Global Constraints
SSOT3.3.51 DEC-065 PRS-008; four original avatars and session routes unchanged. Names stay local; model assets/scoring unchanged. Existing audio/motion/letter opt-outs and Stop remain. Preserve250MiB D reserve and all old deliveries. No commit/merge/push/cleanup.

## Review Focus
- Picture completion and recorded/letter practice use the existing same panel, with no new scoring/entitlement.
- Compact/2x layouts keep caption and Stop accessible.
- Motion-off/Still/system-off do not schedule decoration.
- No new speech trigger, restored-event replay or voice/mic overlap.
- Bundled PNG alpha/provenance; original avatar/model bytes unchanged.

## Task 1: Existing completion-card reward art
Files: EncouragementPanel.kt, drawable-nodpi/vm_reward_veshti_man.png, AllPagesThemeInstrumentedTest.kt, SSOT/context/report/provenance.
Interfaces: consumes existing automatic completion tickets, PraiseSettings and AvatarMotionEnvironment; no new public API.
- [x] Add native dec065 completion-sticker/normal+2x controls test; assemble test and observe RED against bound previous8c1adccd main APK (missing sticker).
- [x] Bundle generated art and replace only current artwork slot. Retain existing short scale entrance; gate it on system animations too. Keep caption/button/session behavior.
- [x] Run177JVM/lint/bothABIs/test build, native retained19+gallery49, asset/installed hashes and rollback checks.
- [x] Finish public screenshot inspection/current phone voice probe after reconnection; emulator fallback timed out.
- [x] ONE scoped final review, ledger rulings/minors; fix Important findings once if any. Update report/context, freeze source/evidence/manifest and keep workspace.
