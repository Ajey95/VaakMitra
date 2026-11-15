# Round-only Rewards Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans inline. User chose the concrete three-turn round approach; preserve current dirty branch/workspace, no commit/merge/push/cleanup.

**Goal:** one automatic reward after an earned completed round, with individual actions/results quiet.
**Architecture:** explicit ROUND event, central automatic-event gate, existing earned-round/one-shot lifecycle and demo exposure separated from completion.
**Tech Stack:** existing Kotlin/Compose/Android, no dependencies.
**Spec:** docs/superpowers/specs/2026-11-12-round-rewards-design.md

## Global Constraints
SSOT3.3.52 DEC066 PRS009. Preserve avatars/model/sticker bytes, session paths, configured pacing, opt-outs, voluntary Stop/End, offline voice/name ownership and unscorable gates. Minimum3participating completed turns per eligible round. KeepD250MiBreserve and old deliveries. HEAD712de54/dirty branch retained, no commit/merge/push/cleanup.

## Review Focus
- Automatic old/unknown/saved cues cannot render art, construct voice or later replay.
- Only real completed participating rounds qualify; demo taps and support/user/time breaks do not.
- Letter marks and word picture/mic paths use the same central rule, including short/long configured pacing.
- Stop/recreation/resume/summary cannot duplicate a round; previews remain explicitly manual.
- Default/2x layouts, existing avatars/audio ownership and protected assets remain intact.

## Task 1: Shared round-only celebration
Files: journey/Encouragement.kt; ui/components/EncouragementPanel.kt; ui/screens/{PracticeScreen,LetterLearningScreen}.kt; JVM encouragement/review tests and native AllPagesThemeInstrumentedTest.
Interfaces: add PraiseEvent.ROUND, automaticCelebrationEligible(PraiseEvent):Boolean; earnedPraiseRound retains signature but requires roundSize>=3. No storage schema changes.
- [x] Add policy/short-round tests and native demo/recording-result negative cases; watch JVM missing-interface RED and phone cases fail on bound195ee225 main.
- [x] Implement central gate/ROUND call sites and demo accounting; update obsolete per-action test expectations without weakening progress/Stop/ownership assertions.
- [x] Run JVM/lint/bothABI/test builds, complete native retained/gallery suites, inspect round/quiet/default/2x captures, verify protected/installed hashes and rollback.
- [x] ONE scoped final review; fix Important findings once with RED/GREEN if any. Update context/report/ledger, verify and freeze final source/evidence. Keep workspace.
- [x] Review fix pass: reproduce terminal-letter omission natively on basic round-only candidate and missing versioned-attribution interface in JVM; then version participation saver, preserve earned terminal word/letter rounds and verify migration/rotation/terminal regressions with the complete final suite. No rereview.
