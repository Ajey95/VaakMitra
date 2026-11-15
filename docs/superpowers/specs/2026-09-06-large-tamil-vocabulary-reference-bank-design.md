# Large Tamil Vocabulary and Adult Reference Bank Design

**Status:** Approved for implementation on 2026-09-06
**Authority:** `VAAKMITRA_FINAL_SSOT.md` v3.1.0 remains normative
**Scope:** DEC-003, DEC-007, DEC-015..017, CLS-001..005, DTW-001..007, FUS-001..007, DATA-001..012

## Outcome

VaakMitra will not be limited to the six lessons inherited from the frontend. It will use a dynamic, versioned registry with 100 intended V1 Tamil whole-word targets, a 250–500 word candidate layer, 32–64 quality-controlled adult references per active word, and at least 10,000 adult `OTHER`/confusable examples.

The system assesses the complete attempted word. It does not grade phonemes, syllables, articulation locations, or letter sounds. Existing single-letter lessons may remain as guided teaching activities, but the scoring API must not pretend that a letter exercise is a word class.

Target-child validation is deliberately excluded from this implementation phase. Consequently, an adult-data engineering bundle may be complete and reproducible while `approved=false`, `scoring_ready=false`, and the product remains labelled **technical prototype — scoring not clinically validated**.

## Why the original six are not the boundary

The six entries were implementation constants in `therapy.py` and `vaakmitra_word/router.py`; they were not a limit of Tamil IndicConformer. Hardcoding them couples UI navigation, curriculum, classifier labels, and release artifacts. The new registry separates:

1. candidate vocabulary that may be curated;
2. intended V1 vocabulary;
3. active bundle vocabulary that has passed data and review gates;
4. frontend teaching content, which may include non-scored letters.

## What breaks first

The first scaling failure is false acceptance, not disk or GPU capacity. If runtime DTW compares an attempt against hundreds of recordings and accepts the single closest result, the chance of an accidental close match rises with bank size. Near-duplicates and overrepresented speakers further distort the score.

The bank therefore uses bounded, balanced coverage and aggregates the three best matches from distinct speakers. The aggregation output is a calibration feature; it is never a hand-written PASS threshold. Per-speaker caps, exact/near-duplicate rejection, split isolation, and held-out negative evaluation are mandatory.

## Approaches considered

### A. Balanced large bank — selected

- 32–64 accepted adult references per active word.
- At least eight speakers per word and at most four references from one speaker.
- Best-three distinct-speaker aggregate at inference.
- Balanced class weights and a large `OTHER`/confusable pool.
- Words activate independently only after all gates pass.

This gives substantial acoustic coverage without allowing unlimited best-of-many matching.

### B. Maximum-size bank

Hundreds or thousands of references per word maximize diversity but increase latency, duplicate risk, and multiple-comparison false acceptance. It is rejected for V1 unless an indexed matcher and child-separated recalibration later demonstrate a safer operating point.

### C. Therapist-only compact bank

Four to eight recordings per word are simple to review but do not meet the requested diversity and are vulnerable to speaker/microphone mismatch. Such recordings remain valuable as human-reviewed canaries and provenance anchors, not as the whole bank.

## Vocabulary architecture

Every vocabulary release is immutable and contains:

- `schema_version` and `vocabulary_version`;
- stable `word_id` values unrelated to list position;
- canonical NFC Tamil text;
- English gloss and semantic category;
- aliases used only for corpus matching, never as canonical scoring labels;
- state: `candidate`, `intended`, `active`, or `disabled`;
- minimum evidence requirements and human-review status;
- source and reviewer metadata without child identity.

The frontend retrieves active teaching/scoring metadata from the authenticated backend. It must tolerate an inactive word and show a neutral unavailable state rather than infer or substitute another word.

## Intended V1 vocabulary (100 words)

This is the engineering registry. Clinical use still requires therapist review under GATE-06.

| Category | Canonical Tamil words |
|---|---|
| Family and people (10) | அம்மா, அப்பா, அக்கா, அண்ணா, தம்பி, தங்கை, பாட்டி, தாத்தா, ஆசிரியர், நண்பர் |
| Needs and self-advocacy (15) | தண்ணீர், உணவு, வேண்டும், வேண்டாம், இன்னும், போதும், உதவி, ஓய்வு, கழிப்பறை, வலி, பசி, தாகம், சூடு, குளிர், தூக்கம் |
| Food and drink (15) | பால், சோறு, இட்லி, தோசை, பழம், ஆப்பிள், வாழை, மாம்பழம், காய்கறி, முட்டை, ரொட்டி, சாறு, தயிர், பிஸ்கட், தேநீர் |
| Actions (20) | வா, போ, உட்கார், நில், கொடு, எடு, பார், கேள், சொல், படி, எழுது, விளையாடு, சாப்பிடு, குடி, திற, மூடு, காத்திரு, நிறுத்து, தொடங்கு, தூங்கு |
| Objects and places (15) | வீடு, பள்ளி, அறை, கதவு, ஜன்னல், நாற்காலி, மேசை, புத்தகம், பேனா, பந்து, பொம்மை, படம், கைபேசி, பேருந்து, பூங்கா |
| Feelings, body, and safety (15) | மகிழ்ச்சி, சோகம், கோபம், பயம், அமைதி, நல்லது, இல்லை, ஆம், கை, கால், தலை, வாய், கண், காது, பாதுகாப்பு |
| Social and session language (10) | வணக்கம், நன்றி, தயவு, மன்னிக்கவும், சரி, மீண்டும், மெதுவாக, இங்கே, அங்கே, சேர்ந்து |

The registry may retain additional dialectal or inflected aliases for corpus discovery. An alias must never merge semantically different targets.

## Corpus tiers

### Tier 1 — reference candidates

Adult human recordings whose isolated or reliably segmented transcript equals one canonical target or an approved alias. These may become reference embeddings only after provenance, quality, deduplication, speaker-balance, split, and human-review checks.

### Tier 2 — classifier positives

Adult target-word recordings and approved augmentations used to train the pooled-embedding classifier. Augmented children-like audio remains labelled synthetic and cannot enter reference or held-out truth sets.

### Tier 3 — `OTHER` and confusables

At least 10,000 adult recordings consisting of:

- acoustically or lexically confusable Tamil words;
- non-target isolated words;
- short Tamil phrases and sentences;
- partial/cut utterances;
- silence, room noise, and background adult speech for quality/challenge tests.

Silence/noise trains rejection and validates capture gates; it is not treated as a spoken `OTHER` word when reporting linguistic confusion.

### Tier 4 — held-out engineering evaluation

Speaker-disjoint adult positives, wrong words, confusables, noise, and therapist recordings. No item used to select references or train the classifier may enter this tier.

### Tier 5 — child validation (not implemented now)

The provided child recordings are preserved and inventoried but excluded from training, reference construction, threshold selection, canary approval, and current accuracy claims. They may be used only in a separately approved child-validation protocol.

## Acquisition and provenance

Acquisition supports manifest-driven adapters rather than ad hoc downloads. Candidate public sources include isolated-word Tamil corpora, transcribed Tamil speech corpora that permit reliable word segmentation, and owned therapist recordings. Each source adapter must record and verify its current licence and redistribution conditions at acquisition time; an unknown or incompatible licence blocks ingestion.

Raw external audio lives outside Git in a configurable build cache. The repository contains manifests, checksums, scripts, tests, and reports—not redistributed audio unless its licence and release decision explicitly allow it. The runtime bundle contains embeddings and metadata only.

Network interruptions are resumable. Source revision, URL or Hub identifier, original sample ID, checksum, byte size, and extraction result are recorded before preprocessing.

## Quality and balancing gates

An accepted reference must satisfy all of the following:

- decodes to finite mono audio and is resampled to 16 kHz;
- contains detected speech and passes duration, clipping, and signal-level bounds;
- transcript maps unambiguously to the canonical target;
- speaker identity/pseudonym is available for balancing;
- exact audio hash and acoustic near-duplicate checks pass;
- source and redistribution provenance are known;
- it belongs only to the reference-selection split;
- human review status is explicit.

Selection is deterministic from a seed. It maximizes speaker, source, microphone, sex/voice-range where lawfully available, and duration diversity without inferring protected attributes from voice.

## Classifier design

The V1 classifier remains a lightweight linear head over frozen IndicConformer representations. Training adds masked mean, standard deviation, and attentive/statistical pooling behind a versioned feature schema. The output vocabulary is the active word set plus `OTHER`.

Training uses speaker-disjoint train/calibration/evaluation splits, class balancing, deterministic seeds, and explicit data manifests. Class probability calibration on adult data is an engineering calibration only. The classifier exports weights, bias, pooling schema, label order, model hash, vocabulary hash, dataset-manifest hash, training code commit, and metrics.

## Reference-bank design

Each stored reference includes its embedding, stable reference ID, canonical word ID, pseudonymous speaker ID, source ID, source-sample hash, quality summary, and approval state. Raw audio is not shipped.

At runtime:

1. reject model/vocabulary/hash mismatch;
2. compute cosine DTW against accepted references for the target word;
3. retain the best distance per speaker;
4. aggregate the best three distinct-speaker distances using a versioned statistic;
5. expose the aggregate and coverage metadata to fusion;
6. never convert it directly into PASS.

## Calibration and thresholds

Two artifacts are deliberately distinguished:

- **Adult engineering calibration:** reproducible coefficients and thresholds used for offline evaluation, marked `approved=false`; it cannot make runtime scoring ready.
- **Child-separated clinical calibration:** future therapist-labelled artifact satisfying GATE-03; only this may be `approved=true`.

The adult calibrator reports false PASS, false RETRY, abstention coverage, ECE, Brier score, AUROC/AUPRC, word confusion, and bootstrap confidence intervals on held-out adults. It is useful for pipeline verification but never substitutes for target-child evidence.

## Canary policy

Canaries are fixed, hash-pinned, consented adult/therapist recordings held out from training and reference selection. A release set contains at least:

- one positive canary for every active word;
- wrong-word and confusable canaries across every semantic category;
- silence, noise, clipped, unsupported, and overlong negative canaries;
- expected evidence availability and decision constraints.

Automated checks can mark a canary technically accepted. `approved` in the clinical release sense still requires the named human reviewer and, for scoring, an approved child-separated calibrator. The current therapist files can become candidates after the owner maps filenames/segments to exact canonical words and confirms consent/use.

## Bundle and release state

The immutable engineering bundle cross-hashes the acoustic model, vocabulary, classifier, reference bank, adult calibrator, dataset manifest, canary manifest, code commit, and reports. Bundle construction fails on unsupported vocabulary coverage, provenance gaps, split leakage, or hash mismatch.

Until child validation exists:

- bundle status: `engineering_complete` when all adult gates pass;
- calibration `approved=false`;
- `scoring_ready=false`;
- API scoring remains fail-closed;
- no clinical accuracy or production-readiness claim is allowed.

## Implementation order

1. Add vocabulary/corpus schemas and the 100-word registry.
2. Replace hardcoded scoring maps with the registry while preserving teaching-only letter lessons.
3. Add resumable corpus adapters, provenance manifests, and licence gates.
4. Add deterministic preprocessing, segmentation import, quality checks, and deduplication.
5. Extract IndicConformer embeddings on the RTX 4060.
6. Select the balanced reference bank and implement distinct-speaker DTW aggregation.
7. Train/export the closed-vocabulary classifier with `OTHER`.
8. Fit/export adult-only engineering calibration and threshold reports.
9. Build hash-pinned adult/therapist canaries and run them.
10. Create and verify the immutable engineering bundle.
11. Dynamically expose active vocabulary to the frontend.
12. Keep child validation and clinical approval visibly pending.

## Acceptance boundary

This phase is complete only when the scripts can reproduce the manifests and artifacts from declared adult sources, the 100-word registry is dynamic, every activated word meets its reference quota, `OTHER` contains at least 10,000 accepted examples, adult evaluations and canaries pass their predeclared engineering gates, the bundle verifies immutably, and all tests/builds pass.

It is not complete merely because a model file loads, a few recordings produce embeddings, or a synthetic test returns PASS. Child validation remains the one explicitly excluded evidence stream.
