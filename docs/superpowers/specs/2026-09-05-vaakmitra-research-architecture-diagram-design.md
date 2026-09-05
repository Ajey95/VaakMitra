# VaakMitra Research Architecture Diagram Design

## Purpose

Create one editable diagrams.net (`.drawio`) document that communicates the complete VaakMitra research architecture at block and layer level. The document must be suitable for an academic guide review, clearly separate research evidence from deployable behavior, and preserve the project's offline-first privacy constraints.

The diagram is an architectural communication artifact. It must not imply that pending model training, clinician approval, child-domain validation, teammate integration, or physical-device benchmarking has already been completed.

## Deliverable

- File: `docs/architecture/VaakMitra_Academic_Research_Architecture.drawio`
- Format: uncompressed diagrams.net XML so that source control diffs and manual editing remain practical.
- Pages: three coordinated pages with consistent typography, colors, identifiers, and legend semantics.
- Motion: primary data-flow edges use diagrams.net animated-flow styling (`flowAnimation=1`) with visible dash patterns. Control, feedback, governance, and prohibited-flow edges remain visually distinct.
- Compatibility: the file must open as editable content in diagrams.net without requiring external image downloads.

## Visual System

The design uses an academic blue-and-teal palette on a white background. Each page includes a title, research-scope subtitle, numbered layers, trust-zone containers, component identifiers, and a compact legend.

Recognizable icons are embedded or expressed with diagrams.net-supported vector shapes at the point where they add semantic value:

- child participant and therapist;
- microphone and audio waveform;
- Android/mobile edge device;
- Unity presentation layer;
- Python/PyTorch research environment;
- AI4Bharat/IndicConformer teacher model as a labelled research model block;
- ONNX Runtime edge inference;
- dataset/corpus and model registry;
- encrypted local database;
- consent-controlled cloud/API boundary;
- shield, lock, audit, and validation gates.

Icons support the labels rather than replace them. Every technical block retains a text name, responsibility, and principal input/output.

## Page 1: Layered End-to-End System Architecture

This page presents the complete operational loop in six horizontal layers.

1. **Human and interaction layer**
   - Child participant
   - Therapist or caregiver
   - Unity-based Tamil therapy interface
   - Visual/avatar feedback and Tamil TTS

2. **Session and edge orchestration layer (Member 3)**
   - Session state machine
   - Exercise retrieval and retry limits
   - Deterministic adaptive policy
   - Response intent: `PASS`, `COACH`, `RETRY`, or `UNSCORABLE`

3. **Audio and linguistic preparation layer (Member 1)**
   - Local microphone capture
   - 16 kHz mono validation
   - VAD and quality checks
   - Tamil normalization, G2P, phoneme inventory, and syllabification

4. **Speech intelligence and alignment layer (Members 1 and 2)**
   - Local Tamil acoustic encoder
   - Phoneme-level CTC log probabilities
   - CTC forced alignment and timestamp confidence
   - GOP, competitor evidence, confidence calibration, and syllable aggregation

5. **Local persistence and runtime layer (Member 3)**
   - ONNX Runtime/mobile execution
   - Signed/hash-verified model package
   - Encrypted pseudonymous session metrics
   - Audit log and consent state
   - Explicit raw-audio/intermediate deletion boundary

6. **Optional consent-controlled service layer**
   - Allow-listed metric sync only
   - Therapist API and progress dashboard
   - Exercise/configuration download
   - No raw audio, transcript, embedding, spectrogram, MFCC, voiceprint, or frame-level probability upload

The primary animated loop runs from exercise selection through capture, acoustic inference, alignment, scoring, adaptive response, and Unity feedback. A secondary animated path shows minimum approved metrics entering the local sync queue and crossing the network only after consent and schema enforcement.

## Page 2: Research, Training, and Model-Lifecycle Pipeline

This page separates offline research/training from runtime deployment.

1. **Governed research inputs**
   - Public Tamil speech corpus with immutable source revision and licensing evidence
   - Therapist-reviewed Tamil phoneme inventory
   - Adult-domain versus child-domain labels
   - Dataset provenance and exclusion ledger

2. **Data engineering and experimental controls**
   - Audio validation and normalization
   - Speaker-disjoint train/validation/test split
   - Leakage checks and frozen indices
   - Feature preparation and reproducible manifests

3. **Teacher adaptation**
   - AI4Bharat Tamil IndicConformer acoustic encoder
   - New provisional Tamil phoneme CTC head
   - Staged head/top-block/full-encoder training
   - Text-token and phoneme-posterior representations explicitly marked non-interchangeable

4. **Compact student distillation**
   - Compact Conformer candidate
   - Compact Conv-BiGRU candidate
   - Supervised phoneme CTC loss
   - Hidden-representation and relational distillation losses
   - Checkpointing and experiment metadata

5. **Evaluation and acceptance gates**
   - Phone-unit error rate and exact sequence accuracy
   - Speaker-disjoint evaluation
   - Alignment/GOP calibration when validated alignments become available
   - FP32 versus INT8 degradation
   - Latency, memory, package size, cold start, and P95 device timing
   - Robustness, privacy, and failure-mode tests

6. **Deployment packaging**
   - Model card and immutable manifest
   - FP32 ONNX candidate
   - INT8 ONNX candidate
   - Hash/signature verification
   - Controlled promotion into the edge application

Animated flows distinguish corpus data, model/gradient flow, distilled knowledge, evaluation evidence, and approved deployment promotion. Feedback arrows return failed gates to the relevant experimental stage.

## Page 3: Validation, Governance, Privacy, and Evidence Boundaries

This page presents research credibility and safety as first-class architecture.

1. **Research question and hypotheses**
   - Whether Tamil acoustic representations can support phoneme-level pronunciation evidence on an offline edge device
   - Whether compact distilled models preserve acceptable phoneme and GOP behavior under mobile constraints

2. **Evidence ladder**
   - Unit and contract evidence
   - Synthetic pipeline evidence
   - Real adult-Tamil corpus evidence
   - Speaker-disjoint model evidence
   - Member 1 forced-alignment evidence
   - Clinician/linguist review
   - Child-domain validation
   - Physical Android benchmark

3. **Deterministic safety controls**
   - Confidence and alignment gates
   - Neutral `UNSCORABLE` result for insufficient evidence
   - Retry and fatigue limits
   - Therapist-approved action policy
   - Model output cannot create an unrestricted clinical decision

4. **Privacy and security boundary**
   - Local raw audio and voice-derived intermediates
   - Immediate/controlled deletion lifecycle
   - Encrypted pseudonymous metrics
   - Consent, authentication, TLS, allow-list, idempotency, and audit controls
   - Red prohibited-flow arrows for disallowed network payloads

5. **Current-status truth boundary**
   - Implemented engineering prototype blocks
   - Research runs or integrations still pending
   - Explicit statement that synthetic fixtures prove mechanics, not clinical accuracy

## Edge Semantics

- Animated blue dashed edge: primary local data flow.
- Animated teal dashed edge: model/research artifact flow.
- Solid purple edge: control or configuration.
- Dashed amber return edge: evaluation feedback or retraining loop.
- Solid green edge: approved minimum-metric synchronization.
- Red edge with stop marker: prohibited privacy flow.
- Grey dotted edge: planned or evidence-pending dependency.

Animation must reinforce direction without being necessary for comprehension. Arrowheads, labels, sequence numbers, and the legend preserve meaning in static exports.

## Academic Integrity and Status Labels

The file must visibly mark these limitations:

- The historical tiny Conv-BiGRU proxy achieved approximately 98.2% phone-unit error and is rejected for accuracy.
- The AI4Bharat IndicConformer is a teacher/baseline candidate; its released text-token output is not the required phoneme posterior.
- The Tamil phoneme inventory is provisional until expert approval.
- Final GPU training, validated Member 1 alignment, child-domain assessment, clinician calibration, and physical-device evidence remain research gates unless newer evidence supersedes the checked documents.
- The architecture is a research prototype and not an autonomous diagnostic or clinical decision system.

## Verification

Before delivery:

1. Parse the XML and confirm three diagram pages exist.
2. Confirm all component identifiers are unique.
3. Confirm each page has a title, subtitle, legend, and status boundary.
4. Confirm primary paths contain `flowAnimation=1` and explicit arrowheads.
5. Confirm icons are embedded or supported without remote network dependencies.
6. Confirm the document can be opened by diagrams.net as editable geometry.
7. Render or inspect each page and check for overlaps, clipped text, crossing ambiguity, and illegible labels.
8. Scan all labels for unsupported claims and contradictions with the repository architecture.

