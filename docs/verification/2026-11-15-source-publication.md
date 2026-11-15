# Source publication — 15 November 2026

Owner requested the current project on `Ajey95/VaakMitra` `main`, with the previous `main` preserved as a new branch. This is source publication; it does not activate conversational guidance, therapist email delivery, a new acoustic model or clinical scoring.

## Preservation and scope

The previous remote main commit is `160037a051a864da1c49a7252608002ffa957277`. It was pushed and independently read back at `backup/main-before-update-20261115` before updating main. The publication is a normal descendant commit, not a forced history replacement.

The development worktree originally pointed to a different upstream repository. Publication therefore uses a separate target checkout; the development branch/index and the other remote are preserved. Its current Android, FastAPI, frontend, training/export tools, tests, documentation and required source assets are included. The optional Unity submodule retains commit `881f617723d0ece135ea3814872e979c4e6df25b` and its original URL. The Gradle wrapper is executable in Git for Linux CI.

Private recordings, credentials, local workflow tokens, machine-only handoffs, trained model/tensor binaries, APKs and generated output are excluded. Native model metadata/vocabulary remain available; model provisioning is separate and hash checked. The model card's public-release limitation is preserved. Public adult audio fixtures retain source/license attribution and engineering-only limitations.

## Publication fixes

- Added source exclusions and narrowly constrained secret-scan exceptions for a public token-inventory checksum and React password-strength display code. Each exception requires both its exact file path and line structure.
- Declared the ML/unit-test dependencies, used supported Node22 in CI and installed CPU PyTorch before the development requirements. Pretrained model fetching is disabled in CI tests.
- Explicitly selected the original TorchScript export mode (`dynamo=False`, MST-005). This resolves newer PyTorch choosing another exporter; quantization/scoring logic and existing model artifacts were not changed.
- Constrained development NumPy to 1.x (tested at 1.26.4) because ONNX Runtime percentile calibration fails on narrow float32 histogram ranges with the tested NumPy 2.x versions. The existing export/quantization tests passed after the constraint; their thresholds were not relaxed.
- Updated vulnerable Axios/redirect and Zod dependencies, including the compatible form resolver. Added focused normalization, invalid-input and cross-field error-mapping checks for the resolver integration.
- Updated README to distinguish current Android implementation, legacy backend surfaces, proposed conversation/reports and model/physical/clinical limits.

## Local verification

- Backend: 819 collected, 817 passed, 2 CUDA-only cases skipped, zero failures/errors. The skipped cases require actual CUDA AMP/reconstruction; this CPU run is not their validation. Earlier dependency/export compatibility failures are retained in local evidence.
- Web: 251 tests passed in 50 files after dependency updates; lint and production build passed. The production dependency audit reports zero vulnerabilities after updating the redirect dependency as well.
- Android: 275 JVM tests across 54 suites, zero failures/errors/skips; lint and both debug ABI source-only builds succeeded. This build intentionally contains no trained graphs and does not establish live microphone recognition or clinical readiness.
- One read-only publication review found no material blockers in the scoped publishing/export/test-dependency changes, followed by bounded web security dependency updates and final checks. This is not an application-wide clinical or security certification.
- Secret scan on the selected source snapshot: zero findings after reviewing the two non-secret matches. Existing EOF-whitespace warnings, Android deprecation/compile-SDK warnings and web chunk-size warnings are retained; no warning-free claim is made.

Detailed manifests, redacted scans, JUnit and failed/successful logs are retained locally under `D:/VaakMitraBuildTemp/publication-20261115/evidence`. The installed phone APK/model and the owner's recording workflow were not changed by publication. Refer to the earlier [Android review verification](2026-11-14-clean-learner-flow.md) for the separate emulator/native evidence and its limits.
