package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test

/** DEC069/PHN010: these fixtures check interaction policy, never acoustic/child accuracy. */
class OptionalSoundPracticeTest {
    private val known=setOf("a","aː","m","p","k","n","u","t͡ʃ","s","eː","ɾ","n̪","t̪")
    private fun evidence(id:String,heard:List<String>,reference:List<String>)=
        SoundPracticePolicy.evidence(id,heard,reference,known)

    @Test fun phn010NormalGeminationAndLongVowelsArePreserved() {
        assertTrue(evidence("TA_WORD_0001",listOf("a","m","m","aː"),listOf("a","m","m","aː"))!!.sequenceAgrees)
        assertEquals(setOf("m"),evidence("TA_WORD_0001",listOf("a","m","aː"),listOf("a","m","m","aː"))!!.possibleSounds)
        assertEquals(setOf("aː"),evidence("TA_WORD_0083",listOf("a","m"),listOf("aː","m"))!!.possibleSounds)
    }
    @Test fun phn010AmbiguousTargetsUnsupportedInsertionsAndInvalidEvidenceAbstain() {
        assertNull(evidence("TA_WORD_0001",listOf("a","a"),listOf("a","m","p","a")))
        assertNull(evidence("TA_WORD_0001",listOf("a","k","m","aː"),listOf("a","m","aː")))
        assertNull(evidence("TA_WORD_0001",emptyList(),listOf("a","m")))
        assertNull(evidence("TA_WORD_0001",listOf("[UNK]"),listOf("a","m")))
        assertNull(evidence("TA_LETTER_UYIR_01",listOf("a"),listOf("a")))
        assertNull(evidence("TA_WORD_0001",List(65){"a"},listOf("a","m")))
    }
    @Test fun phn010WholeWordSoftSVariantDoesNotNormalizeOtherWords() {
        val reference=listOf("t͡ʃ","eː","ɾ","n̪","t̪","u")
        assertTrue(evidence("TA_WORD_0100",listOf("s","eː","ɾ","n̪","t̪","u"),reference)!!.sequenceAgrees)
        assertFalse(evidence("TA_WORD_0001",listOf("s","a"),listOf("t͡ʃ","a"))?.sequenceAgrees==true)
    }
    @Test fun phn010SuggestionNeedsThreeAttemptsAcrossTwoWords() {
        val state=SoundPracticeTracker()
        repeat(3){state.record(SoundPracticeEvidence("TA_WORD_0001",setOf("m")))}
        assertNull(state.prioritizedSound())
        state.record(SoundPracticeEvidence("TA_WORD_0083",setOf("m")))
        assertEquals("m",state.prioritizedSound()?.token)
        assertEquals("ம்",state.prioritizedSound()?.sound)
    }
    @Test fun phn010AgreementClearsTentativeWordPatternWithoutMastery() {
        val state=SoundPracticeTracker()
        state.record(SoundPracticeEvidence("TA_WORD_0001",setOf("m")))
        repeat(2){state.record(SoundPracticeEvidence("TA_WORD_0083",setOf("m")))}
        assertNotNull(state.prioritizedSound())
        state.record(SoundPracticeEvidence("TA_WORD_0001",emptySet(),sequenceAgrees=true))
        assertNull(state.prioritizedSound())
        state.clear();assertNull(state.prioritizedSound())
    }
    @Test fun phn010HistoryBoundStopsOldPatternsFollowingNewActivities() {
        val state=SoundPracticeTracker()
        state.record(SoundPracticeEvidence("TA_WORD_0001",setOf("m")))
        repeat(2){state.record(SoundPracticeEvidence("TA_WORD_0083",setOf("m")))}
        repeat(24){state.record(SoundPracticeEvidence("TA_WORD_0002",setOf("p")))}
        assertNull(state.prioritizedSound())
    }
    @Test fun phn010UnclearAttemptsAlsoAgeOutOldSuggestions() {
        val state=SoundPracticeTracker()
        state.record(SoundPracticeEvidence("TA_WORD_0001",setOf("m")))
        repeat(2){state.record(SoundPracticeEvidence("TA_WORD_0083",setOf("m")))}
        repeat(24){state.record(null)}
        assertNull(state.prioritizedSound())
    }
    @Test fun phn010ClearingAWordDoesNotExtendOtherPatternsHistoryWindow() {
        val state=SoundPracticeTracker()
        state.record(SoundPracticeEvidence("TA_WORD_0002",setOf("p")))
        state.record(SoundPracticeEvidence("TA_WORD_0050",setOf("p")))
        state.record(SoundPracticeEvidence("TA_WORD_0002",setOf("p")))
        state.record(SoundPracticeEvidence("TA_WORD_0001",setOf("m")))
        state.record(SoundPracticeEvidence("TA_WORD_0083",setOf("m")))
        state.record(SoundPracticeEvidence("TA_WORD_0001",emptySet(),sequenceAgrees=true))
        repeat(19){state.record(null)}
        assertNull(state.prioritizedSound())
    }
    @Test fun phn010RelatedWordNeverLeavesForwardApprovedItinerary() {
        assertEquals(13,SoundPracticePolicy.relatedLesson(1,false,setOf("TA_WORD_0083","TA_WORD_0001")))
        assertNull(SoundPracticePolicy.relatedLesson(13,true,setOf("TA_WORD_0001","TA_WORD_0083","other")))
        assertNull(SoundPracticePolicy.relatedLesson(25,false,setOf("TA_WORD_0001")))
    }
    @Test fun phn010GenericExplorationUsesOnlySoundsInTheCurrentReference() {
        assertEquals("m",SoundPracticeCatalog.forWord(listOf("a","m","m","aː"))?.token)
        assertNull(SoundPracticeCatalog.forWord(listOf("[UNK]")))
        assertEquals(listOf("ம்","மா","அம்மா"),SoundPracticeCatalog.steps(SoundPracticeCatalog.find("m")!!,"TA_WORD_0001"))
        assertTrue(SoundPracticeCatalog.steps(SoundPracticeCatalog.find("m")!!,"not-approved").isEmpty())
    }
}

