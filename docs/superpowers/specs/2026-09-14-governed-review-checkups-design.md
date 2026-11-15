# Governed human review and 14-day checkups — design

Authority: `VAAKMITRA_FINAL_SSOT.md` v3.2.4, DEC-019, GOV-001..007, CHK-001..004, DATA-002/006/008/012/013, GATE-03/06, PRV-001..009, UX-007.

## Goal and honest boundary

Make consent/ethics receipts, adult-reference review, canary review, clinical-content review, and caregiver checkup requests operational. The software can prepare evidence, enforce identity and hashes, and show pending state. It cannot itself become a guardian, ethics committee, independent rater, or qualified clinician. No approval is pre-populated. No child audio enters the product database or review API.

## Options considered

1. Markdown/CSV packet only: easy to hand over but cannot enforce role, source integrity, or status in the live app.
2. Integrated local metadata workflow plus immutable exports: recommended. An administrator separately verifies qualifications/evidence; therapists submit their own exact-hash decisions; caregiver sees real status and can request checkups. The model/release path still consumes explicit gated artifacts.
3. Auto-approve machine drafts or treat the owner as guardian: rejected because it would misrepresent consent and clinical evidence.

## Review record boundaries

- Credential verification is administrator-authored for a different account, scoped to `reference`, `canary`, or `clinical`, with evidence SHA-256 and an external reference. A self-registered therapist has no automatic signing authority. Revocation is append-only and makes future approvals invalid.
- Caregiver consent submission is a scoped receipt with protocol, purpose, effective timestamp, expiry, and external document hashes. Its state is pending until an independent administrator checks guardian relationship and ethics basis. A past recording is never swept into new consent.
- Adult reference review uses a local-only source manifest and authorized playback; the API/review exporter matches sample ID, word, audio SHA-256, source manifest SHA-256, and actor. One decision per source sample/version is immutable. The reference-bank builder accepts only a global human-approved manifest and cross-checks every approved row against source metadata.
- Canary candidates are prepared offline with no `human_approved` flag. Qualified review binds suite hash, expected categories/decisions, audio hashes, and source non-overlap; a separate technical execution report binds the same suite hash. Neither alone opens release gates.
- Clinical-content review binds a manifest hash covering vocabulary, prompts, voices, avatar states, wording, actions, limits, protocol, and limitations. The therapist is the server-authenticated signer. Changes to a bundle or qualification require another review.
- Every transition creates a pseudonymous audit event; the browser sees status and hashes, not consent documents, child audio, or sensitive notes. Export only metadata required by existing builders and release preflight.

## Checkup and appointment contract

The account `user` represents the existing caregiver/child profile; it can request an appointment for its own child only. The assigned therapist is read from the child account at every read and mutation. Assignment writes an immutable `therapist_assigned_at` timestamp. An older assignment lacking it has unknown schedule, so the UI prompts scheduling without manufacturing a due date. Completed checkups are recorded only by the assigned therapist and only after the scheduled start. Due date is 14 days after the later of current assignment and last valid therapist completion. Pending/confirmed/cancelled/no-show requests do not reset the clock. The caregiver can book or reschedule/cancel; therapist can confirm/complete/no-show. Practice remains available when overdue. Duplicate open checkup requests and active slot clashes are rejected with conditional writes/indexes; no appointment is created automatically.

## Interface and rollout

Backend endpoints return explicit `pending`, `approved`, `rejected`, `due`, `scheduled`, `overdue`, `schedule_unestablished`, or `therapist_unassigned` states. The existing appointments route and page are retained, but fictional therapist names, ratings, dates, and notes are removed in favor of actual API data and honest empty/loading/error states. A therapist review surface shows review packages and exact immutable hashes, not a fake sign-off. No hidden browser local-state booking.

Migration is additive: existing appointments are `ordinary`; their `completed` values do not count as checkups. Existing therapist relationships with no assignment timestamp have unknown due date. All legacy adult approval manifests and canaries remain unapproved until rebuilt. Existing child-session scoring remains guarded/UNSCORABLE when artifacts or child evidence are absent. Physical-device, child-separated, ethics, and clinician release evidence are still external gates.

## Verification

Backend tests cover forged role/approval, revoked credential, changed source/audio hash, duplicate review, consent timing and independence, category/word coverage, due boundary, unknown legacy assignment, unauthorized completion, duplicate booking, and no practice lock. Frontend tests and rendered QA cover real API booking, pending/error/empty states, due reminder, no fictional clinician data, and no claim of clinical readiness. Full backend/frontend suites, build, and local Mongo integration run before handoff. Any unrun physical-device or human review gate is reported as pending.
