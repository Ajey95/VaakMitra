package com.team96.speakeasy.audio

import kotlin.math.abs
import kotlin.math.sqrt

/** DEC-028/MST-009: privacy-safe capture telemetry; no PCM is retained or persisted. */
data class PcmCaptureEvidence(
    val sampleCount: Int,
    val peakAbsolute: Int,
    val rms: Double,
    val nonZeroRatio: Double,
) {
    val isSilent: Boolean
        get() = sampleCount == 0 || (peakAbsolute < 32 && rms < 16.0)

    companion object {
        fun analyze(samples: ShortArray): PcmCaptureEvidence {
            if (samples.isEmpty()) return PcmCaptureEvidence(0, 0, 0.0, 0.0)
            var peak = 0
            var nonZero = 0
            var squareSum = 0.0
            samples.forEach { sample ->
                val value = sample.toInt()
                val magnitude = abs(value)
                if (magnitude > peak) peak = magnitude
                if (value != 0) nonZero += 1
                squareSum += value.toDouble() * value.toDouble()
            }
            return PcmCaptureEvidence(
                sampleCount = samples.size,
                peakAbsolute = peak,
                rms = sqrt(squareSum / samples.size),
                nonZeroRatio = nonZero.toDouble() / samples.size,
            )
        }
    }
}

/** DEC-028/MST-009: exposes why the frozen Silero gate accepted or rejected a capture. */
data class SpeechVadEvidence(
    val maximumProbability: Float,
    val speechSamples: Int,
    val sampleRate: Int,
    val threshold: Double,
    val minimumSpeechMs: Int,
    val firstSpeechSample: Int? = null,
    val lastSpeechSampleExclusive: Int? = null,
) {
    val speechMilliseconds: Long
        get() = speechSamples * 1_000L / sampleRate

    val hasEnoughSpeech: Boolean
        get() = speechMilliseconds >= minimumSpeechMs

    fun extractSpeech(samples: ShortArray, paddingSamples: Int = sampleRate / 10): ShortArray {
        val first = firstSpeechSample ?: return ShortArray(0)
        val last = lastSpeechSampleExclusive ?: return ShortArray(0)
        val start = (first - paddingSamples).coerceAtLeast(0)
        val end = (last + paddingSamples).coerceAtMost(samples.size)
        return if (start < end) samples.copyOfRange(start, end) else ShortArray(0)
    }
}
