# Autonomous attention-window practice cycles

Owner's latest corrections: core flow must be an autonomous feedback loop, repeated for a child's comfortable focus window; one child may be ready for a different challenge after3whole cycles while another needs a gentler set after5. Those are examples, not a single fixed loop. SSOT3.3.61 DEC070/PHN011 governs. Continue existing implementation autonomously; no new approval gate.

## Baseline already verified

Base core sound/microphone update:220JVMtests,18phonechecks252.78s, build/lint success, screenshots normal/2x text inspected. Installed base APK SHA5b382b5cd4bb39198a741e29e2b044f9240d19ac0401791c2d9404b81c285d6f (60,467,740B), modelff41636b...5020cf (1,262,607,977B) both actual phone SHA readbacks match. W/core-sound-delivery preserves rollback APK/proofs/screenshots; manifest explicitly says autonomous_cycle_update_pending=true. No scoring/weights/decoder changes or1665benchmark repeat.

## Flow

Use existing CarePlan focusMinutes (2..8) as caregiver-estimated comfortable active focus window and sessionMinutes (5..20) as total cap. Core local controller chooses an approved3-word set and a sound cue from public reference metadata. Automatically show/play sound→syllable→word cues, pause to allow imitation, then show Your turn using existing Record/Stop. Microphone never starts automatically; fragment steps are unrecorded/unscored. After a recording, neutral feedback and the next teaching/word step are chosen automatically; no child Next-part/difficulty selection. Child Skip/Help/pause/Stop always win. Stop stale cues/results on account/target/background changes.

One full cycle visits its3words, collecting only bounded transient abstract practice signals. Repeat or change the complete set based on trends, not one utterance. Tentative repeated sound patterns choose similar/simpler sound work and more help. Independently observed picture/help responses and task completion can permit one-tier curricular complexity increase; token agreement alone never declares correctness/mastery. Unclear capture yields generic help, not child failure. Derive support/repetition budgets from focus window and recent cycles; do not require all children to repeat3or5times. A bounded stagnant-set budget changes to a different similar/easier approved set rather than retrying forever. Existing saved picture-task progress may seed complexity; phoneme-derived state remains session memory only.

Reuse current3-turn reward overlay per cycle. Automatic ROUND continuation waits for bounded cheer/settling, rechecks foreground/identity/user stop, and resets only round credit. It MUST preserve blockActiveMs and totalActiveMs. FOCUS, USER, SUPPORT, BACKGROUND and END never auto-resume. At the focus deadline offer an actual break; at total deadline end. These are configured pacing limits, not measured attention/therapy outcomes.

Use installed offline Tamil voice, gated by existing automaticSpeech preference, readiness, current speech ownership and no active capture. Silent/unsupported voice falls back to the same visual cadence. Cues are bounded and never restart after background without explicit continuation. Preserve avatars/interests, letters/manual unlocking, existing microphone fix, no wrong scores or new rewards from passive demos.

## Approach and verification

Deterministic local state machine; no LLM or clinical classifier. Separate pure set/cycle/difficulty/budget policy from cancellable Compose cue scheduling. Red/green tests for repeated cycles/child-specific focus budgets, conservative promotion, same/easier fallback, finite sets, manual-stop precedence, clock preservation, stale audio cancellation and no capture from cue progression. Render autonomous stage/feedback flow on phone with public fixtures and no real mic, recheck reward/letter/privacy/native pipeline. New final artifact must replace active delivery only after actual verification; preserve base rollback/proofs and report manual hardware voice timing separately.
