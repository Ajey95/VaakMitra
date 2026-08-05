# Alternative Model and Data Preparation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add reproducible provisional Tamil IPA inventory generation, licensed corpus-source preflight, and privacy-safe IndicConformer teacher-feature contracts without silently downloading gated assets.

**Architecture:** Research tooling remains under `modeling/`. Epitran is optional and injected behind a small transliterator protocol. Dataset descriptors and teacher-feature manifests use frozen Pydantic models, canonical SHA-256 digests, and fail-closed validation.

**Tech Stack:** Python 3.11, NumPy, Pydantic 2, optional Epitran, pytest.

## Global Constraints

- No gated model or dataset download and no acceptance of terms on behalf of the user.
- IndicVoices is adult-only evidence because published participant brackets begin at 18.
- Provisional inventories always set `expert_approved=false` and `therapist_approved=false`.
- Direct posterior distillation from the IndicConformer ASR vocabulary to the phoneme vocabulary is prohibited.
- Teacher feature caches and source audio remain outside Git.
- All code changes use red-green-refactor.

---

### Task 1: Provisional Tamil IPA inventory generator

**Files:**
- Create: `modeling/inventory/__init__.py`
- Create: `modeling/inventory/tamil_ipa.py`
- Create: `modeling/inventory/generate_inventory.py`
- Test: `backend/tests/unit/test_tamil_ipa_inventory.py`

**Interfaces:**
- Consumes: `Transliterator.transliterate(text: str) -> str` and `generate_inventory(words, transliterator, version) -> InventoryManifest`.
- Produces: normalized lexicon entries, ordered IPA units, provenance hashes, and approval flags.

- [ ] **Step 1: Write failing normalization and IPA-unit tests**

```python
def test_split_ipa_units_retains_length_and_combining_marks() -> None:
    assert split_ipa_units("aːm") == ("aː", "m")
    assert split_ipa_units("n̪a") == ("n̪", "a")


def test_generated_inventory_is_reproducible_and_unapproved() -> None:
    manifest = generate_inventory(("அம்மா",), FakeTransliterator({"அம்மா": "ammaː"}), "ta-ipa-proxy-1")
    assert manifest.expert_approved is False
    assert manifest.therapist_approved is False
    assert manifest.lexicon[0].ipa == "ammaː"
    assert manifest.digest() == generate_inventory(
        ("அம்மா",), FakeTransliterator({"அம்மா": "ammaː"}), "ta-ipa-proxy-1"
    ).digest()
```

- [ ] **Step 2: Run tests and confirm missing-module failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_tamil_ipa_inventory.py -q`

- [ ] **Step 3: Implement Unicode normalization, stable unit splitting, manifests, and optional Epitran adapter**

Use NFC normalization. Attach Unicode combining marks, IPA length marks `ː`/`ˑ`, and tie-bar continuations to the preceding base unit. Reject empty Tamil words, empty transliterations, duplicate normalized words, and blank-token collisions. Import Epitran only inside `EpitranTamilTransliterator.__init__` and raise `RuntimeError("epitran optional dependency is not installed")` on import failure.

- [ ] **Step 4: Run focused tests and CLI help**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_tamil_ipa_inventory.py -q`

Run: `.\.venv\Scripts\python.exe -m modeling.inventory.generate_inventory --help`

- [ ] **Step 5: Commit the inventory tooling**

```powershell
git add -- modeling/inventory backend/tests/unit/test_tamil_ipa_inventory.py
git commit -m "feat: add provisional Tamil IPA inventory tooling"
```

### Task 2: Licensed source preflight

**Files:**
- Create: `modeling/data/source_preflight.py`
- Create: `modeling/configs/tamil_research_sources.json`
- Test: `backend/tests/unit/test_source_preflight.py`

**Interfaces:**
- Consumes: `ResearchSource` JSON records.
- Produces: `SourcePreflightReport` with allowed claims and a canonical digest.

- [ ] **Step 1: Write failing tests for access, licence, and age-scope validation**

```python
def test_indicvoices_is_rejected_if_claimed_as_child_evidence() -> None:
    source = valid_indicvoices_source(target_age_scope="child")
    with pytest.raises(ValidationError, match="adult_only"):
        ResearchSource.model_validate(source)


def test_preflight_never_authorizes_silent_download() -> None:
    report = preflight_sources((ResearchSource.model_validate(valid_indicvoices_source()),))
    assert report.sources[0].requires_user_terms_acceptance is True
    assert report.sources[0].automatic_download_allowed is False
```

- [ ] **Step 2: Run tests and confirm missing-module failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_source_preflight.py -q`

- [ ] **Step 3: Implement frozen source descriptors and preflight report**

Define exact fields: `source_id`, `organization`, `canonical_url`, `language`, `license_spdx`, `revision`, `target_age_scope`, `transcript_scope`, `streaming_supported`, `requires_user_terms_acceptance`, `automatic_download_allowed`, and `allowed_evidence_claims`. Require HTTPS, immutable revisions, approved licences, non-empty allowed claims, and `automatic_download_allowed=false` whenever terms acceptance is required.

- [ ] **Step 4: Add reviewed IndicVoices and Vistaar descriptors**

Set IndicVoices to `target_age_scope="adult_only"`, `license_spdx="CC-BY-4.0"`, gated access, streaming support, and engineering-proxy claims only. Set Vistaar to adult/unspecified target age, MIT model-code licence while recording dataset-specific licence review as required before materialization.

- [ ] **Step 5: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_source_preflight.py -q`

- [ ] **Step 6: Commit source preflight**

```powershell
git add -- modeling/data/source_preflight.py modeling/configs/tamil_research_sources.json backend/tests/unit/test_source_preflight.py
git commit -m "feat: validate Tamil research data sources"
```

### Task 3: IndicConformer teacher-feature contract

**Files:**
- Create: `modeling/distillation/__init__.py`
- Create: `modeling/distillation/teacher_features.py`
- Create: `modeling/configs/tamil_teacher.example.json`
- Test: `backend/tests/unit/test_teacher_features.py`

**Interfaces:**
- Consumes: finite `np.ndarray[float32]` features plus `TeacherFeatureManifest`.
- Produces: `write_teacher_feature_cache(...)` and `read_teacher_feature_cache(...)` with hash validation.

- [ ] **Step 1: Write failing round-trip and tamper tests**

```python
def test_teacher_feature_cache_round_trips_with_hash_validation(tmp_path: Path) -> None:
    features = np.arange(12, dtype=np.float32).reshape(3, 4)
    written = write_teacher_feature_cache(tmp_path / "teacher.npz", features, fixture_manifest())
    loaded, manifest = read_teacher_feature_cache(written.path)
    np.testing.assert_array_equal(loaded, features)
    assert manifest.evidence_scope == "adult_tamil_teacher"


def test_teacher_feature_cache_rejects_non_finite_values(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="finite"):
        write_teacher_feature_cache(
            tmp_path / "teacher.npz", np.array([[np.nan]], dtype=np.float32), fixture_manifest()
        )
```

- [ ] **Step 2: Run tests and confirm missing-module failure**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_teacher_features.py -q`

- [ ] **Step 3: Implement manifest and cache validation**

Require the model identifier `ai4bharat/indicconformer_stt_ta_hybrid_ctc_rnnt_large`, an immutable model revision, MIT licence, 16 kHz source rate, positive frame shift and hidden dimension, a 64-character audio SHA-256, `privacy_classification="voice_derived_local_only"`, and `evidence_scope="adult_tamil_teacher"`. Store features and canonical manifest JSON in a compressed NPZ without audio paths.

- [ ] **Step 4: Add the example teacher configuration**

Record the gated-access requirement, hidden-feature strategy, phoneme-head incompatibility, and `direct_posterior_distillation_allowed=false`.

- [ ] **Step 5: Run focused tests**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_teacher_features.py -q`

- [ ] **Step 6: Commit teacher-feature contracts**

```powershell
git add -- modeling/distillation modeling/configs/tamil_teacher.example.json backend/tests/unit/test_teacher_features.py
git commit -m "feat: add Tamil teacher feature contracts"
```

### Task 4: Alternative-strategy documentation and regression gate

**Files:**
- Modify: `modeling/training/README.md`
- Modify: `modeling/model_cards/ta-phoneme-ctc-baseline.md`

**Interfaces:**
- Consumes: outputs from Tasks 1-3.
- Produces: reproducible operator instructions and explicit limitations.

- [ ] **Step 1: Document the staged training strategy**

Describe: generate a provisional IPA inventory, materialize a speaker-disjoint adult Tamil corpus only after licence/access approval, extract IndicConformer hidden features locally, train a compact student encoder with feature supervision plus phoneme CTC, then evaluate before any child test.

- [ ] **Step 2: Document the safety and evidence boundaries**

State that adult data cannot establish child/ASD validity, Epitran is not expert approval, teacher features are voice-derived and local-only, and accuracy remains unproven until a new benchmark is run.

- [ ] **Step 3: Run the alternative-strategy test set**

Run: `.\.venv\Scripts\python.exe -m pytest backend/tests/unit/test_tamil_ipa_inventory.py backend/tests/unit/test_source_preflight.py backend/tests/unit/test_teacher_features.py -q`

- [ ] **Step 4: Commit the documentation**

```powershell
git add -- modeling/training/README.md modeling/model_cards/ta-phoneme-ctc-baseline.md
git commit -m "docs: describe Tamil teacher distillation path"
```
