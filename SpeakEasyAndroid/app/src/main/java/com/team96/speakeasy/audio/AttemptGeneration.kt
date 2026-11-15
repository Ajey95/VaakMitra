package com.team96.speakeasy.audio

/** MST-008/UX-003: stale inference cannot publish after a cancellation boundary. */
class AttemptGeneration {
    private var value = 0L

    @Synchronized fun next(): Long = ++value
    @Synchronized fun invalidate() { value += 1 }
    @Synchronized fun isCurrent(candidate: Long): Boolean = candidate == value
}

