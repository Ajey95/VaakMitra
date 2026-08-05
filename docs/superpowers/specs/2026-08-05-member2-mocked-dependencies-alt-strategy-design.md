# Member 2 Mocked Dependencies and Alternative Model Strategy

Date: 2026-08-05  
Status: Proposed for implementation  
Owner: Backend Member 2

## 1. Objective

Extend the Member 2 implementation so the complete three-member interaction can be exercised before
Members 1 and 3 deliver their real modules, while improving the model-development path beyond the
current tiny adult-TTS proxy experiment.

The implementation must preserve the project ownership boundaries. Member 1 and Member 3 behavior is
represented only by explicit test and demonstration adapters. No mock output may be presented as real
alignment, therapist feedback, clinical validation, or production integration evidence.

## 2. Current constraints

- The GitHub repository contains no Member 1 or Member 3 branches or pull requests.
- No therapist-labelled Tamil child recordings are available.
- No target Android tablet is available locally.
- The current adult-proxy model has a test phone-unit error rate of approximately 98.20 percent and is
  not suitable for pronunciation feedback.
- The current vocabulary is a Unicode code-point proxy rather than a Tamil-expert-approved phoneme
  inventory.
- The current INT8 Conv-BiGRU ONNX graph is CPU-compatible but unsuitable for NNAPI acceleration. The
  ONNX Runtime mobile checker reports fragmented support because of dynamic shapes, GRU, and integer
  quantization operators.

## 3. Scope

### 3.1 Test-only Member 1 adapter

Create a deterministic alignment adapter outside the production `vaakmitra` package. It will accept:

- the expected phoneme sequence;
- the acoustic output frame count and frame shift;
- mock confidence settings.

It will return the existing `AlignmentResult` contract using non-empty, half-open frame ranges. When
there are fewer frames than expected phonemes, the adapter will return an invalid neutral result rather
than fabricating overlapping segments.

Every result will be wrapped in evidence metadata containing:

- `dependency`: `member1`;
- `implementation`: `deterministic_mock`;
- `evidence_scope`: `mock_dependency_integration`;
- `production_eligible`: `false`;
- `clinical_validity`: `false`.

The adapter will not capture audio, perform VAD, implement production G2P, or claim forced-alignment
accuracy.

### 3.2 Test-only Member 3 adapter

Create a deterministic action adapter outside the production `vaakmitra` package. It will consume only
`AssessmentResult`, never audio or probability arrays. The initial mapping is:

| Assessment evidence | Mock response intent | Safety behavior |
|---|---|---|
| all usable units pass | `CELEBRATE_AND_CONTINUE` | continue within the mock plan |
| one or more usable units need coaching | `ENCOURAGE_TARGETED_PRACTICE` | identify only the lowest-scoring usable unit |
| assessment requests retry | `ENCOURAGE_NEUTRAL_RETRY` | do not describe pronunciation as wrong |
| assessment is unscorable | `REQUEST_NEUTRAL_RECAPTURE` | do not persist a negative result |
| assessment is an error | `PAUSE_AND_REPORT_TECHNICAL_ERROR` | no adaptive or clinical decision |

The output will include the same mock-only metadata as the Member 1 adapter, with `dependency` set to
`member3`. The adapter will not implement real persistence, sync, authentication, Unity integration,
or therapist policy.

### 3.3 Mocked end-to-end runner

Create a runner that executes:

1. validated synthetic in-memory audio;
2. Member 2 acoustic inference;
3. the Member 1 mock alignment adapter;
4. Member 2 GOP, confidence, and syllable aggregation;
5. the Member 3 mock action adapter;
6. a privacy-safe JSON evidence report.

The report must contain hashes and versions but no audio, embeddings, frame probabilities, transcript,
or direct identity. Its top-level evidence scope must be `mocked_three_member_pipeline`, and its release
status must remain `technical_prototype`.

### 3.4 Provisional Tamil inventory research tool

Add a research-only Tamil text-to-IPA inventory generator using Epitran's `tam-Taml` or
`tam-Taml-red` mapping behind an optional dependency boundary. The tool will:

- normalize Tamil Unicode input;
- transliterate a supplied, versioned word list;
- split IPA output into stable units while retaining length and combining marks;
- generate a vocabulary and pronunciation lexicon manifest;
- record the Epitran version, input hash, generation parameters, and output hash;
- set `expert_approved` and `therapist_approved` to `false`.

This tool is a provisional replacement for raw Unicode code-point labels during research. It is not a
production Member 1 G2P implementation and does not remove the Tamil-expert review requirement.

### 3.5 Tamil teacher and distillation preparation

Use AI4Bharat's Tamil IndicConformer as an optional offline teacher candidate. Because its native CTC
output is an ASR text vocabulary rather than the project's phoneme vocabulary, direct posterior
distillation is prohibited.

Instead, implement a versioned teacher-feature contract:

- source model identifier, revision, licence, and file hash;
- source-audio hash without storing an audio path in reports;
- frame shift, hidden dimension, tensor shape, and finite-value checks;
- feature-array hash and privacy classification;
- explicit `adult_tamil_teacher` evidence scope.

Teacher hidden representations may later supervise a compact student encoder while the student's CTC
head is trained against the provisional phoneme labels. Teacher feature caches remain ignored by Git
and are deleted or retained only under the documented local research policy.

The implementation in this phase will provide the manifest validator, cache writer/reader boundary,
configuration example, and a deterministic fixture. Downloading the gated model or claiming improved
accuracy is outside this phase.

### 3.6 Corpus-source preflight

Add validated source descriptors for IndicVoices and Vistaar. The preflight will record:

- canonical source URL and source organisation;
- language and configuration;
- licence and access requirements;
- adult-only or unknown target-age scope;
- transcript availability;
- whether streaming is supported;
- allowed evidence claims.

It will not silently accept access terms, download large archives, or mix speakers across evaluation
splits. IndicVoices must be marked adult-only because its published age brackets begin at 18.

### 3.7 Mobile readiness audit

Add a structured wrapper around the ONNX Runtime mobile usability checker. It will record:

- model hash and size;
- supported-node counts and partition counts where available;
- dynamic-shape warnings;
- unsupported operators;
- recommended execution provider;
- whether the result is a static compatibility audit or a real-device benchmark.

The current proxy model audit must recommend the CPU execution provider. An emulator may be used for
functional testing but will never satisfy physical-device performance acceptance. Firebase Test Lab is
the planned remote physical-device option once an Android application and credentials exist.

## 4. Architecture and ownership

Production Member 2 code remains under `backend/src/vaakmitra`. Mock dependencies and research tooling
remain under `modeling/` so the production package cannot import them accidentally.

Proposed additions:

```text
modeling/
  team_mocks/
    member1_alignment.py
    member3_actions.py
    run_mocked_pipeline.py
  inventory/
    tamil_ipa.py
    generate_inventory.py
  distillation/
    teacher_features.py
  data/
    source_preflight.py
  mobile/
    usability_audit.py
  configs/
    tamil_teacher.example.json
    tamil_research_sources.json
benchmarks/reports/
  member2-mocked-three-member-evidence.json
  proxy-int8-mobile-usability.json
```

The production assessment pipeline remains unchanged: Member 2 exposes acoustic probabilities, accepts
an `AlignmentResult`, and returns an `AssessmentResult`.

## 5. Error handling and safety

- Mock alignment returns neutral invalid results for impossible frame allocations.
- Unknown phonemes remain unscorable; mocks may not extend the production vocabulary silently.
- Unscorable and error results never become negative pronunciation feedback.
- Research source descriptors fail closed on missing licences, revisions, or age scope.
- Teacher feature readers reject hash mismatches, non-finite values, unexpected dimensions, or version
  mismatches.
- Mobile audits distinguish static graph analysis from real-device measurement.
- Logs and reports exclude audio, probability matrices, embeddings, transcripts, and personal data.

## 6. Testing strategy

All behavior changes will follow test-driven development.

Required tests include:

- deterministic and complete mock frame partitioning;
- impossible alignment returns an invalid neutral result;
- Member 3 mapping for pass, coach, retry, unscorable, and error;
- no prohibited voice-derived fields in mock evidence;
- complete mocked flow with explicit non-production labels;
- Tamil Unicode normalization and stable IPA-unit splitting;
- generated inventories remain unapproved by default;
- teacher-feature shape, hash, finite-value, and version validation;
- source preflight licence/access/age validation;
- structured parsing of representative ONNX mobile-checker output;
- regression coverage for the existing Member 2 pipeline.

The final verification gate will run pytest, Ruff, strict mypy, package build, CLI help, and
`git diff --check`.

## 7. Acceptance criteria for this implementation

This implementation is complete when:

1. The three-member interaction runs deterministically using explicit Member 1 and Member 3 mocks.
2. Mock outputs cannot be confused with production, therapist, or clinical evidence.
3. A provisional Epitran-based Tamil inventory can be generated reproducibly without entering the
   production Member 1 path.
4. Teacher-feature and corpus-source contracts are implemented and tested without downloading gated
   or bulk data automatically.
5. The current ONNX model has a reproducible structured mobile-usability report.
6. All existing and new automated checks pass.
7. Documentation states that model accuracy, therapist calibration, real forced alignment, child
   validity, and physical-device acceptance remain open gates.

## 8. Explicit non-goals

- Claiming that mocks replace Members 1 or 3.
- Shipping a production forced aligner, G2P service, adaptive engine, database, sync service, or Unity
  API under Member 2 ownership.
- Downloading or accepting gated model or dataset terms on the user's behalf.
- Claiming clinical validity or a target accuracy without therapist-labelled target-user evaluation.
- Treating laptop or emulator measurements as target-tablet evidence.

## 9. Later real-integration path

When teammate branches become available, each mock will be replaced at its existing contract boundary.
The integration audit will verify vocabulary/version agreement, frame timing, blank index, confidence
semantics, privacy fields, cancellation behavior, persistence allow-lists, and score-to-action rules.
Mock evidence will remain in the repository only as deterministic regression coverage.
