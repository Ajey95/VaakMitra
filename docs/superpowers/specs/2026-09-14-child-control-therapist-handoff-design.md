# Child control and therapist handoff design

Status: approved product direction from the 2026-09-14 conversation; implementation evidence remains separate.
Normative authority: `VAAKMITRA_FINAL_SSOT.md` v3.3.0, especially DEC-020/021, SES-004/007/008, UX-003/009, PRV-011, and RPT-001..007.

## Scope and trust boundaries

The child session runs without a camera. Parent answers initialize a conservative practice-block and break schedule within the assigned plan's limits. Explicit actions (pause, help, skip, stop), completed whole-word decisions, and audio-quality categories are the only behavioral signals. The system never claims to infer attention, emotion, a specific sound error, or clinical improvement.

The child-facing word practice control is one large red `Break / Stop` button. Its first activation stops microphone capture and aborts in-flight assessment immediately, sends a guarded server pause, and opens two large options: `Take a break` and `End session`. If the server pause fails, listening remains disabled and the child sees an unavailable state. `End session` sends Stop, which must win over any late PASS. A voluntary break may resume the same word after the plan's break interval, while retry-limit/capability pauses remain adult-controlled. No automatic restart or forced continuation occurs.

The local 2D avatar receives only approved state and audio-asset IDs. It never controls scoring or the stop path. Existing Unity code remains a diagnostic/asset experiment and is not shipped as a mobile runtime requirement.

## Session and report data flow

The authoritative session store records bounded word-attempt events and explicit break/stop transitions, including event order, cause, and plan/artifact versions. At session end, a report builder freezes a canonical version from persisted events. It derives counts and denominators independently: total captures, completed scored captures, first-attempt word passes, eventual word passes, retries, unscorable captures by coarse reason, supported attempts, skipped words, and planned/actual breaks. Missing legacy fields are `unavailable`, never zero or fabricated. Cross-session trends are omitted if vocabulary/model/plan versions differ or sample size is too small.

The report view has three visually distinct sections: observed timeline and denominated metrics; deterministic rule explanations and unapproved next-step suggestions; therapist remarks and approved follow-up plan. Neither a suggestion nor a typed reviewer name is clinical approval. The existing inherited reports page must stop rendering mock pronunciation percentages, phoneme accuracy, camera time, peer ranks, or invented trends. An empty/blocked state is preferable to a fake chart.

Child-device report sync is disabled by default. With separate guardian report-sharing consent, the client sends a strict PRV-011 allow-listed pseudonymous report over authenticated transport. Raw audio, transcripts, candidate words, embeddings, exact probabilities/confidence, names, face/gaze data, and child-origin free text are prohibited. Offline delivery is queued and retry-idempotent; it never blocks practice. Only the currently assigned therapist may read or review a report. Reassignment immediately revokes former access.

## Authenticity

Report bytes are canonicalized and hashed with SHA-256. An Android implementation uses a device-bound Android Keystore asymmetric key to sign its snapshot; the backend verifies device binding and does not equate a device signature with model correctness. The therapist's `Sign review` action uses a registered passkey/WebAuthn assertion with user verification and a fresh server challenge bound to the exact report digest, remarks digest, and next-plan digest. The server verifies origin, RP ID, challenge, credential, counter where available, current therapist assignment, and report-sharing consent before appending the review. It stores an immutable verification receipt and publishes no `signed` state on failure. A changed report/remark/plan is a new version with a new signature. The export is independently integrity-checkable, but the signature is not a medical efficacy certificate or automatically a jurisdiction-specific qualified e-signature.

## Failure behavior and verification

Stop and Break are functional when the scorer is unavailable; assessment instead returns UNSCORABLE. A failed pause, database write, revoked assignment, absent consent, missing signing credential, or invalid signature fails closed. The UI shows delivery/verification state rather than a fabricated success. Tests must cover late-PASS cancellation, voluntary-break timing, retry-limit adult gate, no camera permission, no mock metrics, accurate denominators, authorization/reassignment, report tampering, signature replay, offline retry, and an Android-device end-to-end run before mobile release claims.

The web/FastAPI harness can verify behavior and contracts; it cannot by itself prove on-device Android inference, privacy packet capture, thermals/battery, or child-separated clinical validation. Those remain release gates.
