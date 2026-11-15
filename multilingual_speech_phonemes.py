#!/usr/bin/env python3
"""Offline multilingual speech transcription and acoustic phoneme listener."""

from __future__ import annotations

import argparse
import importlib
import math
import os
import queue
import sys
import tempfile
import time
import unittest
import wave
from array import array
from collections import deque
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any, Iterable
from unittest.mock import patch


SAMPLE_RATE = 16_000
BLOCK_SIZE = 512
PHONE_MODEL_NAME = "facebook/wav2vec2-lv-60-espeak-cv-ft"
INSTALL_PACKAGES = (
    "numpy",
    "sounddevice",
    "torch",
    "faster-whisper",
    "silero-vad",
    "transformers",
)


class MissingDependencies(RuntimeError):
    pass


class NoSpeechDetected(RuntimeError):
    pass


@dataclass(frozen=True)
class ListenerConfig:
    model: str = "turbo"
    silence_seconds: float = 2.5
    device: str = "auto"
    microphone: int | None = None
    max_wait_seconds: float = 15.0
    max_recording_seconds: float = 60.0


@dataclass
class SpeechStopDetector:
    silence_seconds: float
    max_recording_seconds: float
    start_threshold: float = 0.60
    continue_threshold: float = 0.35
    start_frames: int = 3
    started: bool = False
    _positive_frames: int = 0
    _started_at: float | None = None
    _last_speech_at: float | None = None

    def observe(self, probability: float, now: float) -> str | None:
        if not self.started:
            if probability >= self.start_threshold:
                self._positive_frames += 1
            else:
                self._positive_frames = 0
            if self._positive_frames >= self.start_frames:
                self.started = True
                self._started_at = now
                self._last_speech_at = now
                return "started"
            return None

        assert self._started_at is not None
        assert self._last_speech_at is not None
        if now - self._started_at >= self.max_recording_seconds:
            return "max-duration"
        if probability >= self.continue_threshold:
            self._last_speech_at = now
            return None
        if now - self._last_speech_at >= self.silence_seconds:
            return "finished"
        return None


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Listen once, transcribe multilingual speech, and print acoustic IPA phonemes."
    )
    parser.add_argument("--model", default="turbo", help="Faster-Whisper model name (default: turbo).")
    parser.add_argument("--silence", type=float, default=2.5, help="Seconds of silence that ends recording.")
    parser.add_argument("--device", choices=("auto", "cpu", "cuda"), default="auto")
    parser.add_argument("--microphone", type=int, help="Input device index from --list-devices.")
    parser.add_argument("--list-devices", action="store_true", help="List microphones and exit.")
    parser.add_argument("--max-wait", type=float, default=15.0, help="Seconds to wait for speech.")
    parser.add_argument("--max-recording", type=float, default=60.0, help="Maximum utterance duration.")
    parser.add_argument("--self-test", action="store_true", help="Run dependency-free built-in tests.")
    return parser


def dependency_error_message(missing: Iterable[str]) -> str:
    missing_text = ", ".join(missing)
    install_command = "python -m pip install " + " ".join(INSTALL_PACKAGES)
    return (
        f"Missing required packages: {missing_text}\n"
        f"Install them once with:\n  {install_command}\n"
        "Then run this file again. Models download automatically on the first run."
    )


def float_samples_to_pcm16(samples: Iterable[float]) -> tuple[int, ...]:
    return tuple(
        int(round(max(-1.0, min(1.0, float(sample))) * 32767.0))
        for sample in samples
    )


def require_transcript(text: str) -> str:
    cleaned = " ".join(text.split())
    if not cleaned:
        raise ValueError("No reliable speech was recognized. Please try again closer to the microphone.")
    return cleaned


def remove_temp_file(path: str | os.PathLike[str] | None) -> None:
    if not path:
        return
    try:
        os.remove(path)
    except FileNotFoundError:
        pass


def configure_quiet_ml_imports() -> None:
    os.environ["USE_TF"] = "0"
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


def load_runtime() -> SimpleNamespace:
    configure_quiet_ml_imports()
    module_to_package = {
        "numpy": "numpy",
        "sounddevice": "sounddevice",
        "torch": "torch",
        "faster_whisper": "faster-whisper",
        "silero_vad": "silero-vad",
        "transformers": "transformers",
    }
    modules: dict[str, Any] = {}
    missing: list[str] = []
    for module_name, package_name in module_to_package.items():
        try:
            modules[module_name] = importlib.import_module(module_name)
        except (ImportError, OSError):
            missing.append(package_name)
    if missing:
        raise MissingDependencies(dependency_error_message(missing))

    return SimpleNamespace(
        np=modules["numpy"],
        sd=modules["sounddevice"],
        torch=modules["torch"],
        WhisperModel=modules["faster_whisper"].WhisperModel,
        load_silero_vad=modules["silero_vad"].load_silero_vad,
        AutoProcessor=modules["transformers"].AutoProcessor,
        AutoModelForCTC=modules["transformers"].AutoModelForCTC,
    )


def choose_device(requested: str, runtime: SimpleNamespace) -> tuple[str, str]:
    cuda_available = bool(runtime.torch.cuda.is_available())
    if requested == "cuda" and not cuda_available:
        raise RuntimeError("CUDA was requested but PyTorch cannot see a CUDA-capable GPU.")
    if requested == "cuda" or (requested == "auto" and cuda_available):
        return "cuda", "float16"
    return "cpu", "int8"


def load_phoneme_processor(runtime: SimpleNamespace) -> Any:
    # This model already emits phoneme IDs. Disabling text phonemization avoids
    # an unnecessary eSpeak/phonemizer dependency on Windows.
    return runtime.AutoProcessor.from_pretrained(PHONE_MODEL_NAME, do_phonemize=False)


def load_capture_models(runtime: SimpleNamespace) -> SimpleNamespace:
    print("Loading the speech detector (usually a few seconds)...", flush=True)
    return SimpleNamespace(vad=runtime.load_silero_vad())


def load_models(runtime: SimpleNamespace, config: ListenerConfig) -> SimpleNamespace:
    print(f"Loading Whisper '{config.model}' (the first run downloads the model)...", flush=True)
    whisper_device, compute_type = choose_device(config.device, runtime)
    try:
        whisper = runtime.WhisperModel(
            config.model,
            device=whisper_device,
            compute_type=compute_type,
        )
    except Exception as error:
        if config.device != "auto" or whisper_device != "cuda":
            raise
        print(f"CUDA initialization failed ({error}). Falling back to CPU INT8.", flush=True)
        whisper_device, compute_type = "cpu", "int8"
        whisper = runtime.WhisperModel(config.model, device=whisper_device, compute_type=compute_type)

    print(f"Loading multilingual phoneme model '{PHONE_MODEL_NAME}'...", flush=True)
    processor = load_phoneme_processor(runtime)
    phone_model = runtime.AutoModelForCTC.from_pretrained(PHONE_MODEL_NAME)
    phone_device = "cuda" if whisper_device == "cuda" else "cpu"
    phone_model.to(phone_device)
    phone_model.eval()
    return SimpleNamespace(
        whisper=whisper,
        processor=processor,
        phone_model=phone_model,
        phone_device=phone_device,
    )


def list_input_devices() -> int:
    try:
        sd = importlib.import_module("sounddevice")
    except (ImportError, OSError):
        print(dependency_error_message(("sounddevice",)), file=sys.stderr)
        return 2
    print(sd.query_devices())
    return 0


def record_utterance(
    runtime: SimpleNamespace,
    models: SimpleNamespace,
    config: ListenerConfig,
) -> Any:
    audio_queue: queue.Queue[tuple[Any, Any]] = queue.Queue()
    pre_roll_blocks = max(1, math.ceil(0.5 * SAMPLE_RATE / BLOCK_SIZE))
    pre_roll: deque[Any] = deque(maxlen=pre_roll_blocks)
    recorded: list[Any] = []
    detector = SpeechStopDetector(
        silence_seconds=config.silence_seconds,
        max_recording_seconds=config.max_recording_seconds,
    )

    def callback(indata, _frames, _time_info, status):
        audio_queue.put((indata[:, 0].copy(), status))

    started_waiting_at = time.monotonic()
    print("\nListening... Speak now.", flush=True)
    try:
        with runtime.sd.InputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            channels=1,
            dtype="float32",
            device=config.microphone,
            callback=callback,
        ):
            while True:
                now = time.monotonic()
                if not detector.started and now - started_waiting_at >= config.max_wait_seconds:
                    raise NoSpeechDetected(
                        f"No speech was detected within {config.max_wait_seconds:g} seconds."
                    )
                try:
                    block, status = audio_queue.get(timeout=0.5)
                except queue.Empty:
                    continue
                if status:
                    print(f"Microphone warning: {status}", file=sys.stderr)

                block = runtime.np.asarray(block, dtype=runtime.np.float32)
                pre_roll.append(block)
                tensor = runtime.torch.from_numpy(block)
                with runtime.torch.inference_mode():
                    probability = float(models.vad(tensor, SAMPLE_RATE).item())
                event = detector.observe(probability, time.monotonic())

                if event == "started":
                    recorded.extend(item.copy() for item in pre_roll)
                    print("Speech detected...", flush=True)
                elif detector.started:
                    recorded.append(block.copy())

                if event in {"finished", "max-duration"}:
                    if event == "max-duration":
                        print("Maximum recording duration reached.", flush=True)
                    break
    except runtime.sd.PortAudioError as error:
        raise RuntimeError(
            f"Could not open the microphone: {error}. Run with --list-devices and choose --microphone INDEX."
        ) from error

    if not recorded:
        raise NoSpeechDetected("No usable speech audio was recorded.")
    return runtime.np.concatenate(recorded).astype(runtime.np.float32, copy=False)


def write_temp_wav(audio: Any, sample_rate: int = SAMPLE_RATE) -> str:
    handle = tempfile.NamedTemporaryFile(prefix="speech_phonemes_", suffix=".wav", delete=False)
    path = handle.name
    handle.close()
    pcm = array("h", float_samples_to_pcm16(audio))
    if sys.byteorder != "little":
        pcm.byteswap()
    try:
        with wave.open(path, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(pcm.tobytes())
    except Exception:
        remove_temp_file(path)
        raise
    return path


def transcribe_audio(models: SimpleNamespace, wav_path: str) -> tuple[str, str, float]:
    segments, info = models.whisper.transcribe(
        wav_path,
        beam_size=5,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 300},
        condition_on_previous_text=False,
        temperature=0.0,
    )
    transcript = require_transcript(" ".join(segment.text.strip() for segment in segments))
    language = getattr(info, "language", "unknown") or "unknown"
    probability = float(getattr(info, "language_probability", 0.0) or 0.0)
    return transcript, language, probability


def recognize_phonemes(
    runtime: SimpleNamespace,
    models: SimpleNamespace,
    audio: Any,
    sample_rate: int = SAMPLE_RATE,
) -> str:
    chunk_samples = 15 * sample_rate
    decoded_chunks: list[str] = []
    for start in range(0, len(audio), chunk_samples):
        chunk = audio[start : start + chunk_samples]
        if len(chunk) < int(0.08 * sample_rate):
            continue
        inputs = models.processor(chunk, sampling_rate=sample_rate, return_tensors="pt")
        model_inputs = {"input_values": inputs.input_values.to(models.phone_device)}
        attention_mask = getattr(inputs, "attention_mask", None)
        if attention_mask is not None:
            model_inputs["attention_mask"] = attention_mask.to(models.phone_device)
        with runtime.torch.inference_mode():
            logits = models.phone_model(**model_inputs).logits
        predicted_ids = runtime.torch.argmax(logits, dim=-1)
        decoded = models.processor.batch_decode(predicted_ids)[0].strip()
        if decoded:
            decoded_chunks.append(decoded)
    return " ".join(decoded_chunks) or "(no stable phonemes detected)"


def run_self_tests() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__])
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


def config_from_args(args: argparse.Namespace, parser: argparse.ArgumentParser) -> ListenerConfig:
    for name, value in (
        ("--silence", args.silence),
        ("--max-wait", args.max_wait),
        ("--max-recording", args.max_recording),
    ):
        if value <= 0:
            parser.error(f"{name} must be greater than zero")
    return ListenerConfig(
        model=args.model,
        silence_seconds=args.silence,
        device=args.device,
        microphone=args.microphone,
        max_wait_seconds=args.max_wait,
        max_recording_seconds=args.max_recording,
    )


class SpeechStopDetectorTests(unittest.TestCase):
    def make_detector(self):
        return SpeechStopDetector(
            silence_seconds=2.5,
            max_recording_seconds=10.0,
            start_threshold=0.60,
            continue_threshold=0.35,
            start_frames=3,
        )

    def test_requires_three_positive_frames_before_starting(self):
        detector = self.make_detector()

        self.assertIsNone(detector.observe(0.90, 0.00))
        self.assertIsNone(detector.observe(0.80, 0.03))
        self.assertEqual(detector.observe(0.70, 0.06), "started")

    def test_ignores_noise_before_speech(self):
        detector = self.make_detector()

        for index, probability in enumerate((0.10, 0.59, 0.20, 0.61, 0.10)):
            self.assertIsNone(detector.observe(probability, index * 0.03))
        self.assertFalse(detector.started)

    def test_finishes_after_trailing_silence(self):
        detector = self.make_detector()
        detector.observe(0.90, 0.00)
        detector.observe(0.90, 0.03)
        detector.observe(0.90, 0.06)

        self.assertIsNone(detector.observe(0.10, 2.55))
        self.assertEqual(detector.observe(0.10, 2.57), "finished")

    def test_resumed_speech_cancels_pending_finish(self):
        detector = self.make_detector()
        detector.observe(0.90, 0.00)
        detector.observe(0.90, 0.03)
        detector.observe(0.90, 0.06)
        detector.observe(0.10, 2.00)
        detector.observe(0.80, 2.40)

        self.assertIsNone(detector.observe(0.10, 4.60))
        self.assertEqual(detector.observe(0.10, 4.91), "finished")

    def test_stops_at_maximum_recording_duration(self):
        detector = self.make_detector()
        detector.observe(0.90, 0.00)
        detector.observe(0.90, 0.03)
        detector.observe(0.90, 0.06)

        self.assertEqual(detector.observe(0.90, 10.07), "max-duration")


class RuntimeHelperTests(unittest.TestCase):
    def test_main_starts_listening_before_loading_heavy_inference_models(self):
        events = []

        def fake_load_models(_runtime, _config):
            events.append("heavy-models")
            return SimpleNamespace()

        def fake_record(_runtime, _models, _config):
            events.append("listening")
            return (0.0,)

        module = sys.modules[__name__]
        with (
            patch.object(module, "load_runtime", return_value=SimpleNamespace()),
            patch.object(module, "load_capture_models", return_value=SimpleNamespace(), create=True),
            patch.object(module, "load_models", side_effect=fake_load_models),
            patch.object(module, "record_utterance", side_effect=fake_record),
            patch.object(module, "write_temp_wav", return_value="fake.wav"),
            patch.object(module, "transcribe_audio", return_value=("hello", "en", 0.9)),
            patch.object(module, "recognize_phonemes", return_value="h ə l oʊ"),
            patch.object(module, "remove_temp_file"),
            patch("builtins.print"),
        ):
            self.assertEqual(main([]), 0)

        self.assertLess(events.index("listening"), events.index("heavy-models"))

    def test_phoneme_processor_disables_text_phonemizer_backend(self):
        class FakeAutoProcessor:
            @staticmethod
            def from_pretrained(name, **kwargs):
                return name, kwargs

        name, kwargs = load_phoneme_processor(SimpleNamespace(AutoProcessor=FakeAutoProcessor))

        self.assertEqual(name, PHONE_MODEL_NAME)
        self.assertIs(kwargs["do_phonemize"], False)

    def test_quiet_import_configuration_disables_unused_tensorflow_backend(self):
        original = os.environ.pop("USE_TF", None)
        try:
            configure_quiet_ml_imports()
            self.assertEqual(os.environ["USE_TF"], "0")
            self.assertEqual(os.environ["TF_CPP_MIN_LOG_LEVEL"], "3")
        finally:
            if original is None:
                os.environ.pop("USE_TF", None)
            else:
                os.environ["USE_TF"] = original

    def test_dependency_message_contains_one_actionable_install_command(self):
        message = dependency_error_message(("sounddevice", "faster-whisper"))

        self.assertIn("python -m pip install", message)
        self.assertIn("sounddevice", message)
        self.assertIn("faster-whisper", message)

    def test_float_audio_is_clipped_and_encoded_as_pcm16(self):
        pcm = float_samples_to_pcm16((-2.0, -1.0, 0.0, 1.0, 2.0))

        self.assertEqual(pcm, (-32767, -32767, 0, 32767, 32767))

    def test_blank_transcript_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "No reliable speech"):
            require_transcript("  \n ")

    def test_temporary_audio_cleanup_removes_file(self):
        with tempfile.NamedTemporaryFile(delete=False) as handle:
            path = handle.name

        remove_temp_file(path)

        self.assertFalse(__import__("os").path.exists(path))


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.self_test:
        return run_self_tests()
    if args.list_devices:
        return list_input_devices()

    config = config_from_args(args, parser)
    wav_path: str | None = None
    try:
        print("Starting the offline speech listener...", flush=True)
        runtime = load_runtime()
        capture_models = load_capture_models(runtime)
        audio = record_utterance(runtime, capture_models, config)
        wav_path = write_temp_wav(audio)
        print("Processing speech...", flush=True)
        print("On the first run, model downloads can take several minutes.", flush=True)
        models = load_models(runtime, config)
        transcript, language, probability = transcribe_audio(models, wav_path)
        phonemes = recognize_phonemes(runtime, models, audio)

        print("\n" + "=" * 72)
        print(f"Detected language : {language}")
        print(f"Language confidence: {probability:.1%}")
        print(f"You said          : {transcript}")
        print(f"Acoustic phonemes : {phonemes}")
        print("=" * 72)
        print("Phonemes are automatic acoustic estimates, not clinical measurements.")
        return 0
    except MissingDependencies as error:
        print(f"\n{error}", file=sys.stderr)
        return 2
    except NoSpeechDetected as error:
        print(f"\n{error}", file=sys.stderr)
        return 3
    except KeyboardInterrupt:
        print("\nStopped by user.", file=sys.stderr)
        return 130
    except Exception as error:
        print(f"\nSpeech listener failed: {error}", file=sys.stderr)
        if config.device == "cuda":
            print("Try again with --device cpu if CUDA libraries are unavailable.", file=sys.stderr)
        return 1
    finally:
        remove_temp_file(wav_path)


if __name__ == "__main__":
    raise SystemExit(main())
