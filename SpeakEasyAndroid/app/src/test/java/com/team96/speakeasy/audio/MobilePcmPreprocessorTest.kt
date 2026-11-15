package com.team96.speakeasy.audio

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

/** DEC-028/MST-001: Kotlin preprocessing must match the Python golden literals. */
class MobilePcmPreprocessorTest {
    @Test fun mst001SymmetricPadMatchesPythonGoldenVector() {
        val result = MobilePcmPreprocessor.prepare(shortArrayOf(Short.MIN_VALUE, 0, 16384), length = 7)
        assertArrayEquals(floatArrayOf(0f, 0f, -1f, 0f, .5f, 0f, 0f), result, 0f)
    }

    @Test fun mst001CenterCropMatchesPythonGoldenVector() {
        val input = ShortArray(9) { it.toShort() }
        val result = MobilePcmPreprocessor.prepare(input, length = 5)
        assertArrayEquals(floatArrayOf(2f / 32768f, 3f / 32768f, 4f / 32768f, 5f / 32768f, 6f / 32768f), result, 0f)
    }

    @Test fun mst016ActiveEnvelopeRemovesLowEnergyRoomTailWithFixedMargins() {
        val samples = ShortArray(6_400) { 20 }
        for (index in 1_600 until 4_800) {
            samples[index] = if (index % 2 == 0) 2_000 else -2_000
        }

        val trimmed = MobilePcmPreprocessor.trimActiveWord(samples, sampleRate = 16_000)

        assertEquals(5_120, trimmed.size)
        assertEquals(20, trimmed.first().toInt())
        assertEquals(20, trimmed.last().toInt())
        assertEquals(2_000, trimmed[960].toInt())
    }

    @Test fun mst016SilentEnvelopeReturnsEmptyInsteadOfInventingSpeech() {
        assertEquals(0, MobilePcmPreprocessor.trimActiveWord(ShortArray(3_200) { 12 }).size)
    }

    @Test fun mst017TargetDurationNormalizationUsesDeterministicLinearInterpolation() {
        val normalized = MobilePcmPreprocessor.normalizeDuration(
            shortArrayOf(0, 1_000, 2_000, 3_000),
            targetLength = 7,
        )
        assertArrayEquals(shortArrayOf(0, 500, 1_000, 1_500, 2_000, 2_500, 3_000), normalized)
    }
}
