# Local live-tempo implementation plan

Execute inline with superpowers:executing-plans; spec docs/superpowers/specs/2026-11-11-phoneme-live-tempo-design.md. PHN001..006/DEC050. Existingisolatedlab, no commits.

## Review Focus
- Pitch-preserving independent-channel transform; no speech truncation/wrap/privateaudio.
- Capturedsources/config/model/data/immutableV5anchor agree.
- Strict clean-cal and independent-tempo-bank gates; no test-basedreselection/wordforcing.
- Runtime/recognition evidence and unresolvedlive failures reported distinctly.

### Task1 — causal probe and TDD augmentation
- [x] Preserve publiccaldiagnostics andcorrectruntime-onlyclaim.
- [x] Tests for identity/silence/pitch/duration/no mutation/unsafe expansion/invalidfactor observedRED, then implementtempo_in_padding andmode integration/defaultsunchanged, actualCUDA smoke. FullphonemePythonGREEN before training. Architecturefiles unchanged.
- [x] Form public105cal tempo bank at1.5/2/3 whenactualcompleteaudio fits3sec; recordeligibleparents/labels/hash/FFmpegbinaryhash/factors before training, no truncation. Publiconly.

### Task2 — ONE bounded local trial/cal selection
- [x] Snapshottrainer/baserunner/selector/helper/decoder; run exactlyconfigspec, logs/noreselectiontest.
- [x] Actualdeclareddecoder best/terminalcal/source replay; applyexistingstrictfixedcaps plusindependent bankquality gate. Ifnoeligible model retainV7, skip conditionaldeployment and finishnegativehandoff.

### Task3 — conditional deployment, review and handoff
- [x] Onlyqualifiedcandidate freeze/export/parity/finalgates/native/build/physical/userrepeat; skipafterearlierfailure and donot claimfix.
- [x] Evidence/provenance/sourcearchives/docs/context plusONEfreshfinalreview(mostcapablemodel)/onefixpass, finalhash checks. No externalpublish or commit.


DEC051 evidence-led diagnostic extension before final review: user rejected file retention and explicitly chose fifteen adult captures kept in phone memory/erasedpertrial. Add only androidTest PhonemeLiveDiagnosticTest.kt; no mainapp/modelchanges. Operator taps Record for each2.5s promptedword, Stop/Back/cancel immediate. Defaultskipwithoutoperator_memory_opt_in=true; no automaticbackgroundrecording. CapturetheactualMIC PCM viaexistingWordPcmRecorder; compare rawmodelinput(if<=3s) vsactualMobileWordPracticeEngine onidenticalsamples. Canonicalprompt editcounts are not expertgroundtruth/accuracy score; outputs transient, logs onlynumericcounts/knownprompt/capturecondition/reason, no audiofiles/phonemes. Clearrecording/internalbuffers/temporarytokenIDs finally.5words*3, no training. Buildoffline testAPK+70JVM/lint, run3oldnativegoldens+purecounttest/defaultskip beforeoperator session. MainAPKhash/modelunchanged. Finalonefreshreview covers both completedtrainingcontrol anddiagnostic afteractualresults; no extra review before then. Ifcomparisondoesnotidentifyfix, discloseunresolvedlivefailure and no acceptedmodel.


Completion annotation: snapshot timing exception disclosed in training-intent.json; authenticated V7 decoder source now archived. Conditional candidate deployment was SKIPPED after both clean-calibration views failed. DEC051 review clarification/SSOT3.3.35 permits minimal recorder/VAD/wrapper memory hardening; this later main APK retains V7 weights/decoder, and does not change actual historical15 results. One fresh review and one fix pass complete with168Python/8integrity/74JVM/lint/build/native6pass+1defaultskip. No new private capture, training, final heldout evaluation or recognition-success claim. Owned ledger preserved because no commits/integration were authorized. Final source/archive verification follows.
