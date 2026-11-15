# Further phoneme improvement from v3

User authorization: keep improving22.8% PER using existing data and laptop GPU. Existing isolated lab worktree; preserve prior checkpoints/deliveries and protected reference roots. Authority DEC-030/031, PHN-001..006; amend PHN-003 before implementing optional150-frame architecture.

## Task 1: Controlled timing/continuation experiments

Keep source dataset/cache/vocabulary immutable and use exclusive new output roots. Start from v3 checkpoint95b11b...072f17. Predefine comparisons: gentle40ms continuation (LR encoder1e-5/head1e-4, seed93, current augmentation/50%target sampling);20ms last encoder stride with transferred weights;20ms with65%target sampling if calibration supports it. Select on the original speaker-disjoint calibration only, using the existing .7target PER+.3overall PER score and no >1pp overall regression. Do not read new evaluation results until a candidate is frozen. Tests must cover40/20ms shapes and strict checkpoint architecture/frame metadata, old checkpoints default40ms, no target conditioning, immutable artifact protections.

## Task 2: Conditional stronger acoustic teacher

Check an isolated local Linux runtime in the D-hosted Ubuntu distribution, avoiding the nearly-full C/E drives and slow NTFS package installation. Use cached wheels and existing pinned teacher weights; no cloud or credential flow. Measure a canary before committing to feature extraction. If a teacher is useful, cache train/calibration acoustic representations with explicit source/checkpoint/split bindings, train a phoneme head from true transcript-derived phone sequences, then distill acoustic representations/phone logits into the mobile student. Never substitute word-ASR text probabilities for phone probabilities. If compact-model experiments already give a useful improvement, stop unused setup work and record its state rather than claiming the teacher was trained.

## Task 3: Freeze, final comparison and app integration

Choose a candidate using calibration only. Freeze candidate/source/checkpoint hashes before descriptive old-test evaluation. The old test was already exposed; do not claim fresh independent validation. Require measured target PER lower than22.7778%, export token parity and no material broader-vocabulary regression before app replacement. Export model frame metadata consistently; native Android must validate75/150 output frames from a bounded manifest contract. Keep official UNSCORABLE, ephemeral tokens and no audio storage. Run affected Python/JVM/lint/build/native tests, quantify latency, deliver APK/model/report/per-word-D-S-I evidence on D, update SSOT/context and retain rollback. If no candidate improves, preserve the existing deployed model and continue from calibration diagnosis rather than hiding the plateau.

Review Focus: test leakage and repeated evaluation tuning; source/checkpoint/vocabulary/frame bindings; weight transfer correctness; no target-conditioned inference; frozen cache preservation; native frame contract and actual VAD/trim/model path; truthful quality/teacher/child/device claims. One final fresh-context review per executing-plans skill, followed by one regression-tested fix pass if needed. No merge or commit required in this existing dirty experimental worktree.
