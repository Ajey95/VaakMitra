package com.team96.speakeasy.audio

import android.content.Context
import android.util.Log
import kotlin.math.abs

/** DEC-028/MST-006..009: complete offline development pipeline with official abstention. */
class MobileWordPracticeEngine private constructor(
    private val bundle: LoadedMobileBundle,
    private val student: OnnxMobileWordStudent,
    private val vad: OnnxSpeechVad,
    private val phoneme: OnnxMobilePhoneme?,
    private val backbone: OnnxBackbonePhoneme? = null,
    private val practicePhones: Map<String,List<String>> = emptyMap(),
    private val captureProfile:BackboneCaptureProfile=BackboneCaptureProfile.LEGACY,
) : AutoCloseable {
    /** DEC-056: waveform-only preview; letters cannot fall back to the word classifier. */
    @Synchronized
    fun assessLetter(targetId: String, samples: ShortArray, sampleRate: Int = 16_000): LocalWordOutcome {
        if (com.team96.speakeasy.journey.TamilAlphabet.find(targetId) == null)
            return LocalWordOutcome(reason = "TARGET_UNAVAILABLE", developmentResult = "DEV_UNAVAILABLE")
        if (phoneme == null && backbone == null)
            return LocalWordOutcome(reason = "MODEL_UNAVAILABLE", developmentResult = "DEV_UNAVAILABLE")
        return assess(targetId, samples, sampleRate)
    }

    @Synchronized
    fun assess(targetId: String, samples: ShortArray, sampleRate: Int = 16_000): LocalWordOutcome =
        assessWithProfile(targetId,samples,sampleRate,captureProfile).let{outcome->
            val alignment=if(outcome.soundPracticeEvidence?.sequenceAgrees==true)PauseAlignmentResult("sequence_agreement")else outcome.pauseAlignment
            val reconciled=outcome.copy(pauseAlignment=alignment)
            val cue=PracticeVoiceCoach.choose(reconciled,PcmCaptureEvidence.analyze(samples))
            val tool=if(com.team96.speakeasy.journey.StarterWords.all.any{it.id==targetId})PracticeVoiceCoach.toolResult(targetId,alignment,cue)else null
            reconciled.copy(coachCue=cue,coachToolResult=tool)
        }

    /** Paired public-fixture validation uses one acoustic session, never a second model or word hint. */
    @Synchronized
    fun assessBackboneWindowForValidation(targetId:String,samples:ShortArray,profile:BackboneCaptureProfile):LocalWordOutcome {
        check(com.team96.speakeasy.BuildConfig.DEBUG);checkNotNull(backbone)
        return assessWithProfile(targetId,samples,16000,profile)
    }

    private fun assessWithProfile(targetId:String,samples:ShortArray,sampleRate:Int,profile:BackboneCaptureProfile):LocalWordOutcome {
        val captureEvidence = PcmCaptureEvidence.analyze(samples)
        Log.i(
            DIAGNOSTIC_TAG,
            "capture samples=${captureEvidence.sampleCount} peak=${captureEvidence.peakAbsolute} " +
                "rms=${"%.2f".format(java.util.Locale.US, captureEvidence.rms)} " +
                "nonZero=${"%.4f".format(java.util.Locale.US, captureEvidence.nonZeroRatio)}",
        )
        val captureReason = captureProblem(targetId, samples, sampleRate)
        if (captureReason != null) {
            Log.i(DIAGNOSTIC_TAG, "captureRejected reason=$captureReason")
            return LocalWordOutcome(reason = captureReason, developmentResult = "DEV_UNAVAILABLE")
        }
        return try {
            val vadEvidence = vad.analyze(samples, sampleRate)
            Log.i(
                DIAGNOSTIC_TAG,
                "vad accepted=${vadEvidence.hasEnoughSpeech} maxProbability=${vadEvidence.maximumProbability} " +
                    "speechMs=${vadEvidence.speechMilliseconds} threshold=${vadEvidence.threshold} " +
                    "first=${vadEvidence.firstSpeechSample} last=${vadEvidence.lastSpeechSampleExclusive}",
            )
            if (!vadEvidence.hasEnoughSpeech) {
                return LocalWordOutcome(reason = "VAD_NO_SPEECH", developmentResult = "DEV_UNAVAILABLE")
            }
            val selectedProfile=if(backbone!=null)profile else BackboneCaptureProfile.LEGACY
            val detectedSpeech = vadEvidence.extractSpeech(samples,selectedProfile.vadPaddingSamples)
            if (detectedSpeech.isEmpty()) {
                return LocalWordOutcome(reason = "VAD_NO_SPEECH", developmentResult = "DEV_UNAVAILABLE")
            }
            val activeSpeech = if(selectedProfile==BackboneCaptureProfile.CONSERVATIVE_V1)BackboneCaptureWindow.trim(detectedSpeech)
                else MobilePcmPreprocessor.trimActiveWord(detectedSpeech, sampleRate)
            Log.i(DIAGNOSTIC_TAG, "speechWindow vadSamples=${detectedSpeech.size} activeSamples=${activeSpeech.size}")
            if (activeSpeech.isEmpty()) {
                detectedSpeech.fill(0)
                return LocalWordOutcome(reason = "VAD_NO_SPEECH", developmentResult = "DEV_UNAVAILABLE")
            }
            if (phoneme != null || backbone != null) {
                try {
                    if (activeSpeech.size > PhonemeAudio.SAMPLES) {
                        return LocalWordOutcome(reason = "TOO_LONG", developmentResult = "DEV_UNAVAILABLE")
                    }
                    if(activeSpeech.size<400)return LocalWordOutcome(reason="TOO_SHORT",developmentResult="DEV_UNAVAILABLE")
                    // The target is consulted only AFTER waveform-only inference has finished.
                    val observed=backbone?.inferObservation(activeSpeech,includeFrames=true)
                    val predicted = observed?.phones ?: checkNotNull(phoneme).infer(activeSpeech)
                    // PHN012: reference-conditioned diagnostics follow unchanged free decoding.
                    // Owned frame evidence never enters a report or the coaching tool payload.
                    val alignment=observed?.frameEvidence?.let{evidence->
                        try{PauseAwareAlignment.align(evidence.probabilities,evidence.tokens,practicePhones[targetId].orEmpty())}
                        finally{evidence.close()}
                    }
                    return LocalWordOutcome(
                        reason = if (predicted.isEmpty()) "PHONEME_EMPTY" else "PHONEME_TOKENS",
                        developmentResult = if (predicted.isEmpty()) "DEV_UNCERTAIN" else "DEV_PHONEMES",
                        predictedPhonemes = predicted,
                        supportAction = if(observed!=null)PhoneticSupportPolicy.fromPreview(
                            observed.phones,practicePhones[targetId].orEmpty(),checkNotNull(backbone).knownTokens,
                        ).action else null,
                        // Separate optional educational experiment, never clinical support/confidence.
                        soundPracticeEvidence = if(observed?.supported==true)SoundPracticePolicy.evidence(
                            targetId,observed.phones,practicePhones[targetId].orEmpty(),checkNotNull(backbone).knownTokens,
                        ) else null,
                        pauseAlignment=alignment,
                    )
                } finally { activeSpeech.fill(0); detectedSpeech.fill(0) }
            }
            val targetDuration = bundle.calibration.targetDurationSamples[targetId]
            if (targetDuration == null || targetDuration !in 3_200..32_000) {
                activeSpeech.fill(0)
                detectedSpeech.fill(0)
                return LocalWordOutcome(reason = "MODEL_UNAVAILABLE", developmentResult = "DEV_UNAVAILABLE")
            }
            val normalizedSpeech = MobilePcmPreprocessor.normalizeDuration(activeSpeech, targetDuration)
            Log.i(DIAGNOSTIC_TAG, "duration targetSamples=$targetDuration normalizedSamples=${normalizedSpeech.size}")
            val waveform = MobilePcmPreprocessor.prepare(normalizedSpeech)
            try {
                val output = student.infer(waveform)
                val outcome = MobileDevelopmentPolicy.evaluate(
                    targetId = targetId,
                    probabilities = output.probabilities,
                    embedding = output.embedding,
                    references = bundle.references,
                    calibration = bundle.calibration,
                    vadOk = true,
                )
                val topIndex = output.probabilities.indices.maxByOrNull { output.probabilities[it] }
                val topLabel = topIndex?.let { bundle.calibration.labels.getOrNull(it) }
                val topProbability = topIndex?.let { output.probabilities[it] }
                Log.i(
                    DIAGNOSTIC_TAG,
                    "model target=$targetId result=${outcome.developmentResult} reason=${outcome.reason} " +
                        "top=$topLabel topProbability=$topProbability " +
                        "targetProbability=${outcome.targetProbability} margin=${outcome.targetMargin} " +
                        "referenceSimilarity=${outcome.referenceSimilarity} index=${outcome.engineeringIndex}",
                )
                outcome
            } finally {
                waveform.fill(0f)
                normalizedSpeech.fill(0)
                activeSpeech.fill(0)
                detectedSpeech.fill(0)
            }
        } catch (_: Exception) {
            LocalWordOutcome(reason = "MODEL_UNAVAILABLE", developmentResult = "DEV_UNAVAILABLE")
        }
    }

    @Synchronized
    override fun close() {
        runCatching { vad.close() }
        runCatching { student.close() }
        runCatching { phoneme?.close() }
        runCatching { backbone?.close() }
        bundle.modelBytes.fill(0)
        bundle.vadBytes.fill(0)
        bundle.references.values.forEach { it.fill(0f) }
    }

    companion object {
        private const val DIAGNOSTIC_TAG = "VaakMitraCapture"

        fun create(context: Context, enabled: Boolean): MobileWordPracticeEngine {
            if (!enabled) throw MobileBundleException("mobile_engineering_path_disabled")
            return createEngine(context,false)
        }

        /** Public-fixture instrumentation only; the ordinary UI cannot enable unverified weights. */
        fun createForBackboneValidation(context:Context):MobileWordPracticeEngine {
            check(com.team96.speakeasy.BuildConfig.DEBUG)
            return createEngine(context,true,forcedCaptureProfile=BackboneCaptureProfile.LEGACY)
        }

        fun createForBackboneConservativeValidation(context:Context):MobileWordPracticeEngine {
            check(com.team96.speakeasy.BuildConfig.DEBUG)
            return createEngine(context,true,forcedCaptureProfile=BackboneCaptureProfile.CONSERVATIVE_V1)
        }

        fun createRetainedForComparison(context:Context):MobileWordPracticeEngine {
            check(com.team96.speakeasy.BuildConfig.DEBUG)
            return createEngine(context,false,true)
        }

        private fun createEngine(context:Context,allowCalibrationOnly:Boolean,forceLegacy:Boolean=false,
            forcedCaptureProfile:BackboneCaptureProfile?=null):MobileWordPracticeEngine {
            val bundle = AndroidMobileBundleLoader.load(context.applicationContext)
            var student: OnnxMobileWordStudent? = null
            var vad: OnnxSpeechVad? = null
            var phoneme: OnnxMobilePhoneme? = null
            var backbone: OnnxBackbonePhoneme? = null
            var captureProfile=BackboneCaptureProfile.LEGACY
            return try {
                student = OnnxMobileWordStudent(bundle.modelBytes)
                vad = OnnxSpeechVad(bundle.vadBytes, bundle.manifest.vad)
                val hasBackbone=context.assets.list(OnnxBackbonePhoneme.ROOT)?.contains("bundle.json")==true
                if(hasBackbone && !forceLegacy) {
                    val header=org.json.JSONObject(context.assets.open("${OnnxBackbonePhoneme.ROOT}/bundle.json").bufferedReader().use{it.readText()})
                    val fields=header.keys().asSequence().associateWith{key->
                        val value=header.get(key)
                        if(value is org.json.JSONObject)value.keys().asSequence().associateWith{value.get(it)} else value
                    }
                    val contract=BackboneBundleContract.parse(fields,allowCalibrationOnly=true)
                    captureProfile=forcedCaptureProfile?:contract.captureProfile
                    if(allowCalibrationOnly || contract.nativeVerified)backbone=OnnxBackbonePhoneme(context,allowCalibrationOnly)
                }
                if(allowCalibrationOnly)checkNotNull(backbone)
                val hasPhoneme = context.assets.list(OnnxMobilePhoneme.ROOT)?.contains("bundle.json") == true
                if (backbone==null && hasPhoneme) phoneme = OnnxMobilePhoneme(context)
                MobileWordPracticeEngine(bundle, checkNotNull(student), checkNotNull(vad), phoneme,backbone,loadPracticePhones(context),captureProfile)
            } catch (error: Exception) {
                runCatching { vad?.close() }
                runCatching { phoneme?.close() }
                runCatching { backbone?.close() }
                runCatching { student?.close() }
                bundle.modelBytes.fill(0)
                bundle.vadBytes.fill(0)
                throw MobileBundleException("mobile_engine_initialization_failed:${error.message}")
            }
        }

        internal fun loadPracticePhones(context:Context):Map<String,List<String>> = runCatching {
            val root="vaakmitra/practice-words-v1"
            val manifest=org.json.JSONObject(context.assets.open("$root/bundle.json").bufferedReader().use{it.readText()})
            require(manifest.getString("schema")=="practice-reference-bundle-v1" && manifest.get("production_ready")==false && manifest.get("approved_for_child_scoring")==false)
            require(manifest.getString("references_file")=="references.json")
            val bytes=context.assets.open("$root/references.json").use{it.readBytes()}
            try {
                PhonemeCtcDecoder.verifySha(bytes,manifest.getString("references_sha256"))
                val document=org.json.JSONObject(String(bytes,Charsets.UTF_8));require(document.getString("schema")=="provisional-practice-phonemes-v1")
                val expected=document.getJSONObject("expected")
                expected.keys().asSequence().associateWith{id->val array=expected.getJSONArray(id);List(array.length()){array.getString(it)}}
            } finally {bytes.fill(0)}
        }.getOrDefault(emptyMap())

        private fun captureProblem(targetId: String, samples: ShortArray, sampleRate: Int): String? {
            if (targetId.isBlank() || targetId == "OTHER") return "TARGET_UNAVAILABLE"
            if (sampleRate != 16_000) return "UNSUPPORTED_SAMPLE_RATE"
            if (samples.size < 4_800) return "TOO_SHORT"
            if (samples.size > 128_000) return "TOO_LONG"
            if (PcmCaptureEvidence.analyze(samples).isSilent) return "NO_SPEECH"
            if (samples.count { abs(it.toInt()) >= 32_734 } > samples.size / 100) return "CLIPPED"
            return null
        }
    }
}
