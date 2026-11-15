# Multilingual Speech and Phoneme Listener Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build one local Python file that records one multilingual utterance, ends after 2.5 seconds of silence, and prints the transcript plus acoustic IPA phonemes.

**Architecture:** A dependency-light CLI owns argument parsing and microphone capture. A deterministic hysteresis state machine consumes Silero speech probabilities, then temporary 16 kHz PCM audio is independently processed by Faster-Whisper and Meta Wav2Vec2 before guaranteed deletion.

**Tech Stack:** Python 3.12, NumPy, sounddevice, Silero VAD, PyTorch, Transformers, Faster-Whisper.

## Global Constraints

- Deliver exactly one user-facing runtime source file: `multilingual_speech_phonemes.py`.
- Default trailing silence is exactly 2.5 seconds.
- Audio is mono 16 kHz and is deleted after inference.
- Language selection is automatic unless the user changes the model arguments.
- Phoneme output is explicitly labelled as an acoustic estimate and not a clinical measurement.
- Built-in `--self-test` must run without installing model dependencies.

---

### Task 1: CLI and speech-state self-tests

**Files:**
- Create: `multilingual_speech_phonemes.py`

**Interfaces:**
- Produces: `ListenerConfig`, `SpeechStopDetector.observe(probability, now) -> str | None`, `build_parser()`, and `run_self_tests() -> int`.

- [ ] **Step 1: Add failing built-in tests before implementations**

Add `unittest` cases that require three positive frames to emit `started`, ignore pre-speech noise, emit `finished` after 2.5 seconds below the continuation threshold, cancel pending finish when speech resumes, and emit `max-duration` when recording exceeds its bound.

- [ ] **Step 2: Run the red test**

Run: `python multilingual_speech_phonemes.py --self-test`

Expected: FAIL because `SpeechStopDetector` is missing.

- [ ] **Step 3: Implement minimal deterministic state logic and CLI parsing**

Implement a dataclass-backed detector with start threshold `0.60`, continuation threshold `0.35`, three start frames, configurable trailing silence, and maximum recording duration. Add options `--model`, `--silence`, `--device`, `--microphone`, `--list-devices`, `--max-wait`, `--max-recording`, and `--self-test`.

- [ ] **Step 4: Run self-tests green**

Run: `python multilingual_speech_phonemes.py --self-test`

Expected: all detector and parser tests pass without importing ML packages.

### Task 2: Microphone recording and local inference

**Files:**
- Modify: `multilingual_speech_phonemes.py`

**Interfaces:**
- Consumes: `ListenerConfig` and `SpeechStopDetector` from Task 1.
- Produces: `load_runtime()`, `record_utterance() -> numpy.ndarray`, `write_temp_wav()`, `transcribe_audio()`, `recognize_phonemes()`, and `main() -> int`.

- [ ] **Step 1: Extend the built-in test with dependency and audio-helper expectations**

Test that missing imports produce one actionable pip command, float audio clips safely to signed 16-bit PCM, blank transcripts are rejected, and temporary paths are deleted by the top-level cleanup helper.

- [ ] **Step 2: Run the expanded tests red**

Run: `python multilingual_speech_phonemes.py --self-test`

Expected: FAIL on the first missing helper.

- [ ] **Step 3: Implement microphone and models**

Use `sounddevice.InputStream` with 512-sample float32 blocks. Feed each block into Silero, retain 0.5 seconds of pre-roll, and stop on detector events. Write PCM with the standard-library `wave` module. Load Faster-Whisper `turbo` using CPU INT8 or CUDA FP16/INT8 fallback, then load `facebook/wav2vec2-lv-60-espeak-cv-ft` with Transformers and decode CTC phoneme IDs.

- [ ] **Step 4: Implement defensive terminal behavior**

Print model-download progress, `Listening...`, `Speech detected...`, `Processing...`, detected language, language probability, transcript, and acoustic phoneme estimate. Handle dependency, microphone, timeout, CUDA, model-download, no-speech, and `Ctrl+C` failures with non-zero exits and concise remediation.

- [ ] **Step 5: Run built-in tests green**

Run: `python multilingual_speech_phonemes.py --self-test`

Expected: all tests pass and no model is downloaded.

### Task 3: Verification and handoff

**Files:**
- Verify: `multilingual_speech_phonemes.py`

**Interfaces:**
- Consumes: the complete single-file CLI.
- Produces: verified syntax, help output, device-list behavior, and installation instructions.

- [ ] **Step 1: Compile and inspect CLI help**

Run: `python -m py_compile multilingual_speech_phonemes.py` and `python multilingual_speech_phonemes.py --help`.

Expected: both exit zero.

- [ ] **Step 2: Run self-tests and dependency-path verification**

Run: `python multilingual_speech_phonemes.py --self-test` and execute the default command in the current environment.

Expected: self-tests pass; default either performs a live utterance or prints the exact dependency installation command without a traceback.

- [ ] **Step 3: Check one-file boundary and whitespace**

Run: `git diff --check -- multilingual_speech_phonemes.py` and confirm that no second runtime/test/config file was created.

- [ ] **Step 4: Commit only the runtime file if the surrounding worktree permits it**

Use `git commit --only multilingual_speech_phonemes.py` so unrelated staged work remains untouched.
