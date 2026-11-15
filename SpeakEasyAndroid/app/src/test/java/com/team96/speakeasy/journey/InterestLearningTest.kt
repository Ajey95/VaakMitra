package com.team96.speakeasy.journey

import org.junit.Assert.*
import org.junit.Test

/** DEC059/ILR001..010: on-device activity evidence never becomes pronunciation mastery. */
class InterestLearningTest {
    @Test fun saturatedCountersStillRestoreGuidanceAfterAnIncorrectPicture() {
        val p=PictureProgress(choices=10000,matches=10000,noExtraHintMatches=9996,help=PromptHelp.YOUR_TURN)
        val wrong=p.answer(false,2)
        assertEquals(PromptHelp.GUIDED,wrong.help)
        assertEquals(10000,wrong.choices)
    }
    @Test fun earlierDayPicturePracticeCanBeScheduledAgainWithinTheRemainingWindow() {
        val today=java.time.LocalDate.now().toEpochDay()
        val history=mapOf("TA_WORD_0001" to PictureProgress().answer(true,today),"TA_WORD_0083" to PictureProgress().answer(true,today-1))
        assertEquals(13,adaptiveWordLessonId(1,true,history))
        assertNull(adaptiveWordLessonId(25,true,history))
    }
    @Test fun themesRecognizePresetsWithoutGeneratingPromptsFromFreeText() {
        assertEquals(InterestTheme.TRAINS, InterestTheme.fromInterest("trains"))
        assertEquals(InterestTheme.TRAINS, InterestTheme.fromInterest("ரயில்"))
        assertEquals(InterestTheme.ANIMALS, InterestTheme.fromInterest("Animals"))
        assertEquals(InterestTheme.STORIES, InterestTheme.fromInterest("stories"))
        assertEquals(InterestTheme.NEUTRAL, InterestTheme.fromInterest("some unrecognized private interest"))
    }
    @Test fun twoPictureMatchesTrialOneLessHintAndOnlyHintFreeMatchesHaveTheirOwnCounter() {
        var p=PictureProgress()
        assertEquals(PromptHelp.GUIDED,p.help)
        p=p.answer(true,10).answer(true,10)
        assertEquals(PromptHelp.CUE,p.help)
        assertEquals(0,p.noExtraHintMatches)
        p=p.answer(true,10).answer(true,10)
        assertEquals(PromptHelp.YOUR_TURN,p.help)
        assertEquals(0,p.noExtraHintMatches)
        p=p.answer(true,10)
        assertEquals(1,p.noExtraHintMatches)
        assertEquals(5,p.matches)
        assertEquals(3,p.optionCount)
    }
    @Test fun helpAndMismatchImmediatelyRestoreGuidanceWithoutErasingHistory() {
        val p=PictureProgress().answer(true,1).answer(true,1).answer(true,1).answer(true,1).answer(true,1)
        val help=p.requestedHelp(2)
        assertEquals(PromptHelp.GUIDED,help.help);assertEquals(1,help.helps)
        assertEquals(1,help.noExtraHintMatches);assertEquals(2,help.optionCount)
        val wrong=p.answer(false,2).answer(false,2)
        assertEquals(PromptHelp.GUIDED,wrong.help);assertTrue(wrong.needsBreak)
        assertEquals(5,wrong.matches);assertEquals(7,wrong.choices)
    }
    @Test fun onlyKnownVisiblePictureChoicesCanAffectTheActivity() {
        val options=listOf("TA_WORD_0001","TA_WORD_0002")
        val result=pictureSelection("TA_WORD_0001","TA_WORD_0002",options,PictureProgress(),1)
        assertFalse(result.matched);assertEquals(1,result.progress.choices)
        for(selected in listOf("TA_WORD_9999","OTHER","a m m a")) {
            assertThrows(IllegalArgumentException::class.java){pictureSelection("TA_WORD_0001",selected,options,PictureProgress(),1)}
        }
    }
    @Test fun targetPositionChangesAndEveryChoiceBelongsToTheInstalledCatalogue() {
        val positions=(0..5).map { turn ->
            val choices=learningOptions("TA_WORD_0001",3,turn)
            assertEquals(3,choices.distinct().size)
            assertTrue(choices.all{id->StarterWords.all.any{it.id==id}})
            choices.indexOf("TA_WORD_0001")
        }
        assertEquals(setOf(0,1,2),positions.toSet())
        assertThrows(IllegalArgumentException::class.java){learningOptions("unknown",3,0)}
    }
    @Test fun emptyHistoryPreservesOldRoutesAndTheFinalWordNeverWraps() {
        assertEquals(13,adaptiveWordLessonId(2,true,emptyMap()))
        assertEquals(3,adaptiveWordLessonId(2,false,emptyMap()))
        assertNull(adaptiveWordLessonId(25,true,emptyMap()))
        assertNull(adaptiveWordLessonId(0,true,emptyMap()))
    }
    @Test fun strugglingPictureTaskMayRecommendAnEasierRemainingItemOnly() {
        val p=PictureProgress().answer(false,1)
        val next=adaptiveWordLessonId(13,true,mapOf("TA_WORD_0083" to p))!!
        val remaining=StarterWords.focusedLessonIds.dropWhile{it!=13}.drop(1)
        assertTrue(next in remaining)
        assertTrue(StarterWords.byNumericLessonId(next)!!.difficulty<=2)
        assertFalse(next==13)
    }
    @Test fun writingPartsPreserveAll25TamilSpellingsWithoutOrphanMarksOrFragmentAudio() {
        for(word in StarterWords.all){
            val parts=tamilWritingParts(word.tamil)
            assertTrue(parts.isNotEmpty());assertEquals(word.tamil,parts.joinToString(""))
            assertTrue(parts.all{it.first().code in 0x0B80..0x0BFF && Character.isLetter(it.first())})
        }
        assertEquals(listOf("அ","ம்","மா"),tamilWritingParts("அம்மா"))
        assertTrue(tamilWritingParts("\u0BCDஅ").isEmpty())
        assertTrue(tamilWritingParts("external words").isEmpty())
    }
    @Test fun countsAreBoundedAndRestorationCannotManufactureActivityEvidence() {
        val corrupt="word-learning-1\nTA_WORD_0001|999999|999999|999999|999999|999|999|99|999999\nunknown|1|1|1|1|1|1|1|1"
        val restored=WordProgressCodec.decode(corrupt)
        assertTrue(restored.isEmpty())
        var p=PictureProgress()
        repeat(11000){p=p.answer(true,2)}
        assertEquals(10000,p.choices);assertTrue(p.matches<=p.choices);assertTrue(p.noExtraHintMatches<=p.matches)
    }
    @Test fun boundedCountersRoundTripAndUnknownSchemasFailClosed() {
        val data=mapOf("TA_WORD_0001" to PictureProgress().answer(true,2).requestedHelp(2))
        assertEquals(data,WordProgressCodec.decode(WordProgressCodec.encode(data)))
        assertTrue(WordProgressCodec.decode("future-schema\nTA_WORD_0001").isEmpty())
    }
    @Test fun wordClockOffersRoundFocusAndSessionPausesAndRestoresConservatively() {
        val clock=LetterSession.start(3,1000,5000)
        assertEquals(LetterPause.ROUND,clock.practice().practice().practice().reason)
        assertEquals(LetterPause.FOCUS,clock.tick(1000).reason)
        assertEquals(LetterPause.END,clock.tick(5000).reason)
        assertEquals(clock.pause(),clock.pause().tick(3000))
    }
}
