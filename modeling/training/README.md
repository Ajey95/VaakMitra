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

`modeling/configs/tamil_research_sources.json` records pinned IndicVoices and Vistaar preflight
metadata. It deliberately disables automatic download for terms-gated or dataset-licence-review
sources. Adult-only sources may support engineering proxy experiments only, never child or clinical
claims.

`modeling/configs/indicconformer_teacher.json` pins the Tamil IndicConformer candidate. The
`modeling.distillation.teacher_features` package can package already-extracted adult Tamil teacher
features locally with immutable provenance and tamper detection. It does not fetch the gated model,
retain raw audio, or reinterpret the ASR vocabulary as direct phoneme posteriors.
