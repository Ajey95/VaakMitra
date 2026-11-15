# Further local phoneme refinement Implementation Plan

> Execute inline with executing-plans, onefresh finalreview and oneTDDfixpass, no rereview.

Goal: lower14.81% app-word PER using existing data/localGPU and deliver experimental app after gates.
Spec: docs/superpowers/specs/2026-11-11-phoneme-round5-design.md; SSOTPHN001..006/DEC039.
Architecture: sameCNN/BiGRU/CTC290701params; immutable-by-procedure sharedhashverified cache, train14839/cal1630/test1665. Fixedbeam5top8/greedy control; no targetword/lexicon entersinference.

1. [x] Three sequential V6continuations, seed307,45epochs/patience12/max20min: focus90(channel,.9,encoder2e-6/head2e-5), quality80(channel,.8,encoder3e-6/head3e-5,minextraquality.95), dropout80(channel,.8,encoder2e-6/head2e-5,GRUdropout.2). Firsttwo use immutabletrainer-initial snapshot; third gets newimmutable source afterTDD. Preserve alloriginaltraining inqualityfilter; no cache rewrite. Verify taskAVD beforestop forRAM/restartlater.
2. [x] TDD trainingdropout evalinvariance and anchoredcaps oncal/finalmetrics. AuthenticateanchorV5 report anddataset; recordanchorcheckpoint/report inselection. Compare bothgreedy-selected best and terminal checkpoint for each of thethree predefinedtrials oncal beforefreezing; traininggreedyproxy neednot rank beaminference identically. Derivedterminalviews retain exactoriginalcheckpoint/config/source and recordderivation, no furthergradient updates. All candidatesreproduce declareddecoder calibration, config/source matchcheckpoint. Freeze exclusiveV7root andindependentdigest beforeheldoutinference. If no improvedcandidate, diagnosecal and run justifiedcontrolledextension, not testselection.
3. [x] Export/parity/test107/audit192/535aggregate-stress; finaltarget<14.8148 andbroader<=59.29666876%, no ratcheting. ActualVADtrim ninephone fixedreference andnative3; buildbothABI/pullinstalledhash/UI. Report currentwordvariation/aggregateconditions, chronologyR2expansioncorrectly. Packageweights/ONNX/sourceprovenance/rulings. V6rollback. Onefresh finalreview thenoneRED-GREENfixpass andfinalverification. No commit/merge/push/cloud/download/childclaims.

Review Focus: anchoredcap cannotratchet; same dataset/decoder-authenticated reference; trainingdropout doesnotchangeeval/state topology; provenance/true metrics onfrozenartifacts; no exaggerated adult/child/generalization or individualsynthetic claims. Guard metadata/config fixes fromR4 retained.
