# Multilingual Speech and Phoneme Listener Design

**Date:** 2026-08-05
**Status:** Approved for implementation

## Goal

Provide one Python file that runs locally on Windows, prints `Listening...`, records microphone speech, automatically finishes after 2.5 seconds of trailing silence, and prints the detected language, transcript, language confidence, and acoustic IPA-like phoneme sequence.

## Model stack

- `faster-whisper` with OpenAI Whisper `turbo` for automatic multilingual transcription. The user may select `large-v3` for maximum accuracy or smaller Whisper checkpoints for lower-memory computers.
- Silero VAD for language-independent speech activity probabilities and reliable trailing-silence detection.
- Meta `facebook/wav2vec2-lv-60-espeak-cv-ft` for direct multilingual acoustic phoneme recognition from 16 kHz audio.

All inference is local after the first model download. No microphone recording is uploaded or retained.

## Runtime flow

1. Validate Python dependencies and print one exact installation command if they are missing.
2. Load VAD, transcription, and phoneme models, with progress messages because first-run downloads may be large.
3. Open the selected microphone at 16 kHz mono.
4. Print `Listening...` and maintain a short pre-roll buffer so the first sound is not clipped.
5. Ignore background noise until several consecutive speech-positive frames are observed.
6. After speech starts, continue recording while using a lower continuation threshold to avoid cutting quiet syllables.
7. Finish after 2.5 seconds without speech, or at a configurable maximum recording duration.
8. Save a temporary PCM WAV, run Whisper and Wav2Vec2, print results, and delete the WAV in a `finally` block.

## Command-line behavior

- Default execution: one utterance, automatic language detection, 2.5-second ending silence.
- `--model`: choose a Faster-Whisper checkpoint; default `turbo`.
- `--silence`: change trailing silence seconds.
- `--device`: choose `auto`, `cpu`, or `cuda`.
- `--microphone`: choose an input device by numeric index.
- `--list-devices`: display available audio devices and exit.
- `--max-wait` and `--max-recording`: bound waiting and recording time.
- `--self-test`: run dependency-free tests for the speech-state and silence-timing logic.

## Reliability and error handling

- A hysteresis state machine uses a higher threshold to start and a lower threshold to continue speech.
- Consecutive positive frames are required before recording is considered started.
- Missing dependencies, absent microphones, unsupported sample rates, model-download failures, CUDA failures, no speech, and keyboard interruption receive clear messages.
- `auto` device mode attempts CUDA only when the runtime reports it available and otherwise uses CPU INT8.
- Empty or low-confidence audio does not invent a transcript; the file reports that no reliable speech was recognized.
- Acoustic phonemes are labelled as estimates, not clinical or diagnostic measurements.

## Verification

- Built-in deterministic self-tests cover start debounce, pre-speech noise, trailing-silence completion, speech resumption, and maximum duration.
- Python syntax compilation must pass.
- Argument parsing and dependency-error output must be exercised without downloading models.
- A live microphone/model test is run when installed dependencies and model download time permit; otherwise this remaining environment requirement is reported explicitly.

## Delivery boundary

The user-facing deliverable is exactly one Python source file. Design and plan documentation may exist in the project documentation, but no separate runtime configuration, test, or requirements file is needed.
