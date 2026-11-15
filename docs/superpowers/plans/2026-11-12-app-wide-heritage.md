# App-wide Tamil heritage implementation plan

> Execute inline with superpowers:executing-plans; one fresh final reviewer, no per-task agents. Existing dirty isolated lab stays; no commits/merge/push/cleanup.

Goal: finish every Android page and startup branding in one coherent native paper-and-ink theme.
Architecture: original vector brand + shared paper components; visual migration of legacy screens; sanitized debug gallery. Preserve session/model/account behavior. Tech: existing Kotlin/Compose/SDK only. Spec: docs/superpowers/specs/2026-11-12-app-wide-heritage-design.md.

## Constraints
DEC057/SSOT3.3.40, prior DEC053..056 UX002/003/010 PRV001/005 AVT001..006. Model/decoder/VAD/avatar art/preferences/word+letter semantics frozen. No synthetic/private capture. The only capture change is legacy candle peak-only privacy fix. Keep default production behavior for preview-injectable state, never mutate account for screenshots. Public debug gallery nonexported and excluded from release. All page controls scroll at2xtext; redStop remains reachable. Keep existing branches/protected roots.

## Task1 shared branding and components
- [x] Write native missing-gallery/branding contracts and peak-only fake-source tests; observe RED before implementation.
- [x] Add original vector slate/kolam speech mark; adaptive icon/platform splash/appwelcome shared branding. Paper actions/cards/fields, static outlines, high contrast and min56dp touch targets that grow with text.

## Task2 all pages
- [x] Migrate every legacy page to HeritagePage, dark readable copy, paper panels/headers/brand. Quiet splash/onboarding/reward decoration; same routes/callbacks/counters. Touch avatar chooser chrome only.
- [x] Replace candle file capture with peak-only PCM + lifecycle/permission guard, unit cleanup checks. Sanitize debug gallery previews with safe default production behavior; snapshot all17pages and2x forms.

## Task3 validation and one review
- [x] Full JVM/lint/bothABI/test build, old17native plus all-page gallery/startup/2x tests; inspect every page screenshot.
- [x] One fresh whole-scope review. Regrade and ONE Important TDD fix pass, defer minors, no rereview.
- [x] Install/readback hashes on physical phone and emulator as available, unchanged V7/modelflags, archive/report/context. Preserve current branch/workspace.

## Review focus
All routes actually themed including startup/launcher; no stale white-on-paper/hidden buttons; real/empty counters only; no regression of auth/guide/session navigation or child-scoped preferences; no private fields/audio in screenshots; gallery preview cannot be triggered externally or shipped in release; candle nofiles and immediate stop/background/permission cancellation; vector safe zone and largefont fit; frozen model/avatar sources.

Final device limit: current phone APK/model checks are verified; the corrected window-bound UI retest awaits another phone unlock. Emulator acceptance is complete.
