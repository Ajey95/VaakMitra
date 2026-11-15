package com.team96.speakeasy.audio

/** AU-003/PRV-001: fixed-capacity capture; the backing array is cleared after use. */
class BoundedPcmBuffer(private val maxSamples: Int = 128000) {
    init { require(maxSamples > 0) }

    private val values = ShortArray(maxSamples)
    private var length = 0

    val isFull: Boolean
        @Synchronized get() = length == maxSamples

    @Synchronized
    fun append(samples: ShortArray, count: Int): Int {
        require(count in 0..samples.size)
        val accepted = minOf(count, maxSamples - length)
        samples.copyInto(values, destinationOffset = length, endIndex = accepted)
        length += accepted
        return accepted
    }

    @Synchronized
    fun takeAndClear(): ShortArray {
        val result = values.copyOf(length)
        values.fill(0, 0, length)
        length = 0
        return result
    }

    @Synchronized
    fun clear() {
        values.fill(0, 0, length)
        length = 0
    }
}
