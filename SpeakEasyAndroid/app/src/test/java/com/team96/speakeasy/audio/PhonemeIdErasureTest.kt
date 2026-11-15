package com.team96.speakeasy.audio
import org.junit.Assert.*
import org.junit.Test

/** DEC-051/PHN004: erase owned wrapper IDs even when token lookup fails. */
class PhonemeIdErasureTest {
    @Test fun idsAreErasedAfterSuccessfulLookup() {
        val ids = intArrayOf(1, 2)
        assertEquals(listOf("a", "m"), OnnxMobilePhoneme.tokensAndErase(ids, listOf("blank", "a", "m")))
        assertTrue(ids.all { it == 0 })
    }
    @Test fun idsAreErasedAfterFailedLookup() {
        val ids = intArrayOf(1, 9)
        assertTrue(runCatching { OnnxMobilePhoneme.tokensAndErase(ids, listOf("blank", "a")) }.isFailure)
        assertTrue(ids.all { it == 0 })
    }
}
