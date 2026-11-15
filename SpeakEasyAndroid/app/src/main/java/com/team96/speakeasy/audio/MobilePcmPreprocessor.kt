package com.team96.speakeasy.audio

import kotlin.math.max
import kotlin.math.roundToInt
import kotlin.math.sqrt

/** DEC-028/MST-001: exact Python-parity PCM16 conversion, pad and crop. */
object MobilePcmPreprocessor {
    /** MST-016: remove only low-energy room tail outside the active word. */
    fun trimActiveWord(samples: ShortArray, sampleRate: Int = 16_000): ShortArray {
        require(sampleRate > 0) { "sampleRate must be positive" }
        if (samples.isEmpty()) return ShortArray(0)
        val frameSize = max(1, sampleRate / 50) // 20 ms
        val frameCount = (samples.size + frameSize - 1) / frameSize
        val rms = DoubleArray(frameCount)
        for (frame in 0 until frameCount) {
            val start = frame * frameSize
            val end = minOf(samples.size, start + frameSize)
            var squareSum = 0.0
            for (index in start until end) {
                val value = samples[index].toDouble()
                squareSum += value * value
            }
            rms[frame] = sqrt(squareSum / max(1, end - start))
        }
        val threshold = max(64.0, (rms.maxOrNull() ?: 0.0) * 0.08)
        val first = rms.indexOfFirst { it >= threshold }
        val last = rms.indexOfLast { it >= threshold }
        if (first < 0 || last < first) return ShortArray(0)
        val margin = sampleRate * 60 / 1_000
        val start = (first * frameSize - margin).coerceAtLeast(0)
        val end = ((last + 1) * frameSize + margin).coerceAtMost(samples.size)
        return if (end - start >= sampleRate / 5) samples.copyOfRange(start, end) else ShortArray(0)
    }

    /** MST-017: normalize speaking rate to the target's bound reference duration. */
    fun normalizeDuration(samples: ShortArray, targetLength: Int): ShortArray {
        require(samples.isNotEmpty()) { "samples must not be empty" }
        require(targetLength > 0) { "targetLength must be positive" }
        if (samples.size == targetLength) return samples.copyOf()
        if (targetLength == 1) return shortArrayOf(samples.first())
        val output = ShortArray(targetLength)
        val scale = (samples.size - 1).toDouble() / (targetLength - 1).toDouble()
        for (index in output.indices) {
            val position = index * scale
            val left = position.toInt().coerceIn(0, samples.lastIndex)
            val right = (left + 1).coerceAtMost(samples.lastIndex)
            val fraction = position - left
            output[index] = (samples[left] * (1.0 - fraction) + samples[right] * fraction)
                .roundToInt().coerceIn(Short.MIN_VALUE.toInt(), Short.MAX_VALUE.toInt()).toShort()
        }
        return output
    }

    fun prepare(samples: ShortArray, length: Int = 32_000): FloatArray {
        require(length > 0) { "length must be positive" }
        val result = FloatArray(length)
        val sourceOffset = if (samples.size > length) (samples.size - length) / 2 else 0
        val count = minOf(samples.size, length)
        val destinationOffset = if (samples.size < length) (length - samples.size) / 2 else 0
        repeat(count) { index ->
            result[destinationOffset + index] = samples[sourceOffset + index].toFloat() / 32768f
        }
        return result
    }
}
