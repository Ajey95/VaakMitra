# Core sound practice and responsive microphone

Owner requested the proposed flow, then clarified sound-based adaptive practice is CORE, not an optional feature. SSOT3.3.60 DEC069/PHN010/MIC001 governs. Implementation uses the existing isolated lab worktree and preserves prior dirty UI/model work; no commit/push/cleanup.

## Learning flow

Enable inline Tamil sound → syllable → existing word practice by default in current word sessions and their existing result surface. No opt-in switch, new avatar, route, mandatory assessment or automatic popup. The child can Skip, use normal Next, pause or stop. Hoist transient step/Skip/help state by current word so recording/result/retry cannot override an explicit choice. Listening is local and user-triggered; example help can be hidden/restored explicitly. Fragment steps never start the microphone, grant completion/rewards or claim mastery. Closed authored examples use the installed offline Tamil system voice, explicitly unverified as pronunciation references. Existing247-letter sessions and manual unlocking stay intact.

## Adaptation and evidence

After target-free inference, a separate educational policy consumes valid supported tokens and authenticated provisional practice references. Whole-word c/s variants are explicit, never global normalization. A bounded minimum-edit alignment merges optimal target interpretations; ambiguous targets, unsupported insertions, invalid/unknown evidence and differences beyond2 edits/half the reference abstain. Gemination, affricates and vowel length remain exact.

Within24 actual attempts in session memory,3 observations across2 distinct words can prioritize a curated sound. These thresholds are conservative interaction rules, not calibrated confidence or proof of a child's difficulty. Agreement clears that word's tentative labels while preserving attempt-window slots; it never awards mastery. Invalid/agreeing attempts also age history. Nothing is persisted/uploaded or added to child reports. Session exit/account change clears it. Existing clinical support remains generic, official results UNSCORABLE and all child/clinical scoring gates false.

Core Next may prioritize a known same-sound word from the forward current approved/focused itinerary, with difficulty no higher than the current word; otherwise retain existing picture-based curricular selection. Never wrap/retry forcibly or invent new words. A named related-word choice is also available after the warm-up.

## Microphone

Current main-thread recorder.start() can block on native AudioRecord startup; synchronous lifecycle recorder.cancel() can wait through stop/release/join. Use a dedicated single capture worker, separate from model inference/release. Invalidate generations immediately on cancellation, clean stale successful starts before publication, erase unpublished PCM and release cancelled stop ownership so the next attempt is available. PREPARING appears immediately; LISTENING only follows actual successful start. Loading-model capture remains disabled with visible readiness text. No changes to acoustic weights, decoder, VAD, capture window, sampling or8second memory cap.

## Choices and validation

Chosen: deterministic local core learning with neutral experimental suggestions. Automatic child-error scoring remains unvalidated; an LLM adds no acoustic evidence and violates the internal closed-prompt goal. No training or exactly-once1665evaluation repeat.

Use literal red/green JVM tests for sound alignment/variants/bounds/aging/curriculum and deliberately stalled native microphone boundaries. Run full Android JVM/build/lint; rendered phone core stages, skip/retry/help, large text, public native parity/privacy, and existing avatar/round reward/letter regression checks. No unattended real mic; owner-tapped responsiveness is a separate check. Final install-r must preserve and SHA-verify the private1.26GB model plus installed APK, retain old deliverables, and record exact evidence/limitations.
