"""DEC-018: real engineering inference without changing artifact approvals."""
import asyncio
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .artifacts import ArtifactFile, _load_classifier
from .assessment import WordAssessmentService
from .calibration import CalibrationArtifact, EvidenceCalibrator
from .classifier import LinearWordClassifier
from .inference_runner import inference_runner
from .model import NeMoIndicConformerAdapter, sha256_file
from .policy import SafeAdaptivePolicy
from .reference_builder import load_reference_bank_artifact
from .vocabulary import VocabularyRegistry


class EngineeringConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["vaakmitra-local-diagnostics-1"]
    model: ArtifactFile
    vocabulary: ArtifactFile
    classifier: ArtifactFile
    reference_bank: ArtifactFile
    calibration: ArtifactFile
    dataset_manifest: ArtifactFile
    vad_config: ArtifactFile | None = None
    device: Literal["cpu", "cuda"] = "cpu"


def load_engineering(config_path):
    config = EngineeringConfig.model_validate_json(Path(config_path).read_text(encoding="utf-8"))
    paths = {}
    for name in ("model", "vocabulary", "classifier", "reference_bank", "calibration", "dataset_manifest"):
        artifact = getattr(config, name)
        path = Path(artifact.path)
        if not path.is_absolute() or not path.is_file() or sha256_file(path) != artifact.sha256:
            raise ValueError(f"{name}_integrity_mismatch")
        paths[name] = path
    calibration = CalibrationArtifact.model_validate_json(paths["calibration"].read_text(encoding="utf-8"))
    # A diagnostic configuration cannot promote or rewrite an artifact's approval.
    if calibration.approved:
        raise ValueError("diagnostics_require_unapproved_engineering_calibration")
    for name in ("model", "vocabulary", "classifier", "reference_bank", "dataset_manifest"):
        if getattr(calibration, f"{name}_hash") != getattr(config, name).sha256:
            raise ValueError(f"calibration_{name}_hash_mismatch")
    vocabulary = VocabularyRegistry.from_json(paths["vocabulary"])
    classifier = _load_classifier(paths["classifier"])
    if classifier.model_hash != config.model.sha256 or classifier.vocabulary_hash != config.vocabulary.sha256:
        raise ValueError("classifier_hash_binding_mismatch")
    bank = load_reference_bank_artifact(paths["reference_bank"], expected_model_hash=config.model.sha256,
                                       expected_vocabulary_hash=config.vocabulary.sha256)
    words = {entry.word_id: entry.canonical_tamil for entry in vocabulary.entries
             if entry.word_id in classifier.labels and entry.word_id in bank.references}
    if not words:
        raise ValueError("engineering_vocabulary_empty")
    model = NeMoIndicConformerAdapter(model_path=paths["model"], expected_sha256=config.model.sha256, device=config.device)
    model.load()
    vad = None
    if config.vad_config is not None:
        from .vad import OnnxVad
        vad_path = Path(config.vad_config.path)
        if sha256_file(vad_path) != config.vad_config.sha256:
            raise ValueError('vad_config_integrity_mismatch')
        vad = OnnxVad.from_config(vad_path)
    service = WordAssessmentService(model=model, classifier=LinearWordClassifier(classifier), reference_bank=bank,
                                    calibrator=EvidenceCalibrator(calibration), policy=SafeAdaptivePolicy(), vad=vad)
    return service, words, {"vocabulary_version": vocabulary.version, "model_version": model.model_version,
                           "classifier_version": classifier.version, "reference_bank_version": bank.version,
                           "calibration_version": calibration.version, "device": config.device,
                           "vad_mode": "onnx_cpu" if vad else "energy_degraded",
                           "vad_config_hash": vad.config_hash if vad else None}


class DiagnosticRuntime:
    def __init__(self):
        self.state = "disabled"
        self.reason = None
        self.service = None
        self.words = {}
        self.versions = {}
        self.task = None

    def start(self, config_path):
        if self.task is not None:
            return
        self.state = "loading"
        self.task = asyncio.create_task(self._load(config_path))

    async def _load(self, config_path):
        try:
            service, words, versions = await inference_runner.run(load_engineering, config_path, timeout=300)
            self.service, self.words, self.versions = service, words, versions
            self.state = "ready"
        except Exception as exc:
            self.state = "unavailable"
            # Only known reason identifiers, never raw paths or exception text.
            self.reason = "diagnostic_artifact_or_runtime_unavailable"
            if isinstance(exc, ValueError) and str(exc).replace("_", "").isalnum():
                self.reason = str(exc)

    def status(self):
        return {"state": self.state, "reason": self.reason, "pipeline_ready": self.service is not None,
                "scoring_ready": False, "evidence_scope": "adult_engineering_unapproved", "busy": inference_runner.busy,
                "words": [{"word_id": key, "target_word": value} for key, value in self.words.items()],
                **self.versions}


diagnostic_runtime = DiagnosticRuntime()
