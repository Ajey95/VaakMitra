package com.team96.speakeasy.journey

import org.junit.Assert.*
import org.junit.Test

class WordLearningWritesTest {
    @Test fun dec059FailedCommitNeverAcknowledgesOrLeaksDirtyProgressToAnotherReader() {
        var succeeds=false;var owner=true
        val writer=ConfirmedWordLearningWrites(emptyMap(),{succeeds},{owner})
        val options=listOf("TA_WORD_0001","TA_WORD_0002")
        assertFalse(writer.choose("TA_WORD_0001","TA_WORD_0001",options,2))
        assertTrue(writer.load().isEmpty())
        succeeds=true
        assertTrue(writer.choose("TA_WORD_0001","TA_WORD_0001",options,2))
        assertEquals(1,writer.load()["TA_WORD_0001"]!!.matches)
        owner=false
        assertTrue(writer.load().isEmpty())
        assertFalse(writer.help("TA_WORD_0001",2))
    }
    @Test fun dec059WordRecordsNeverContainAudioPhonesOrFreeTextAndRejectUnknownIds() {
        var saved=""
        val writer=ConfirmedWordLearningWrites(emptyMap(),{saved=WordProgressCodec.encode(it);true},{true})
        assertFalse(writer.help("OTHER",1))
        assertTrue(writer.help("TA_WORD_0101",1))
        assertTrue(saved.startsWith("word-learning-2\nTA_WORD_0101|"))
        assertFalse(saved.contains("என்ன"));assertFalse(saved.contains("phoneme"))
    }
}
