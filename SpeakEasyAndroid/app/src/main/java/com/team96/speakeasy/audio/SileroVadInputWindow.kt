package com.team96.speakeasy.audio

/**
 * DEC-028/MST-009: Silero v5 at 16 kHz requires 64 prior samples followed by
 * the current 512-sample chunk. The recurrent state alone is not the full context.
 */
class SileroVadInputWindow {
    private val context = FloatArray(64)

    fun next(samples: ShortArray, offset: Int, count: Int): FloatArray {
        require(offset >= 0 && count >= 0 && offset + count <= samples.size)
        require(count <= 512)
        val input = FloatArray(576)
        context.copyInto(input, destinationOffset = 0)
        repeat(count) { index ->
            input[64 + index] = samples[offset + index].toFloat() / 32768f
        }
        input.copyInto(context, startIndex = input.size - context.size)
        return input
    }

    /** DEC-051: the caller may borrow this owned waveform only inside the block. */
    fun <T> withNext(samples: ShortArray, offset: Int, count: Int, block: (FloatArray) -> T): T {
        val values = next(samples, offset, count)
        return try { block(values) } finally { values.fill(0f) }
    }

    fun clear() = context.fill(0f)
}
