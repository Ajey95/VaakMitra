# Conversational guide and fortnightly therapist delivery

15 November 2026. **Design for owner review; product implementation has not started.**

Owner request: implement natural, Jarvis-like conversation and automatic biweekly therapist-report delivery, allowing backend tools for speech assistance. Preserve existing avatars, Tamil culture, session sequence, voluntary breaks, manual microphone, neutral speech feedback and the retained acoustic model. Recording work is owner-managed and must not resume.

## Approach and boundaries

Recommended engineering choice: backend-assisted conversation, with the existing practice experience still usable without a backend. The owner has been asked whether conversation itself must instead run entirely on the phone; this document does not claim that choice is approved.

1. **Owned backend, local inference — recommended.** Use the already downloaded Gemma4E2B text model through pinned llama.cpp, conventional local Tamil speech recognition and the phone's installed Tamil TTS. Raw audio is never given to a chat/audio LLM or an external provider. No new LLM API subscription is required. The backend must be reachable for conversation. A laptop demonstration does not establish a permanently available service.
2. **Fully on-phone conversation.** Requires choosing, packaging and qualifying an on-device ASR/text-model runtime against actual storage, memory, Tamil performance and latency. The phone recently had approximately2GB free after the current app installation. This is a separate deployment effort; do not advertise backend-assisted conversation as fully offline on the phone.
3. An external text-LLM provider could later reduce backend compute, but is excluded from the initial design because it changes transcript privacy/cost and is not needed to reuse existing local weights.

Decisions below are proposed implementation defaults, not prior owner approvals. After approval, amend the SSOT before product code (proposed DEC081, CONV001 and RPT008 extension). No scoring/clinical qualification or acoustic retraining is included.

## Current implementation gaps

- Android has Retrofit authentication/lesson/summary calls, but no conversational service or persistent report upload queue. Local profile markers are deliberately not backend credentials.
- `LocalTamilSpeaker` selects installed offline Tamil voices and currently speaks a closed catalogue. Existing avatar/audio lifecycle guards and Record/Stop are reusable.
- Backend has authenticated aggregate interactive sessions, canonical word reports, assigned therapist relationships and independently verified report-share grants. Existing reporting/checkup clocks do not send fortnightly email.
- `StoryVoiceService` optionally calls ElevenLabs for fixed authored lines. It is not a conversational model. Its provider being present in source does not establish configured credentials.
- The retained phoneme model has phone execution evidence; reliable omitted/substituted-sound assessment remains unqualified. Conversation cannot turn its estimates into correctness scores.

## Conversational experience

The same avatar can greet the learner, discuss their interests, answer short questions, respond to requests for help, repeat an example and suggest a break. Replies are short Tamil or simple Tamil/English appropriate to caregiver preferences. They are generated from the conversation, rather than selected exclusively from authored sentences.

Conversation is integrated into the existing session host. Keep the existing practice Record/Stop, result, picture, completion and break controls. Insert a short conversational check-in at a block boundary and use the existing help surface for a follow-up conversation. Do not introduce a compulsory child configuration screen, replace the avatars or change three-turn celebration rules.

**Capture purpose is explicit in session state.** A conversational question sets the next capture to CONVERSATION; a word/letter example sets it to PRACTICE. The child does not have to choose a technical mode. Conversation turns cannot mark a letter practised, count toward practice-round rewards, update sound difficulty or become a failed pronunciation attempt. Practice captures retain their existing phoneme engine and neutral outcomes. The state machine returns to the current word after conversation and honors the same focus/session limits. Caregiver controls enable backend connection and voice assistance outside child practice.

One manual capture feeds the relevant pipeline; never start a second microphone recorder. Speaking, recording and processing remain mutually coordinated by the existing foreground/audio guards. Stop, backgrounding, profile change or navigating away cancels pending ASR/LLM/TTS results. Every reply is bound to owner, session, turn, capture purpose and generation; a late reply cannot speak after the learner has moved on. No always-listening microphone is added.

## Conversation implementation contract

- Reuse existing caregiver account authentication. Backend features require a valid caregiver connection; anonymous local practice continues normally. Do not send `local-review-demo` as authentication or weaken JWT/ownership checks. Account connection must preserve separate local histories; no silent profile merge.
- Use a conventional local ASR model, initially multilingual faster-whisper small if resources permit, for short16kHz utterances. ASR is a separate component from the phoneme model. Its normalized text does not prove which individual sounds were spoken. Evaluate transcription and latency before deciding it is usable; uncertain/silent input asks for repetition or a picture response.
- Short audio is processed in memory by the owned backend ASR, never persisted, logged, uploaded to a cloud provider or passed to Gemma. Initial transport is the owned private backend through authenticated HTTPS, or development-only USB reverse to loopback. Do not expose an arbitrary configurable ASR upload URL or silently fall back to a cloud recognizer.
- The local text model receives only bounded transcript text, current lesson/prompt, caregiver interest, observable quality flags and a short session-only conversation history. No clinical diagnosis, asserted missing sound, scoring authority, child media or raw waveform enters its context. No chat transcript retention or inclusion in therapist email.
- Proposed endpoints: authenticated `POST /api/guide/turn` for bounded audio/text and session context, and `POST /api/guide/close` for session cleanup. Strict schemas, size/duration/rate/concurrency limits and timeouts apply. Text input supports testing/accessibility; it is not represented as speech recognition.
- Response fields: opaque `reply_id`, `session_id`, `turn_id`, short `spoken_text`, `language`, `action`, optional known `lesson_id`, and `status`. Actions are a closed set: converse, repeat example, show existing picture help, offer break, return to current practice. Unknown actions/lesson IDs, malformed output, unsupported correctness claims and unsafe output are rejected. LLM output is untrusted and cannot directly execute tools or mutate practice policy.
- Keep answers relevant to child-friendly interests and the current activity. Natural conversation does not grant unrestricted web browsing, arbitrary tool execution, medical instruction or open-ended therapy planning. Requests beyond the guide's scope receive a gentle redirection or caregiver handoff.
- Default speech output uses the installed phone Tamil TTS, including existing avatar speaking animation. Add a dedicated generated-reply speaking method; do not loosen authored-example allowlists globally. If an optional backend TTS adapter is later enabled, it accepts only validated reply IDs and approved text, never voice recordings; no voice cloning or child-name transmission to an external provider by default. Existing phone TTS remains the failure fallback.
- A backend/model/voice failure yields an honest short fallback and the existing practice controls. It never fabricates a model response, sound correction or successful conversation result.

## Fortnightly report capture and synchronization

Biweekly here means **every14days**, consistent with the existing checkup cadence, not twice a week.

Persist a bounded encrypted aggregate outbox on Android at session end, before attempting upload. Preserve last-summary behavior and add report history for new sessions; do not invent earlier history. Stable event IDs make retries idempotent. Sync requires caregiver opt-in/account ownership and an active verified report-share grant. Explicitly connect any legacy local report to the authenticated profile; never infer ownership from a child nickname.

The payload allowlist contains session ID, timestamps, bounded duration, words/letters practised, microphone-attempt counts, picture/help counts, observable support steps, breaks and completion marks. Do not send recordings, transcripts, raw phoneme sequences, diagnoses, unsupported attention measures or correctness percentages. Missing support/legacy data is unavailable, not an invented zero. Backend stores immutable accepted receipts, validates clock/range consistency and rejects conflicting reuse of an event ID.

The report includes its14-day interval, data coverage, participation totals, practiced items, support/break patterns, unavailable fields and clearly separated deterministic suggestions. Speech accuracy/mastery remains unavailable. Do not combine legacy evaluation percentages with current unscorable practice. Produce a frozen canonical report/hash and readable PDF; no LLM is required to summarize these counts.

## Scheduling and delivery

- A caregiver can enable the schedule only for their currently assigned therapist with current verified sharing permission. Use the therapist's backend account identity and confirmed recipient configuration, not arbitrary addresses supplied by a child request. Grant expiry, withdrawal, reassignment or recipient changes are rechecked before sending and before downloading a report.
- Persist schedule anchor and next due time in UTC. Close half-open14-day windows. An actual worker runs on the backend, catches up after restart and does not rely on an Android timer or a request visiting a page. If the laptop/backend is off, exact-time delivery cannot occur; durable catch-up is described honestly. Continuous delivery requires an always-running backend deployment.
- Use a durable Mongo job/outbox collection with unique owner/schedule-version/window identity and atomic claim leases. Two workers or repeated polls cannot create normal duplicate mail. Retry definite pre-send failures with bounded backoff. A crash/connection failure after mail acceptance may be ambiguous: record delivery-unknown and do not blindly resend. Do not promise SMTP exactly-once delivery.
- Generate the immutable report once per window and notify the therapist by email with an authenticated report/PDF link. Never place bearer tokens, child media or clinical claims in the email. Reuse therapist portal login/current access checks; a revoked relationship cannot use an old link. Email acceptance, recipient delivery and therapist review are different states.
- Late offline synchronization cannot silently rewrite an already sent report. Carry late records in a separately labelled section of the next report, retaining their original practice dates. If the backend has no current data, state no synced activity; do not equate that with no child practice.
- Proposed routes: caregiver schedule settings/status, idempotent aggregate receipt upload, owner report history; therapist report list/detail/PDF. Add a small caregiver-facing connection/delivery page and a report list in the existing therapist web dashboard. Child session navigation stays intact.
- Mail server/sender settings are backend secrets. No SMTP password or provider key is included in the APK, logs, response bodies or design. First verify against an actual local SMTP capture service; live provider delivery remains pending until a real sender and therapist destination are configured. Do not send unsolicited test email or use fabricated sharing approvals.

## Resources, delivery and verification

Reuse the pinned downloaded Gemma GGUF/runtime without changing research artifacts. ASR/runtime caches and build outputs go to D; preserve C>=512MiB and D>=250MiB. Current D free space is about6.3GB; recheck before downloads/builds, avoid global copies of the1.26GB acoustic graph, and preserve current APK/data/model rollback. No paid hosting/provider purchase is authorized. Backend-assisted speech on the laptop does not mean the whole APK is independently conversational offline.

Meaningful checks include actual local text-model replies, public-adult ASR samples, silence/noise/timeout/invalid replies, unsupported correction prompts, canceled/stale replies, owner isolation, and real audible reply playback. Provider mocks alone are not end-to-end evidence. Re-run Android word/letter/avatar/break/reward regressions and verify the installed acoustic model identity unchanged.

Report checks cover day14 boundaries, timezone handling, outbox retries, conflicting IDs, offline late data, duplicate workers, restart catch-up, expired/revoked grants, reassignment, unsupported metrics, mail failures and ambiguous delivery. Exercise an actual local SMTP sink and verify email content/report access; separately identify database concurrency checks needing a real isolated Mongo instance. Do not use production child data or auto-verify human grants for tests.

Completion evidence must distinguish implemented code, locally executed model/mail behavior, Android integration, actual phone checks and live external email activation. No automatic phone install, screen recording, cloud deployment or message to faculty is part of this new request. Existing recording ownership and wired-USB preference remain in effect.

## Owner decisions and activation inputs

The backend-assisted versus fully on-phone conversation choice is pending. The recommendation is backend-assisted first. A running server and real mail-sender/therapist configuration are activation dependencies; implement settings and tests without inventing those credentials or claiming delivery is active. Keys should be entered securely in backend configuration, not pasted into chat.

After approval: amend SSOT, write the implementation plan, implement and verify the backend plus Android/therapist integration, then document remaining external activation steps.

One fresh read-only builder check reviewed this draft and reported no important unanswered implementation questions. This is design review, not owner approval or runtime verification.

Primary implementation references: [faster-whisper](https://github.com/SYSTRAN/faster-whisper), [Python SMTP client](https://docs.python.org/3/library/smtplib.html), and the already-pinned local llama.cpp runtime/API contract. Model capability and integration performance still require actual execution; source documentation alone is not performance evidence.
