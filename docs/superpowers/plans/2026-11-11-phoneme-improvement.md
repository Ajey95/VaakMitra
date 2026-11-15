# Existing-data phoneme improvement

User authorization: improve PER using existing local data and GPU, keep working until an improved model can be deployed. Applicable authority: SSOT DEC-030, PHN-001..006. Existing isolated worktree codex/backend-verification-lab; preserve all unrelated changes and read-only source repositories.

Spec: D:/VaakMitraData/analysis/phoneme-improvement-20261111/improvement-plan.md. Implement the following bounded experiments, then adapt from calibration evidence if needed. No target-conditioned decoding, test-data training, synthetic child claims or correctness scoring.

### Task 1: Safe continuation runner and first experiment

Interfaces: existing immutable dataset/cache/vocabulary/best checkpoint -> new run directory, independent checkpoints, calibration-only history. Never mutate hard-linked cache files. New training loader must not sample validation/test rows. Tests verify per-word balancing, no held-out sampling, augmentation preserving content and duration, and checkpoint binding validation.

Steps: write tests and observe failure; implement runner; run focused tests; run CUDA continuation from selected epoch22 with balanced target/other-word batches and low learning rates. Save optimizer/RNG/config/checkpoints. Expected: finite training updates and calibration-only selection/evidence; original artifacts unchanged.

### Task 2: Audit and expand data

Interfaces: original source manifest, alignment quality metadata, existing sentence corpus and transcript index -> versioned audit and expanded training manifest. Preserve speaker/parent identities and independently reserved splits. Test leakage guards and alignment bounds. Expected: measured quality exclusions and independently sourced extra word clips, or a concrete measured extraction limitation. Do not call machine filtering expert review.

### Task 3: Controlled comparisons and final evaluation

Interfaces: runner + audited/expanded input -> calibration comparison, fixed candidate, one final old-test and untouched-audit comparison where available. Compare a small number of defined experiments rather than chasing test results. No evaluation access during training. Expected: lower target calibration PER with no major broader-vocabulary regression, then lower final target PER than28.33%; otherwise continue from calibration diagnosis without deploying a worse model.

### Task 4: Export, app deployment and evidence

Interfaces: selected fixed checkpoint -> hash-bound FP32/INT8 bundle -> Android assets -> emulator instrumentation and APK. Expected: sequence parity, no target word in decoding, native VAD/trim/model path passes, improved results documented and rollback preserved. Keep official UNSCORABLE. Update SSOT artifact/results evidence, context handoff and delivery report.

Review focus: training/test and parent leakage, cache/checkpoint source bindings, false lower-PER claims, machine-label provenance, Android model/vocabulary consistency, unrelated work preservation.

Validation: focused Python tests, real finite CUDA run, calibration and final-test reports, export parity, Android unit/lint/build and native instrumentation as affected. One final fresh-context review required by executing-plans skill. No commits or merges are required for this already dirty experimental worktree; retain evidence and source files.

Completion: all four tasks and the final review fix pass are complete. Final29 Python tests,56 JVM tests, lint/both ABI builds,3 native tests, artifact hashes and measured PER improvement verified. Detailed evidence/rulings: .superpowers/sdd/2026-11-11-phoneme-improvement/progress.md and D:/VaakMitraData/deliveries/phoneme-improvement-20261111/results.md.
