# Local clean-anchored phoneme continuation

Authority: SSOT 3.3.53, DEC-067 / PHN-007; DEC-051 for the foreground adult diagnostic. Work remains in the existing dirty `codex/backend-verification-lab` checkout at HEAD `712de54ee568da6262131f06092c0d4d251b2c92`. No commit, merge, push, cleanup, new training download, cloud runtime or child-recording use.

## Status

Both controls completed six epochs, then stopped at the predeclared six consecutive ineligible epochs. The terminal freeze has `winner=null`, no eligible candidates and unchanged teacher. The training runner did no evaluation inference/private training audio; the separate historical native-fixture exception is disclosed below. Total runner time was 592.391 seconds including baseline/calibration. No replacement has qualified or been installed. V7 remains the main application model and remains UNSCORABLE, `production_ready=false`, `approved_for_child_scoring=false`. Nothing in this report establishes child pronunciation accuracy or a resolved live-recognition issue.

| Adult calibration group | Retained V7 | Control1 terminal | Control2 terminal |
|---|---:|---:|---:|
| Old19, 547 phones | 31 edits / 5.67% | 42 / 7.68% | 37 / 6.76% |
| New6, 93 phones | 51 / 54.84% | 39 / 41.94% | 43 / 46.24% |
| Focus18, 400 phones | 73 / 18.25% | 64 / 16.00% | 66 / 16.50% |
| Broad, 12,413 phones | 6864 / 55.30% | 7151 / 57.61% | 7084 / 57.07% |
| Correlated tempo variants, 1641 phones | 1442 / 87.87% | 1060 / 64.59% | 1065 / 64.90% |
| Slowed Amma, 24 phones | 23 / 95.83% | 13 / 54.17% | 15 / 62.50% |

All twelve epoch checkpoints failed joint qualification. Better focused/tempo results therefore do not establish a better deployable model. Cloud GPU spend was ₹0; laptop electricity was not metered. Historical exposed-test 13.89% remains a different result and was not recomputed or improved here.

## Inputs and protocol

Existing immutable V7 checkpoint/base cache, focused25-v2 metadata/sidecar and public tempo calibration bank are reused by read-only memory mapping. Sources, cache hashes, reserved-source audit and the two configurations are captured before optimizer updates in `C:/Users/AJEYA/VaakMitraArtifacts/phoneme-live-anchor-20261112-v3/training-intent.json`. Actual runtime is Torch 2.6.0+cu124 and the laptop RTX 4060, not the older Torch version in historical context notes. No data or dependency installation.

Both controls use paired clean CTC, sparse pitch-preserving tempo CTC and frozen-V7 clean-logit KL preservation. The decoder remains acoustic-only beam5/top8, 61 tokens, 75 frames at 40ms, 48,000 input samples. No prompt/expected phones enter inference. Fixed configuration details and bounds are in the design, plan and intent; there is no held-out-based reselection.

Qualification requires strictly fewer focus18 and tempo edits, no old19/new6/broad regression, unchanged positive record/phone denominators, the fixed broad cap, and no regression on slowed Amma. Full evaluation-cohort inference remains withheld; the previously exposed engineering fixture is a separate exception below. A failed control is retained as research evidence, never promoted by choosing its best-looking subgroup.

The starting calibration reproduces V7 exactly: old19 31/547 edits (5.67%); new6 51/93 (54.84%); focus18 73/400 (18.25%); broad 6864/12413 (55.30%). Public correlated tempo variants: 1442/1641 (87.87%); slowed Amma 23/24 (95.83%). These are adult/provisional-label calibration counts, not the historical exposed-test 13.89%, phone accuracy or child evidence. Slight tempo differences from older reports are actual current-runtime results, not silently substituted historical numbers.

## Failures before training

Attempt1 expected a reserved-identity field absent from the immutable legacy metadata; it stopped before intent/gradients. Attempt2 independently audited the 80 extra parents against base and reserved source identities and reproduced calibration, then failed before its first backward/update because the inherited collate returns padded 2D CTC targets rather than concatenated targets. Both failed runs and their logs are preserved. No historical binding was rewritten.

A padded-target selection regression failed first, then passed after correction. Fifteen scoped tests passed. An actual 64-clip CUDA forward/backward smoke check produced finite loss 2.638450 and gradient norm 5.376719 with teacher frozen, without an optimizer step. The corrected v3 run starts in a fresh artifact root with corrected sources frozen before actual training.

## Adult diagnostic boundary

The user confirmed availability for the phone test. Any private utterance requires a foreground Record tap, remains in owned phone memory, and is erased after its comparison; no private audio or predicted token strings are saved, uploaded or used for training. Numeric comparisons against a displayed canonical prompt are prompt agreement, not expert transcription of what was spoken.

Before control2 starts, the diagnostic probe is fixed as that control's terminal checkpoint, regardless of its subgroup results. If it fails qualification it may only appear in a clearly identified test APK for a paired memory-only investigation while the main app retains V7. This diagnostic does not turn an unqualified checkpoint into a deployment winner or change selection gates. Old rejected-tempo assets/results remain historical evidence.

## Remaining work

The bounded training/diagnostic protocol is finished; **reliable live phoneme recognition remains unresolved**. Do not infer successful recognition from an instrumentation test completing. Fresh initial baseline checks confirmed main APK `0c69dac144cb8206fd7bfaf9cf9dc3ebde2c19284f0ca1b696229911fce702da` and historical test APK `78628d068b99d92fb78094bda257ccb8b9784b7bf92ce929b8551a6dae5992a5` by phone-side SHA256; all five public phoneme fixture/reference tests passed. Final diagnostic APK is identified below; main APK remains unchanged.

## Final review corrections and evidence boundaries

The one fresh reviewer found no Critical issues and four Important issues. The inherited checkpoint metadata issue was regraded Important because it misstates the new checkpoint's active dataset identity/count and carries unrelated parent training state. One correction pass covers all five; historical v3 data, intent, checkpoints, freeze and original export proofs remain intact. Current hardened source intentionally differs from the completed run; it must not be rebound to v3 or represented as the code that trained it.

1. The original diagnostic did not cancel on activity pause. The corrected test-only recorder is bound to one resumed activity lifetime: Home/lock/pause cancels it, blocks queued starts, prevents publication after cancellation, and never automatically restarts on resume. Fake lifecycle/recorder and cancellation-during-comparison erasure tests precede any private capture.
2. The 513 export cases are **197 natural calibration +315 correlated tempo calibration +1 already-exposed evaluation-origin public fixture**. That fixed parent fixture and its existing five synthetic variants were used by retained-V7 native goldens during training, and by candidate export/native parity after the no-winner selection freeze. It never entered gradients, hyperparameter changes or candidate selection. The full evaluation cohort was never inferred. The original export proof's `calibration_only=true` and blanket `evaluation_inference_accessed=false` are inaccurate; the additive `diagnostic-probe/export-provenance-correction.json` supersedes those flags without rewriting the proof. Future reporting derives roles from actual source hashes/splits.
3. Nine listed Python sources were bound before v3 gradients, but imported `mobile_student_model.py` was omitted; its hash was first explicitly bound at export. No claim of a retroactive pretraining binding. Future runner includes the imported encoder/state helper, and the future exporter rehashes focused metadata, base/extra/tempo caches and bank manifest before parity. Correction-time hashes are identified as such, not claimed as a check performed by the old export.
4. Original independent checkpoint/history writes could strand interrupted resume or detach best weights from evidence. Future epochs publish immutable model/optimizer/history checkpoints through one atomic authoritative pointer. Resume ignores orphan/uncommitted convenience files; candidate derivation rechecks committed eligible records and hashes. A controlled interruption before pointer replacement proves prior model recovery; corrupt committed candidate bytes fail closed. Completed v3 has no eligible/best candidate, so its outcome is unchanged.
5. Historical control2 checkpoint binding inherited `row_count=18134` although the focused dataset contains18214 rows; parent best/stale/RNG/experiment fields also survived. Preserve and disclose that artifact. Future checkpoints construct explicit active child state/counts and keep applicable parent-only metadata under `parent_provenance`.

No live recognition/child accuracy conclusion, forensic OS/native memory wipe, or unrelated dirty UI review is implied. Owned PCM clearing is the privacy guarantee. Original avatars/session/rewards and main APK/model remain unchanged; 19 protected source/assets match their prior manifest. Before correction, actual iQOO public checks recorded10passes and1interactive assumption skip; the corrected APK must pass its expanded checks before an operator Record tap.

## Completed adult phone comparison

The correction passed all206 scoped backend tests. Gradle verified180 unchanged JVM test reports, lint0errors/8warnings and assembled the test APK. The corrected phone suite passed12 public checks plus one private-test assumption skip. A further real-Activity/fake-recorder check was added after the first launch cancelled, raising the final public suite to13passes plus1private default skip. It showed real lifecycle RESUMED/cancels0; an initial-resume race was **not reproduced**, so no speculative relaxation of the guard was made. This added verification test passed on its first run; it is not represented as a RED/GREEN bug fix.

Attempt1 exited at the pre-recorder cancellation assumption after1.883s. The user reported no prompt. No recorder start or PCM comparison occurred; only the bound-model header was logged. Preserve `analysis/operator-attempt-1`. After explicitly foregrounding the unlocked app, attempt2 displayed its dialog and completed all15 operator-tapped comparisons in68.018s. No microphone taps were automated. Native progress1..15, numeric ordinals/prompts, model/baseline hashes, canonical reference counts and erasure markers reconcile in `operator-attempt-2/operator-summary.json`.

| Prompt | Retained V7 exact prompt matches | Unqualified anchor probe exact prompt matches |
|---|---:|---:|
| Amma | 3/3 | 3/3 |
| Appa | 2/3 | 2/3 |
| Unavu | 0/3 | 0/3 |
| Vendum | 0/3 | 0/3 |
| Serndhu | 0/3 | 0/3 |
| Total, actual practice preprocessing | 5/15 | 5/15 |

Both processed paths accepted all15 captures. Total edit disagreements with the canonical prompts were63 on V7 and46 on the probe, over75 canonical reference tokens; **this is not PER against expert transcription**, so do not report it as acoustic accuracy. Feeding whole untrimmed captures directly produced84/56 disagreements and1/2 exact matches respectively. Current paired evidence therefore does not support bypassing VAD/trim. The probe reduced disagreements but did not make any of the three difficult words exactly match its prompt. Neither the clean-regressed checkpoint nor this adult session establishes readiness for child pronunciation decisions or independent speech therapy.

Actual operator pair: main APK `0c69dac144cb8206fd7bfaf9cf9dc3ebde2c19284f0ca1b696229911fce702da`; test APK `b7fa3fb53062c71eee6daddafe540845683784bc0fe58ea4301ac921874b2d7a`; test source `dedcf7e73ee516ad3c119fb58d111a71ddc444dab28167f79efb9e789f8f83d9`. All were frozen/phone-SHA matched before Record taps. Test-only model `fdd54c165ff083f6fdac748fdd4072b62aed104aae28f11c2cbd637fcadbf495`, checkpoint `09b500ab897abb300f4fcf0f2ee4d2e3010b7fbb91677da3adbbd62ed63b8630`, and additive provenance correction were bound in attempt2. The main app remains V7 `94c30918...`; no model promotion or user-flow change.

Each comparison cleared owned PCM before publishing counts. No utterances, predicted token strings or private audio files were saved/uploaded/used for training. The archived operator evidence contains numeric diagnostic metadata only; do not publish it as an independent corpus or clinical evaluation. Original source/proofs and the failed first launch are preserved separately from later verification additions.

Next technical work must address the remaining acoustic/label/coverage gap without treating canonical prompt agreement as a verified transcription. Existing-data preprocessing/label audits or a separately authorized representative labeled recording set are possible follow-ups; neither was performed here, and improvement is not guaranteed. The three-child vowel data was never supplied. Full held-out cohort inference and clinical/child approval remain absent. Training is an unsuccessful joint-qualification experiment, not a solved model deployment.

Evidence roots: `D:/VaakMitraData/analysis/phoneme-live-anchor-20261112`, `C:/Users/AJEYA/VaakMitraArtifacts/phoneme-live-anchor-20261112-v3`; source/evidence handoff `D:/VaakMitraData/deliveries/phoneme-live-anchor-20261112`. One fresh AI source review and one Important correction pass; all five issues addressed, no rereview/deferred minors. No commit/merge/push, cloud GPU charge, new dependencies or protected-root changes.


