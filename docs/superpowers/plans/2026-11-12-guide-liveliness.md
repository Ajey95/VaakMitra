# Guide Liveliness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan inline. Existing authorized branch/workspace retained; no commits/merge/push/cleanup.

**Goal:** the existing guide visibly breathes, blinks and greets with distinct movement modes.
**Architecture:** pure bounded motion/curve policy, lifecycle-owned native Compose animation, existing vector artwork and explicit Hello preview key.
**Tech Stack:** current Kotlin/Compose/Android API26+, no dependencies.
**Spec:** docs/superpowers/specs/2026-11-12-guide-liveliness-design.md

## Global Constraints
SSOT3.3.50 DEC-026 AVT-004..006; all4original avatars/25words/18focus/247letters/manualunlock and unscorable model preserved. No cloud, child/private audio or profile mutation in fixture tests. Still, quiet phases, background and system-off suppress decoration. D250MiB packaging reserve, byte-exact rollback delta/base dependency retained. Keep dirty codex/backend-verification-lab HEAD712de54.

## Review Focus
- Background/phase changes during a greeting must cancel and never replay on resume.
- Still/system-off must leave no blink/gesture/idle frame loop, including mode switches.
- Identity or explicit Hello preview changes must give one bounded greeting, with reduced distance/speed respected.
- Closed eyelids must not leave oversized pupils or alter the character identity.
- Native measurement must isolate the live canvas and settled radio state, never thumbnails/private overlays.

## Task1: Existing guide liveliness
Files: modify avatar/AvatarMotionPolicy.kt, ui/components/ExpressiveAvatar.kt, ui/screens/AvatarPickerScreen.kt; tests avatar/AvatarMotionPolicyTest.kt and AllPagesThemeInstrumentedTest.kt under existing app source roots. Interfaces: add blinkPeriodMs/greetingDurationMs to AvatarMotionSpec; pure avatarBlinkAmount(Float)/avatarGreetingAmount(Float); optional greetingKey:Int=0 on ExpressiveAvatar.
- [x] Write bounded blink/greeting and quiet-state contracts; observe missing-interface RED.
- [x] Add two real public native blink/greeting tests; observe RED on bound motion-only916ab557 APK.
- [x] Implement curves/idle frame states/one-shot greeting/Hello replay using original rig; preserve existing motion cancellation and selection.
- [x] Verify JVM/lint/bothAPKs and complete physical retained/gallery checks, inspect public captures and protected hashes/rollback.
- [x] ONE fresh scoped final review; one Important RED/GREEN correction pass if needed, no rereview. Record rulings/minors, update context/report and freeze separate source/evidence handoff. Keep branch/workspace as-is.
