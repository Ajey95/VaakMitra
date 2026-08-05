# Adult-Tamil proxy CTC training

The checked-in training path is a bounded technical experiment, not the production child-speech
model. It trains a small raw-waveform Conv-BiGRU CTC network on a speaker-disjoint subset of the
CC0 Tamil TTS corpus and exports dynamic-sample ONNX logits.

The target units are normalized Unicode IPA code points. They are intentionally labelled
`unicode_codepoint_proxy_not_expert_phoneme_inventory`; they are not a Tamil-expert-reviewed
phoneme inventory and must not be connected to child feedback as an approved scorer.

For the next inventory iteration, `modeling.inventory.generate_inventory` can use Epitran to create
a deterministic provisional Tamil IPA/token manifest from an approved UTF-8 word list. Its output
always records `expert_approved=false` and `production_ready=false`; a speech-language/Tamil expert
must still decide the final phoneme, vowel-length, gemination, and normalization conventions.

Install the matched CPU framework versions:

```powershell
& .\.venv\Scripts\python.exe -m pip install `
  --requirement modeling\training\requirements-cpu.txt
```

Prepare metadata-only speaker-disjoint indices and materialize a bounded local subset:

```powershell
$env:GIT_LFS_SKIP_SMUDGE = "1"
git clone https://huggingface.co/datasets/asishbala/tamil-tts-dataset.git `
  modeling\artifacts\datasets\tamil-tts-source
Remove-Item Env:GIT_LFS_SKIP_SMUDGE

& .\.venv\Scripts\python.exe -m modeling.data.prepare_tamil_tts_proxy `
  --source-dir modeling\artifacts\datasets\tamil-tts-source `
  --output-dir modeling\artifacts\datasets\tamil-tts-prepared `
  --revision 1d6a78e02c6c21d8da30eb57dd4dc02b4ed765f5

& modeling\data\materialize_proxy_subset.ps1 `
  -PreparedDir modeling\artifacts\datasets\tamil-tts-prepared `
  -Destination modeling\artifacts\datasets\tamil-tts-audio
```

Train and export the bounded proxy model:

```powershell
& .\.venv\Scripts\python.exe -m modeling.training.train_proxy_ctc `
  --prepared-dir modeling\artifacts\datasets\tamil-tts-prepared `
  --audio-root modeling\artifacts\datasets\tamil-tts-audio `
  --corpus-manifest modeling\artifacts\datasets\tamil-tts-prepared\corpus.manifest.json `
  --output-dir modeling\artifacts\proxy-trained-v1 `
  --report benchmarks\reports\proxy-training-adult-tamil.json `
  --epochs 2 --batch-size 4 --channels 16 --hidden-size 24 `
  --max-train-records-per-speaker 3 --max-eval-records-per-speaker 2
```

The recorded run used 42/8/8 utterances across 14/4/4 disjoint speakers. Its test phone-unit error
rate is 0.98198, so it proves the reproducible training/export path but is unsuitable for
pronunciation scoring. A production model still requires a reviewed inventory, substantially more
training, child-domain evaluation, therapist calibration, and target-device validation.

## Additional research-only inputs

`modeling/configs/tamil_research_sources.json` records pinned IndicVoices, Vistaar, and
IISc-MILE/OpenSLR 127 preflight metadata. It deliberately disables automatic download for gated,
large, or dataset-licence-review sources. Adult-only sources may support engineering proxy
experiments only, never child or clinical claims.

`modeling/configs/indicconformer_teacher.json` pins the Tamil IndicConformer candidate. The
`modeling.distillation.teacher_features` package can package already-extracted adult Tamil teacher
features locally with immutable provenance and tamper detection. It does not fetch the gated model,
retain raw audio, or reinterpret the ASR vocabulary as direct phoneme posteriors.

## Dual-track strengthening workflow

Both strategies share one provisional inventory, corpus, split, metric, robustness, and promotion
contract. Member 1 remains the owner of the production pronunciation dictionary and forced
alignment.

### 1. Candidate Tamil inventory

`tamil_phoneme_sources.json` pins PHOIBLE Tamil inventories 1058, 1788, and 2611 plus the upstream
Epitran revision. Generate a word-list inventory and merge it with the published sources:

```powershell
& .\.venv\Scripts\python.exe -m modeling.inventory.generate_inventory `
  --words modeling\artifacts\exercise-words.txt `
  --output modeling\artifacts\tamil-phoneme-contract.json `
  --version ta-candidate-1 `
  --consensus-sources modeling\configs\tamil_phoneme_sources.json `
  --transliterator-revision 3ed96fd7d10f6f5eec75ba1deb10700fcaafe43f
```

The output records core/extended units, per-phone provenance, disagreements, unknown coverage,
and explicit allophone mappings. It remains `expert_approved=false` and
`production_ready=false`.

### 2. IISc-MILE corpus freeze

OpenSLR 127 is recorded as an adult Tamil, CC-BY-2.0 source. The 13 GB archive is not silently
downloaded. After acquiring it locally, compute its SHA-256, generate private JSONL records with
only utterance/speaker identifiers and audio/transcript digests, and freeze aggregate split
evidence:

```powershell
& .\.venv\Scripts\python.exe -m modeling.data.build_corpus_index `
  --records modeling\artifacts\iisc-mile\records.jsonl `
  --assignments modeling\artifacts\iisc-mile\speaker-splits.json `
  --source modeling\artifacts\iisc-mile\verified-source.json `
  --output modeling\artifacts\iisc-mile\frozen-corpus-index.json
```

The source file must use `revision_basis="archive_sha256"`. Speaker, utterance, or audio-digest
overlap fails before training. The aggregate output contains no path, transcript, utterance ID, or
speaker ID.

### 3. Strategy 2: full reference

```powershell
# Works on this CPU host and does not load the gated model.
& .\.venv\Scripts\python.exe -m modeling.teacher.run_preflight `
  --config modeling\configs\indicconformer_teacher.json --mode cpu_smoke

# This remains blocked until access, NeMo, and CUDA genuinely exist.
& .\.venv\Scripts\python.exe -m modeling.teacher.run_preflight `
  --config modeling\configs\indicconformer_teacher.json --mode full_train `
  --access-authorized

& .\.venv\Scripts\python.exe -m modeling.training.smoke_full_track `
  --seed 17 --steps 3 --output benchmarks\reports\full-track-cpu-smoke.json
```

The implementation attaches a new phoneme CTC head, supports head-only, trailing-block, and
full-encoder stages, and advances to full unfreezing only after a predeclared validation-PER
improvement. Actual IndicConformer fine-tuning remains the GPU-dependent implementation item.

### 4. Strategy 1: distilled edge students

```powershell
& .\.venv\Scripts\python.exe -m modeling.training.smoke_student_track `
  --seed 23 --steps 1 --output benchmarks\reports\student-track-cpu-smoke.json
```

The compact Conformer and Conv-BiGRU return phoneme logits plus pre-head representations. Training
combines supervised phoneme CTC, masked teacher representation loss, relational frame similarity,
and optional sequence consistency. Text-posterior KL is absent from the accepted configuration.
Both candidates export with dynamic audio axes and execute as FP32 and dynamic INT8 ONNX models.

### 5. Calibration, robustness, and device evidence

Controlled target corruptions cover substitution, short/long vowels, gemination, insertion,
deletion, and transposition. Proxy calibration reports FAR, FRR, AUROC, Brier, ECE, bootstrap
intervals, and phone/class thresholds. `robustness_matrix.json` adds deterministic transformation
stress only; it never claims child-domain measurement.

Physical or emulator Android JSON is reduced with:

```powershell
& .\.venv\Scripts\python.exe -m modeling.mobile.parse_device_report `
  --input modeling\artifacts\android\raw-benchmark.json `
  --expected-model-sha256 <64-lowercase-hex> `
  --output benchmarks\reports\android-device-benchmark.json
```

Only a physical report with at least 30 runs, offline/network-denial evidence, a matching model
hash, and P95 at or below 500 ms can pass the device gate.
