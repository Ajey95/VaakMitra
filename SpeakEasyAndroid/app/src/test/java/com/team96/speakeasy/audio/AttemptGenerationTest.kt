package com.team96.speakeasy.audio

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

/** MST-008/UX-003: Break, Stop and a new attempt invalidate stale inference. */
class AttemptGenerationTest {
    @Test fun mst008OnlyLatestGenerationMayPublish() {
        val guard = AttemptGeneration()
        val first = guard.next()
        assertTrue(guard.isCurrent(first))
        guard.invalidate()
        assertFalse(guard.isCurrent(first))
        val second = guard.next()
        assertTrue(guard.isCurrent(second))
        assertFalse(guard.isCurrent(first))
    }
}

