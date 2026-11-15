package com.team96.speakeasy.audio

import org.junit.Assert.assertEquals
import org.junit.Test

class SileroVadInputWindowTest {
    @Test fun prv001OwnedWindowErasedWhenInferenceThrows() {
        val window = SileroVadInputWindow()
        var held = floatArrayOf()
        val failure = runCatching {
            window.withNext(ShortArray(512) { 16384 }, 0, 512) { values ->
                held = values
                throw IllegalStateException("controlled failure")
            }
        }.exceptionOrNull()
        org.junit.Assert.assertTrue(failure is IllegalStateException)
        org.junit.Assert.assertEquals(576, held.size)
        org.junit.Assert.assertTrue(held.all { it == 0f })
        window.clear()
    }

    @Test fun mst009FirstSileroWindowPrefixes64ContextSamples() {
        val window = SileroVadInputWindow()
        val pcm = ShortArray(512) { 16_384 }

        val input = window.next(pcm, offset = 0, count = pcm.size)

        assertEquals(576, input.size)
        repeat(64) { assertEquals(0f, input[it], 0f) }
        repeat(512) { assertEquals(0.5f, input[64 + it], 0f) }
    }

    @Test fun mst009NextSileroWindowCarriesOnlyPrevious64SampleContext() {
        val window = SileroVadInputWindow()
        val first = ShortArray(512) { index -> if (index >= 448) 8_192 else 0 }
        window.next(first, offset = 0, count = first.size)

        val second = window.next(ShortArray(512), offset = 0, count = 512)

        repeat(64) { assertEquals(0.25f, second[it], 0f) }
        repeat(512) { assertEquals(0f, second[64 + it], 0f) }
    }

    @Test fun mst009FinalPartialWindowPadsBeforeUpdatingContext() {
        val window = SileroVadInputWindow()

        val input = window.next(ShortArray(20) { 3_276 }, offset = 0, count = 20)
        val following = window.next(ShortArray(512), offset = 0, count = 512)

        assertEquals(3_276f / 32_768f, input[64], 0f)
        repeat(64) { assertEquals(0f, following[it], 0f) }
    }
}
