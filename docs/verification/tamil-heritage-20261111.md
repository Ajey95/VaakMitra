# VaakMitra Tamil heritage learning update

Completed locally on 12 November 2026 after work began on 11 November. The final ARM64 debug APK is installed on the iQOO, verified against its SHA-256 digest, and the same source is verified on the emulator. This is a learning/review APK; child pronunciation scoring and production readiness remain unapproved.

## What is available

The traditional Tamil catalogue has **247 letters: 12 Uyir, 18 Mei, 1 Aytham and 216 Uyirmei**, with all 18 compound families and stable IDs. Exact independent inventories, uniqueness and NFC normalization are tested. The selected familiar avatar, on-tap Example, microphone, transient predicted-sound feedback, retry, Break, Continue and End use the same PracticeScreen as the 19 words. Letters add optional finger tracing and a learner-tapped **Practice complete** button. The letter and experimental-voice warning are readable on entry and after advancing, including at 2× text.

Only manual confirmation plus a successful local save unlocks the next level. Replays stay in their local sequence and cannot skip the global frontier. Sessions continue across Uyir → Mei → Aytham → Uyirmei. A practice mark records participation, never correct pronunciation, attention or mastery. A non-speaking learner can look or trace and mark practice without recording.

The visual theme uses warm paper, maroon and wood signboards, kolam borders, a pallanguzhi-inspired level board, slate cards and an original AI-generated Tamil veranda illustration. Exact Tamil is rendered natively. The generated concept was inspiration, not an actual screenshot or expert cultural assessment. Avatar choices, renderer and movement preferences are preserved. The word voice screen, feedback and break views have the matching visual treatment, with the original word model, targets, next/retry and report behavior retained.

## Pacing and privacy

Learners/caregivers can choose 1, 3 or 5 practice marks per round, optional quiet stamps and voluntary breaks. A first/then cue and optional transient tracing support predictable activity. Foreground focus/session budgets and background/recreation pauses remain. At large text, the voice panel scrolls with the lesson and the red Stop remains fixed. These are adjustable learning supports, not proof that the app sustains attention or has clinical benefit.

The microphone is still a debug-only preview. No new private voice recordings were collected, exported, uploaded or used for training during this work. Recorded PCM and bounded tracing stay in RAM; owned attempt buffers clear after processing/cancel. This is not a forensic erasure claim about native/OS memory. Tests used public audio fixtures and isolated practice state; the static screenshot walk made no user practice marks and never pressed Example or microphone.

An installed offline Tamil system voice is required for Example. Selection rejects network and not-installed voices, requires a successful selection and matching active voice, and reports asynchronous synthesis failures for the current utterance. Voice examples are explicitly experimental/unverified. Mei may be read as names/contextual forms; Aytham reads its name **ஆய்தம்**, not an invented isolated phoneme. No external synthesis or voice download is initiated by the app.

Letter progress stores only counts and rhythm settings under a hashed account/child-alias scope. The existing app has no stable multi-child identifier, so this is alias-scoped. An unidentified authenticated account cannot save/read a shared fallback journey; explicit offline review has its own deliberate namespace. A missing identity in a new auth response clears the previous persisted email. A last-confirmed writer prevents failed disk writes from becoming false saved marks through the SharedPreferences memory cache.

## Validation and review

| Check | Final evidence |
|---|---|
| Full JVM suite | **100 passed**, zero failures/errors |
| Offline build | ARM64, x86_64 and test APKs built successfully |
| Android lint | **0 errors, 17 warnings**; existing toolchain retained |
| Physical iQOO | **17/17 passed**, installed main/test APK digests matched |
| Emulator | **17/17 passed**, installed main/test APK digests matched |
| Acoustic regression | Original three public word goldens retained; same public waveform yields the same unscorable phones across different known letter prompts |
| UI | All categories/locks, replay, global category transitions, final level, background/recreation, normal/2× text and readable targets checked without private mic capture |
| Source/model binding | Eight protected whole files remain identical; original engine assess, word reducers, Mic widgets, word continuation and capture body preserved with explicit safety exceptions |
| Final review | One fresh **AI code review**, six Important findings addressed in one fix pass; no re-review or human/clinical approval claim |

The Important fixes cover initial letter visibility, immediate lifecycle audio/permission cancellation, durable-save acknowledgement, installed offline voice selection/error handling, late model-factory ownership, and missing account identity. New APIs were observed failing before implementation; injected lifecycle, disk-failure, voice and late-factory cases now pass. Initial glyph clipping and later 2× scaling failures were observed as native assertions before the layout/font correction. Earlier unsuccessful runs remain recorded. A physical header lookup timeout passed in isolation; its cause was not established. The final complete runs are green on both devices. A full-run word-font screenshot appeared clipped; an unchanged isolated rerun passed and produced a fully visible Stop capture. The cause of that screenshot discrepancy was not established.

Two minor issues remain deferred: the letter voice panel wording still suggests an Example/mic sequence although speaking is optional, and time accounting polls every 500 ms, allowing a confirmation within one tick before the next deadline settlement. Full decisions/costs are in evidence/review-rulings.md. No clinical efficacy, child acoustic accuracy, individual sensory comfort or expert-quality system-voice pronunciation was established.

## Model and additional words

The V7 model is **unchanged**, SHA-256 `94c30918c5be357d7384ddc6dd39fb65ed16ae80a507699b649332c049885683`. Every official outcome remains **UNSCORABLE**, with `production_ready=false` and `approved_for_child_scoring=false`. Isolated-letter predictions can be inaccurate. Letter targets never enter the word-classifier fallback or word reports, and the expected prompt is not supplied to ONNX/CTC. No new training, model replacement or paid cloud resource was used.

A frozen-model probe used only previously exposed public calibration clips, not fresh held-out/live/child data. Processed exact-sequence counts were Naan 1/4 (one abstention), Ithu 1/2, Athu 2/5 and Sari 0/1. No reliably recognized new word was established. Keep the existing 19 words; Aam, Padam, Innum, Sol and Vendaam are candidates for controlled next phone checks based on tiny existing calibration matches, not guarantees. The three-child vowel recordings have not been supplied or used.

## Looseleaf feasibility

The user also asked about [Looseleaf](https://github.com/kevintngo/looseleaf). Its documented React/Tailwind/Radix paper-and-ink components suit the visual direction. The web frontend could integrate those components after compatibility work; the native Android app needs a Compose adaptation of the look. Retain the Tamil typeface, existing avatars, quiet motion and session sequence. The [MIT license](https://github.com/kevintngo/looseleaf/blob/main/LICENSE) requires retaining its copyright and license notice for reused material. **No Looseleaf package, code, font or art was added in this task.** This is a feasibility finding, not a completed integration.

## Files and limitations

- `VaakMitra-Tamil-Heritage-arm64-debug.apk`: final physical-phone build.
- `changed-source.zip`: verified explicit source-change package for the existing lab, not a standalone project with all dependencies.
- `SHA256SUMS.json`: delivery file bindings.
- `evidence/final-verification.json`: test, model, source and installed APK bindings.
- `evidence/01-home.png` through `05-word-voice.png`: controlled final emulator UI screenshots.
- `evidence/final-letter-ui-large-font.png` and `final-word-ui-large-font.png`: controlled 2× phone captures.

The branch remains `codex/backend-verification-lab` at HEAD `712de54ee568da6262131f06092c0d4d251b2c92`, with changes uncommitted. No merge, push or cleanup was performed; unrelated existing work and protected reference roots were preserved.

Design references: [Tamil Virtual Academy](https://www.tamilvu.org/coresite/download/Basic_Ebook.pdf), [NICE CG170](https://www.nice.org.uk/guidance/cg170/evidence/autism-management-of-autism-in-children-and-young-people-full-guideline-248641453), and [National Autistic Society](https://www.autism.org.uk/advice-and-guidance/about-autism/sensory-processing). These guide the approach and do not validate this app/model.
