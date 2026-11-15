# Local phoneme round6 — V7 retained

The laptop GPU search did not produce an accepted improvement. The single frozen V8 candidate scored **77/540 phone edits (14.25926%)**, versus **75/540 (13.88889%)** for V7. We rejected V8 and preserved the existing V7 app model. No weights, decoder, thresholds or runner-up selection changed after test results.

| Measure | Existing V7 | Rejected V8 |
|---|---:|---:|
| App calibration (105 clips / 547 phones) | 31/547 (5.66728%) | 30/547 (5.48446%) |
| App test (107 clips / 540 phones) | 75/540 (13.88889%) | 77/540 (14.25926%) |
| Exact test sequences | 80/107 | 80/107 |
| Broader test (1665 clips) | 59.10591% | 59.09805% |
| Exposed audit (192 clips) | 8.70668% | 8.79121% |

The broader cap stayed fixed at59.29667%, anchored to V5. V8 passed that cap and FP32/PyTorch decoded parity (zero differences on1665 clips), but failed the required strict app-test improvement. INT8 was rejected on calibration agreement (93.37423% versus98% required). Selection/helper/checkpoint/architecture dependencies were captured in an independent witness before R6 test inference. Full ONNX replays for V5/V7/V8 bind reported metrics to actual bytes; see evaluation-replay.json.

Seven bounded gradient-training controls completed: regularization, sampling, rate augmentation, whole-encoder freezing, earlier-checkpoint restart, deployment-decoder checkpoint selection and BatchNorm-statistics freezing. Calibration also compared fixed checkpoint averages, four global blank-bias offsets and two fixed output combinations. 81 recorded configurations/epoch measurements (not independent training trials) are listed in calibration-search.json. All individual gradient trials failed qualification. The V7-plus-normalization two-member arithmetic posterior mean passed calibration and was frozen once, then rejected on the final test. It contains581402 parameters versus290701 per member and doubles acoustic inference work; no mobile latency was measured for V8.

The seven training loops totaled46.33minutes, including per-epoch CPU calibration. This excludes setup, search, export and packaging; it is not pure GPU kernel time. Cloud cost was **₹0**; electricity was not measured. All existing data remained in use (14839 train /1630 calibration /1665 test); no downloads, new labels, cloud, commits, merges or pushes.

Synthetic adult-audio stress results are descriptive, with535 derivatives of107 parent clips:

| Condition | V7 PER | Rejected V8 PER |
|---|---:|---:|
| noise20 | 15.74074% | 15.00000% |
| noise10 | 14.62963% | 14.44444% |
| echo | 14.62963% | 14.81481% |
| lowpass | 14.44444% | 14.07407% |
| quiet | 14.25926% | 14.07407% |

These condition aggregates do not establish per-clip, child or pronunciation-error robustness. Per-word/speaker/edit counts are in error-analysis.json. Calibration improved while test regressed, so this round does not support further quality claims from repeated tuning alone.

V8 was never staged or installed. Its Android build, JVM/native tests, VAD/trim parity, UI and latency checks were skipped after the earlier quality gate failed; none is claimed passed. The existing V7 source bundle, APK embedded assets and both installed emulator APK hashes were re-verified unchanged (retained-v7-proof.json). The Phoneme_34 emulator was restarted and its retained V7 Home -> Tamil Words -> Amma screen reached the ready state, verified by a fresh UI XML snapshot (retained-practice2.xml). No recording was made. The150 scoped Python tests passed; V8 native tests were not run. Previous V7 native/build evidence is historical, not a new V8 result. The current ARM64 APK is the previously delivered V7 build in ../phoneme-round5-20261111; no physical-phone or live-microphone test was performed this round.

All models remain experimental: official **UNSCORABLE**, approved_for_child_scoring=false, production_ready=false, transient audio-derived tokens. The107-test and192-audit sets have been exposed in earlier rounds; results are descriptive, not fresh generalization. Custom speaker folds reuse341 publisher-test training clips from334 utterances, so the publisher benchmark is not untouched. The audit covers15/19 words with71 Vendum clips. Project speaker/audio split checks do not establish upstream pretraining independence. Labels remain provisional, without expert acoustic review. Child vowel recordings from three children were not supplied to this run; child, clinical and physical-device performance remain unvalidated.

Keep V7 for the present app. A stronger next experiment needs a genuinely separate speaker/session evaluation set and better-targeted phone supervision; simply repeating searches against these exposed sets cannot establish a reliable improvement. The user's existing child recordings may support a later speaker-held-out child evaluation after they are supplied; three speakers limit confidence. This round's rejected weights/source are archived for reproducibility, not app use.

Authority: PHN001..006 / DEC041..049; docs/verification/phoneme-round6-20261111.md, SSOT3.3.32, plan/design and review rulings. One fresh final review completed; five Important issues were fixed in one observed RED-to-GREEN pass.155 phoneme tests plus3 delivery tests passed (158 total). Strict qualified ranking, parent provenance, runtime encoder dependency, optimized-interpreter fail-closed validation, recovery metadata and the checklist were corrected in current tools. Frozen model/decoder/selection/source captures remain unchanged. No deferred issues or second review. Full rulings and final verification are recorded separately.
