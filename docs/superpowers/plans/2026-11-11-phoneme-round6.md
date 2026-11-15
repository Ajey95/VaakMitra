# Local phoneme refinement round6 Implementation Plan

> Execute inline with superpowers:executing-plans. One fresh final review; one TDD fix pass, no re-review. Existing dirty isolated lab is preserved without commits.

**Goal:** Lower13.89% app-word PER using existing data/localGPU and deliver a gated experimental mobile model.
**Architecture:** Same CNN/BiGRU/CTC and audio-only decoder, extended by DEC-048 to a fixed two-member posterior mean. No scoring/product behavior change.
**Tech stack:** Existing CUDA124PyTorch, ONNXRuntime, Kotlin/Android offline SDK.
**Spec:** docs/superpowers/specs/2026-11-11-phoneme-round6-design.md

## Global constraints

SSOT PHN001..006/DEC041; train14839/cal1630/test1665; fixedV5calcap55.70071699%, testcap59.29666876%; targettest<13.888889%. No newdata/cloud/download/labels/commit/merge/push. OfficialUNSCORABLE; all exposed/adult/sourcepartition/child caveats remain.

## Review Focus

- Anchor identity/inheritance cannot loosen fixed caps.
- Ranked configuration matches checkpoint and actual source; selector helper captured before freeze.
- Rate augmentation preserves duration/no wrap or truncation; no child simulation claim.
- Final metrics replay exact delivered model/decoder/data and no format substitution.
- Honest exposed-test, word/condition regressions, publisher partitions and deployment boundaries.

### Task1: predefined local continuations

- [x] Capture trainer/base/selector/helper snapshots and rollback hashes, verifyAVD before temporary stop forRAM, no unrelated processes stopped.
- [x] Run dropout30(.8/.3/channel), balance70(.7/.2/channel), rate80(.8/.2/rate), allV7/seed401/45epochs/patience12/max20min/2e-6&2e-5/.0001.
- [x] Inspect finite history/config/source; existing relevant112Python tests before selection; no implementation change unless a real failure requires RED-to-GREEN.

### Task2: calibration selection and freeze

- [x] Derive terminal views from exactlast.pt/config/history/source; greedy replay matches history, no extra gradients.
- [x] Compare sixviews plus baseline, greedy/beam5top8, inheritedfixedV5anchor. Require strict target calibration improvement and fixedcap.
- [x] ExclusiveV8root with selection/helper/independent SHA witness before any R6test inference. If no candidate, ledger calibration-based bounded extension first.

### Task3: gated deployment and review

- [x] Export/calibrate FP32/INT8, parity/test/audit/stress and full boundONNX replay. Frozen selection unchanged. Iffinalgatefails retainV7.
- **Skipped after V8 quality rejection:** candidate nine-phone VAD/trim/native3,70JVM/lint/bothABI/newAPK staging/UI/latency.
- [x] Separately verified retained V7 source assets/APK contents/installed app and test APK hashes, restarted emulator and checked Home -> Tamil Words -> Amma ready screen; no mic or physical-phone test.
- [x] Package exactweights/ONNX/sourceprovenance/reports/rulings, finalartifactchecks; updateSSOT/context. Onefreshreview then oneImportantRED-to-GREENfixpass and green suite. Preservebranch/evidence, no secondreview.

Task2 extension DEC042: initial14 configs ineligible, rate terminal target30 but overall55.75606>55.70072. TDD average-source binding and shared-source-time accounting; form exact.5best0+.5terminal12 average using existing average_states. Both parent configs identical/source loop459.796s must count once, no new gradients. Archive actual averaging-source and both parent metadata/original trainer. Then new candidate+baseline calibration-only selection; preserve initial failed search log and caps.

Task2 DEC043: equalblend rejected on targettie. TDD boundedweightedaverage(.8right) parameter/metadata, onecandidate only. Ifineligible run conservative truefrozenencoder headtrial as exactspec above, compare itsbest/terminal oncal beforefreeze. No cap/testselection changes.

Task2 DEC044: frozen80terminalalsoineligible. RED-to-GREEN globalblank-onlylogit/state invariance and finitebounds, adddefault0CLIoffset and honestgradient_epochs/method metadata. Snapshotnewtrainerseparately fromimmutableoriginal4trialsource. Formfourfixedepoch0candidates and compareonlycal. No newgradients/labels/expectedword. ArchiveparentCP and distinguishcalibrationformationtime.

Task2 DEC045: fixedblankgridineligible, execute one earlierV5initialization/updateddropout continuation as exactspec; comparebest/terminalcal. Sourcesnapshottrainer-blank.py defaultoffset0, authenticV5CPsameDATA. No further sourcechanges needed for this trial.

Task2 DEC046: TDD optionaldeclareddecoder in evaluate(defaultgreedypreserved) and firstqualifiedcheckpointeligibility; authenticateinputV7frozenbaseline/inheritedV5same-dataanchor. One newtrainingrun usesactualbeam/fullcal each epoch; storedecoder/reference+best_qualified/history/source, terminalreplaydeclareddecoder. Runallphonemesuite beforelaunch. No test-based model selection.

Task2 DEC047: TDD optionalstatistics-only freeze acrossrepeatedtrainingcalls withactiveencoder/headgradients. RunONE V5init deployment-selected control as exactspec, saveactualsources andBNstateproof. No further blindly repeatedcontrols if thisalsofails; preservebestV7 andreportcalplateau truthfully rather than fabricateimprovement.

Task2 DEC048 distinctcompositionextension: TDD two-memberposterior arithmetic/factory schemas/legacy compatibility/sourcebinding and ONNX parity. Create MobilePhonemeEnsemble +checkpointfactory, adaptselector/exporter tofactory, explicitrejectensemblesinsingletrainer. Newassembler forms2fixedpairs withno gradients, capturesparents/provenance. Comparecal only, samecaps/freeze. Stage/runtime unchangedlogitcontract, report581402paramsandactualAndroidlatency. No newhyperparametergrid beyond2fixedpairs.

Task3 DEC-049 quality-gate outcome: V8 failed final target PER (77 versus75/540). Native3/JVM/lint/APK rebuild/staging/UI of V8 are conditional and SKIPPED, not passed. Retain and re-verify V7 assets/APKs; restart its existing emulator. Bound replay/audit/negative-result packaging plus one final source review close this round. Never retry selection from test results.
