"""Ephemeral word-assessment orchestration (DEC-005..009, PRV-001..010)."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from .audio import UnsupportedAudio, decode_wav_bytes, validate_audio
from .calibration import EvidenceCalibrator
from .classifier import LinearWordClassifier
from .contracts import (
    AssessmentEvidence,
    AssessmentResult,
    Decision,
    EvidenceItem,
    ModelEvidence,
    ReasonCode,
    WordCandidate,
)
from .dtw import ReferenceBank
from .model import AcousticModel, ModelCapabilityError
from .normalization import NormalizationConfig, create_normalized_view
from .policy import SafeAdaptivePolicy, SessionPolicyState, TherapistConstraints


@dataclass(frozen=True)
class AssessmentContext:
    session_id: str
    attempt_id: str
    word_id: str
    target_word: str
    attempt_count: int
    therapist_constraints: TherapistConstraints
    stop_requested: bool = False
    break_requested: bool = False


class WordAssessmentService:
    def __init__(
        self,
        *,
        model: AcousticModel,
        classifier: LinearWordClassifier,
        reference_bank: ReferenceBank,
        calibrator: EvidenceCalibrator,
        policy: SafeAdaptivePolicy,
        normalization: NormalizationConfig | None = None,
        vad=None,
    ) -> None:
        self.model = model
        self.classifier = classifier
        self.reference_bank = reference_bank
        self.calibrator = calibrator
        self.policy = policy
        self.normalization = normalization or NormalizationConfig()
        self.vad = vad

    @property
    def production_vad_ready(self):
        return bool(self.vad is not None and self.vad.ready
                    and self.calibrator.artifact.vad_config_hash == self.vad.config_hash)

    @property
    def live_pipeline_ready(self) -> bool:
        # DATA-013: direct service calls must enforce the same binding as bundle verification.
        from .live_evidence import pipeline_fingerprint
        return bool(self.calibrator.artifact.live_pipeline_hash
                    and self.calibrator.artifact.live_pipeline_hash == pipeline_fingerprint(self.normalization))

    def assess(self, audio_bytes: bytes, context: AssessmentContext) -> AssessmentResult:
        started = perf_counter()
        decoded = None
        raw: ModelEvidence | None = None
        normalized: ModelEvidence | None = None
        try:
            try:
                decoded = decode_wav_bytes(audio_bytes)
            except UnsupportedAudio:
                return self._unscorable(context, ReasonCode.UNSUPPORTED_AUDIO, started=started)
            try:
                quality = (self.vad.validate(decoded.samples, decoded.sample_rate) if self.vad is not None
                           else validate_audio(decoded.samples, decoded.sample_rate))
            except ModelCapabilityError:
                return self._unscorable(context, ReasonCode.VAD_UNAVAILABLE, started=started)
            if not quality.valid:
                reason = ReasonCode.NO_SPEECH if quality.reason == "no_speech" else ReasonCode.INVALID_AUDIO
                return self._unscorable(context, reason, quality=quality, started=started)

            # AU-008/009: the current energy validator is engineering-only.
            # Approved calibration cannot promote this unvalidated capture path.
            if self.calibrator.ready and not self.model.is_test_double and not self.production_vad_ready:
                return self._unscorable(context, ReasonCode.VAD_UNAVAILABLE, quality=quality, started=started)
            if self.calibrator.ready and not self.model.is_test_double and not self.live_pipeline_ready:
                return self._unscorable(context, ReasonCode.CALIBRATION_UNAVAILABLE, quality=quality, started=started)
            if context.word_id not in self.classifier.artifact.labels:
                return self._unscorable(context, ReasonCode.CLASSIFIER_UNAVAILABLE, quality=quality, started=started)

            try:
                raw = self.model.infer(decoded.samples, decoded.sample_rate, context.target_word)
            except ModelCapabilityError as exc:
                return self._unscorable(
                    context,
                    self._model_reason(str(exc)),
                    quality=quality,
                    started=started,
                )

            normalized_view = create_normalized_view(decoded, self.normalization)
            normalized_reason = normalized_view.reason or "normalized_view_unavailable"
            if normalized_view.available:
                try:
                    normalized = self.model.infer(
                        normalized_view.samples,
                        normalized_view.sample_rate,
                        context.target_word,
                    )
                except ModelCapabilityError as exc:
                    normalized_reason = str(exc).split(":", 1)[0]

            original_item = self._model_item(raw, context.target_word)
            normalized_item = self._model_item(normalized, context.target_word) if normalized else EvidenceItem(
                available=False,
                reason=normalized_reason,
            )
            classification = self.classifier.predict(raw.embeddings, context.word_id) if raw.embeddings is not None else None
            classifier_item = (
                classification.evidence
                if classification is not None
                else EvidenceItem(available=False, reason="embeddings_unavailable")
            )
            distance = (
                self.reference_bank.best_distance(
                    context.word_id,
                    raw.embeddings,
                    model_hash=raw.model_hash,
                )
                if raw.embeddings is not None
                else None
            )
            dtw_item = (
                EvidenceItem(available=True, similarity=1.0 / (1.0 + distance))
                if distance is not None
                else EvidenceItem(available=False, reason="reference_unavailable")
            )
            evidence = AssessmentEvidence(
                original_asr=original_item,
                normalized_asr=normalized_item,
                word_classifier=classifier_item,
                embedding_dtw=dtw_item,
                classifier_entropy=(classification.entropy if classification is not None else None),
            )
            fusion = self.calibrator.decide(evidence, quality)
            candidates = self._candidates(raw, classification.candidates if classification else ())
            provisional = AssessmentResult(
                session_id=context.session_id,
                attempt_id=context.attempt_id,
                word_id=context.word_id,
                target_word=context.target_word,
                decision=fusion.decision,
                word_match_probability=fusion.probability,
                confidence=fusion.confidence,
                observed_candidates=candidates,
                evidence=evidence,
                quality=quality,
                reason_code=fusion.reason_code,
                model_version=raw.model_version,
                classifier_version=self.classifier.version,
                reference_bank_version=self.reference_bank.version,
                calibration_version=self.calibrator.artifact.version,
                policy_version=self.policy.version,
                latency_ms=self._elapsed_ms(started),
            )
            policy_decision = self.policy.choose(
                provisional,
                SessionPolicyState(
                    attempt_count=context.attempt_count,
                    stop_requested=context.stop_requested,
                    break_requested=context.break_requested,
                ),
                context.therapist_constraints,
            )
            return provisional.model_copy(
                update={
                    "response_intent": policy_decision.response_intent,
                    "avatar_state": policy_decision.avatar_state,
                    "next_exercise_id": policy_decision.next_exercise_id,
                    "latency_ms": self._elapsed_ms(started),
                }
            )
        finally:
            # Drop local references on every success/error path. Product code never persists them.
            decoded = None
            raw = None
            normalized = None

    def _unscorable(
        self,
        context: AssessmentContext,
        reason: ReasonCode,
        *,
        quality=None,
        started: float,
    ) -> AssessmentResult:
        provisional = AssessmentResult.unscorable(
            reason,
            session_id=context.session_id,
            attempt_id=context.attempt_id,
            word_id=context.word_id,
            target_word=context.target_word,
            quality=quality,
            latency_ms=self._elapsed_ms(started),
        )
        policy_decision = self.policy.choose(
            provisional,
            SessionPolicyState(
                attempt_count=context.attempt_count,
                stop_requested=context.stop_requested,
                break_requested=context.break_requested,
            ),
            context.therapist_constraints,
        )
        return provisional.model_copy(
            update={
                "response_intent": policy_decision.response_intent,
                "avatar_state": policy_decision.avatar_state,
                "next_exercise_id": policy_decision.next_exercise_id,
                "policy_version": self.policy.version,
            }
        )

    @staticmethod
    def _model_item(model: ModelEvidence | None, target_word: str) -> EvidenceItem:
        if model is None or model.target_probability is None:
            return EvidenceItem(available=False, reason="target_evidence_unavailable")
        return EvidenceItem(
            available=True,
            target_probability=model.target_probability,
            top1_is_target=bool(model.candidates and model.candidates[0].word == target_word),
        )

    @staticmethod
    def _model_reason(message: str) -> ReasonCode:
        if "integrity" in message:
            return ReasonCode.MODEL_INTEGRITY_MISMATCH
        if "timeout" in message:
            return ReasonCode.MODEL_TIMEOUT
        if "unavailable" in message:
            return ReasonCode.MODEL_UNAVAILABLE
        return ReasonCode.MODEL_INFERENCE_FAILED

    @staticmethod
    def _candidates(raw: ModelEvidence, classifier_candidates) -> list[WordCandidate]:
        merged: dict[str, float] = {candidate.word: candidate.probability for candidate in raw.candidates}
        for candidate in classifier_candidates:
            merged[candidate.word] = max(merged.get(candidate.word, 0.0), candidate.probability)
        return [
            WordCandidate(word=word, probability=probability)
            for word, probability in sorted(merged.items(), key=lambda item: item[1], reverse=True)[:5]
        ]

    @staticmethod
    def _elapsed_ms(started: float) -> int:
        return max(0, round((perf_counter() - started) * 1000))
