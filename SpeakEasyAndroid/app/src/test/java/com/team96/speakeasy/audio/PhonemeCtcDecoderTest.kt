package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test

class PhonemeCtcDecoderTest {
    // PHN-003: only an absent field is a legacy artifact; declared values are exact.
    @Test fun legacyFrameShiftDefaultAppliesOnlyWhenAbsent() {
        assertEquals(40, PhonemeAudio.frameShift(false, null))
        assertEquals(40, PhonemeAudio.frameShift(true, 40))
        assertEquals(20, PhonemeAudio.frameShift(true, 20L))
    }
    @Test fun rejectsMalformedDeclaredFrameShiftsWithoutCoercion() {
        val invalid = listOf<Any?>(null, "40", "bad", 40.0, 40.5, true, 30, (1L shl 32) + 40)
        invalid.forEach { value ->
            var rejected = false
            try { PhonemeAudio.frameShift(true, value) } catch (_: IllegalArgumentException) { rejected = true }
            assertTrue("Declared frame value must be rejected: $value", rejected)
        }
    }
    @Test fun integerContractRejectsFractionalCountsAndOverflow() {
        assertEquals(75, PhonemeAudio.exactInteger(75L))
        listOf<Any?>("75", 75.5, Long.MAX_VALUE, null).forEach { value ->
            var rejected = false
            try { PhonemeAudio.exactInteger(value) } catch (_: IllegalArgumentException) { rejected = true }
            assertTrue("Integer contract must reject: $value", rejected)
        }
    }
    // PHN-003/DEC-032: graph output must agree with the bounded manifest contract.
    @Test fun acceptsOnlyMatchingSupportedFrameContracts() {
        assertEquals(75, PhonemeAudio.validateOutputFrames(40, 75))
        assertEquals(150, PhonemeAudio.validateOutputFrames(20, 150))
    }
    @Test(expected = IllegalArgumentException::class) fun rejectsFrameMetadataMismatch() {
        PhonemeAudio.validateOutputFrames(40, 150)
    }
    @Test(expected = IllegalArgumentException::class) fun rejectsUnsupportedFrameShift() {
        PhonemeAudio.validateOutputFrames(30, 100)
    }
    @Test fun preservesRepeatedPhonesSeparatedByBlank() {
        val path = intArrayOf(0, 1, 1, 0, 1, 2, 2, 0)
        val frames = path.map { t -> FloatArray(3) { if (it == t) 2f else -2f } }.toTypedArray()
        assertArrayEquals(intArrayOf(1, 1, 2), PhonemeCtcDecoder.decode(frames, 3))
    }
    @Test fun emptyAndAllBlankRemainEmpty() {
        assertArrayEquals(intArrayOf(), PhonemeCtcDecoder.decode(emptyArray(), 3))
        assertArrayEquals(intArrayOf(), PhonemeCtcDecoder.decode(arrayOf(floatArrayOf(1f, 0f)), 2))
    }
    @Test(expected = IllegalArgumentException::class) fun rejectsNonfiniteOutput() {
        PhonemeCtcDecoder.decode(arrayOf(floatArrayOf(Float.NaN, 0f)), 2)
    }
    @Test fun waveformPreservesActualDuration() {
        val result = PhonemeAudio.prepare(ShortArray(16000) { 8192 })
        assertEquals(48000, result.size)
        assertEquals(16000, result.count { it != 0f })
        assertEquals(.25f, result[16000], 0f)
    }
    @Test(expected = IllegalArgumentException::class) fun rejectsTruncation() {
        PhonemeAudio.prepare(ShortArray(48001))
    }
}
