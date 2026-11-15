package com.team96.speakeasy.audio

import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Test

class BoundedPcmBufferTest {
    @Test fun au003CaptureStopsAtItsSampleCap() {
        val buffer = BoundedPcmBuffer(maxSamples = 5)
        assertEquals(3, buffer.append(shortArrayOf(1, 2, 3), 3))
        assertEquals(2, buffer.append(shortArrayOf(4, 5, 6), 3))
        assertArrayEquals(shortArrayOf(1, 2, 3, 4, 5), buffer.takeAndClear())
    }

    @Test fun prv001TakingCaptureClearsPriorSamples() {
        val buffer = BoundedPcmBuffer(maxSamples = 4)
        buffer.append(shortArrayOf(7, 8), 2)
        assertArrayEquals(shortArrayOf(7, 8), buffer.takeAndClear())
        assertArrayEquals(shortArrayOf(), buffer.takeAndClear())
        buffer.append(shortArrayOf(3), 1)
        assertArrayEquals(shortArrayOf(3), buffer.takeAndClear())
    }

    @Test(expected = IllegalArgumentException::class)
    fun au003RejectsCountBeyondInputLength() {
        BoundedPcmBuffer(maxSamples = 4).append(shortArrayOf(1), 2)
    }
}
