package com.team96.speakeasy.audio

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer
import java.nio.LongBuffer

/** DEC-028/MST-008: Silero VAD gates inference; unavailable VAD never falls back to energy. */
class OnnxSpeechVad(modelBytes: ByteArray, private val configuration: MobileVadConfiguration) : AutoCloseable {
    private val environment = OrtEnvironment.getEnvironment()
    private val options = OrtSession.SessionOptions().apply {
        setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
        setIntraOpNumThreads(1)
        setInterOpNumThreads(1)
    }
    private val session = environment.createSession(modelBytes, options)

    init {
        require(session.inputNames.containsAll(setOf("input", "state", "sr"))) { "vad_input_contract_invalid" }
        require(session.outputNames.containsAll(setOf("output", "stateN"))) { "vad_output_contract_invalid" }
    }

    fun hasEnoughSpeech(samples: ShortArray, sampleRate: Int = 16_000): Boolean =
        analyze(samples, sampleRate).hasEnoughSpeech

    fun analyze(samples: ShortArray, sampleRate: Int = 16_000): SpeechVadEvidence {
        require(sampleRate == 16_000) { "vad_sample_rate_invalid" }
        val chunkSize = 512
        var state = FloatArray(2 * 1 * 128)
        var speechSamples = 0
        var maximumProbability = 0f
        var firstSpeechSample: Int? = null
        var lastSpeechSampleExclusive: Int? = null
        var gapSamples = 0
        var inSpeech = false
        var offset = 0
        val inputWindow = SileroVadInputWindow()
        try {
            while (offset < samples.size) {
                val count = minOf(chunkSize, samples.size - offset)
                val (probability, nextState) = inputWindow.withNext(samples, offset, count) { values ->
                    OnnxTensor.createTensor(environment, FloatBuffer.wrap(values), longArrayOf(1, values.size.toLong())).use { input ->
                        OnnxTensor.createTensor(environment, FloatBuffer.wrap(state), longArrayOf(2, 1, 128)).use { stateTensor ->
                            OnnxTensor.createTensor(environment, LongBuffer.wrap(longArrayOf(sampleRate.toLong())), longArrayOf()).use { sr ->
                                session.run(mapOf("input" to input, "state" to stateTensor, "sr" to sr)).use { result ->
                                    val probability = ((required(result, "output").value as Array<FloatArray>)[0][0])
                                    probability to flattenState(required(result, "stateN").value)
                                }
                            }
                        }
                    }
                }
                state.fill(0f)
                state = nextState
                if (probability.isFinite()) maximumProbability = maxOf(maximumProbability, probability)
                if (probability.isFinite() && probability >= configuration.threshold) {
                    if (firstSpeechSample == null) firstSpeechSample = offset
                    lastSpeechSampleExclusive = offset + count
                    if (inSpeech && gapSamples <= configuration.mergeToleranceMs * sampleRate / 1_000) {
                        gapSamples = 0
                    }
                    inSpeech = true
                    speechSamples += count
                } else if (inSpeech) {
                    gapSamples += count
                    if (gapSamples > configuration.mergeToleranceMs * sampleRate / 1_000) {
                        inSpeech = false
                        gapSamples = 0
                    }
                }
                offset += count
            }
            return SpeechVadEvidence(
                maximumProbability = maximumProbability,
                speechSamples = speechSamples,
                sampleRate = sampleRate,
                threshold = configuration.threshold,
                minimumSpeechMs = configuration.minimumSpeechMs,
                firstSpeechSample = firstSpeechSample,
                lastSpeechSampleExclusive = lastSpeechSampleExclusive,
            )
        } finally {
            state.fill(0f)
            inputWindow.clear()
        }
    }

    override fun close() {
        session.close()
        options.close()
    }

    private fun flattenState(value: Any): FloatArray {
        @Suppress("UNCHECKED_CAST")
        val state = value as? Array<Array<FloatArray>> ?: throw MobileBundleException("vad_state_shape_invalid")
        return state.flatMap { batch -> batch.flatMap { it.asIterable() } }.toFloatArray()
    }

    private fun required(result: OrtSession.Result, name: String): ai.onnxruntime.OnnxValue {
        val value = result.get(name)
        return if (value.isPresent) value.get() else throw MobileBundleException("vad_output_missing:$name")
    }
}
