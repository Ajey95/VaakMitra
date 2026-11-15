package com.team96.speakeasy.journey

import org.junit.Assert.*
import org.junit.Test

/** DEC061 / ILR012..016: a meaningful target, not arbitrary glyph guessing. */
class ClearLearningScenesTest {
    @Test fun extraSupportBeforeHistoryLoadsOrDuringAWriteNeverEarnsHintFreeCredit() {
        val readyLater=PictureProgress(choices=4,matches=4,help=PromptHelp.YOUR_TURN)
        val turn=choosePictureWithSupport("TA_WORD_0001","TA_WORD_0001",listOf("TA_WORD_0001","TA_WORD_0002"),readyLater,1,extraSupportUsed=true)
        assertFalse(turn.withoutExtraHint);assertEquals(0,turn.response.progress.noExtraHintMatches)
        assertEquals(PromptHelp.GUIDED,pictureProgressWithSupport(readyLater,true).help)
        val wrong=PictureProgress(choices=1,recentErrors=1)
        assertTrue(choosePictureWithSupport("TA_WORD_0001","TA_WORD_0002",listOf("TA_WORD_0001","TA_WORD_0002"),wrong,1,true).response.progress.needsBreak)
        assertTrue(choosePictureWithSupport("TA_WORD_0001","TA_WORD_0001",listOf("TA_WORD_0001","TA_WORD_0002"),readyLater,1,false).withoutExtraHint)
    }
    @Test fun guideCopyNamesAvailableControlsAndKeepsSpeakingOptional() {
        for(word in StarterWords.all){
            val initial=wordIdlePrompt(word.id,false);val explored=wordIdlePrompt(word.id,true)
            assertTrue(initial.contains("optional"));assertTrue(explored.contains("optional"))
            if(!WordActivityCatalog.isMatch(word.id)){assertTrue(initial.contains("Show the action"));assertTrue(explored.contains("See it again"));assertFalse(initial.contains("picture"))}
        }
    }
    @Test fun backgroundResumePreservesPartialWordRoundAndFocusBudget() {
        val original=WordLearningPacing.start(CarePlan(focusMinutes=2,sessionMinutes=5)).practice().practice().tick(2000)
        val resumed=WordLearningPacing.resume(WordLearningPacing.restore(original.snapshot()))
        assertFalse(resumed.paused);assertEquals(2,resumed.roundPractised);assertEquals(2000L,resumed.blockActiveMs)
        assertEquals(LetterPause.ROUND,resumed.practice().reason)
        assertEquals(LetterPause.FOCUS,resumed.tick(118000).reason)
        assertEquals(0,WordLearningPacing.resume(original.practice()).roundPractised)
    }
    @Test fun illustrationFittingPreservesShapeAndCentersWithinWideOrNarrowFrames() {
        for((width,height)in listOf(320f to 120f,144f to 96f,76f to 48f,320f to 60f,90f to 96f)){
            val frame=com.team96.speakeasy.ui.components.fitIllustration(width,height,120f,90f)
            assertTrue(frame.scale>0f);assertTrue(frame.dx>=0f);assertTrue(frame.dy>=0f)
            assertTrue(120f*frame.scale<=width+.001f);assertTrue(90f*frame.scale<=height+.001f)
            assertEquals(width,frame.dx*2+120f*frame.scale,.001f)
            assertEquals(height,frame.dy*2+90f*frame.scale,.001f)
        }
        assertThrows(IllegalArgumentException::class.java){com.team96.speakeasy.ui.components.fitIllustration(0f,10f,120f,90f)}
    }
    @Test fun ammaAndAppaUseOnlyFamilyAlternativesAtTwoChoices() {
        for(target in listOf("TA_WORD_0001","TA_WORD_0002"))for(turn in 0..15)
            assertEquals(setOf("TA_WORD_0001","TA_WORD_0002"),learningOptions(target,2,turn).toSet())
    }
    @Test fun abstractWordsCannotEnterMatchingEvenWithKnownVisibleIds() {
        assertThrows(IllegalArgumentException::class.java){pictureSelection("TA_WORD_0013","TA_WORD_0013",listOf("TA_WORD_0013","TA_WORD_0014"),PictureProgress(),1)}
    }
    @Test fun oldGlyphHistoryCannotSeedClearPictureDifficulty() {
        assertTrue(WordProgressCodec.decode("word-learning-1\nTA_WORD_0001|4|4|0|0|0|0|2|1").isEmpty())
    }
    @Test fun onlySixConcreteMeaningsCanOfferPictureAlternatives() {
        val concrete=setOf("TA_WORD_0001","TA_WORD_0002","TA_WORD_0012","TA_WORD_0086","TA_WORD_0084","TA_WORD_0061")
        for(word in StarterWords.all)if(word.id !in concrete)
            assertThrows(word.id,IllegalArgumentException::class.java){learningOptions(word.id,2,0)}
    }
    @Test fun everyInstalledWordHasAnExplicitIllustrationAndFairActivityMode() {
        assertEquals(25,StarterWords.all.map{WordActivityCatalog.art(it.id)}.toSet().size)
        assertEquals(6,WordActivityCatalog.matchIds.size)
        for(word in StarterWords.all){
            val example=WordActivityCatalog.context(word.id)
            if(WordActivityCatalog.isMatch(word.id)){
                assertNull(example);assertTrue(WordActivityCatalog.pictureCaption(word.id).isNotBlank())
                for(turn in 0..20)for(count in 2..3){
                    val options=learningOptions(word.id,count,turn)
                    assertEquals(count,options.distinct().size);assertTrue(options.all{it in WordActivityCatalog.pool(word.id)})
                }
            }else{
                assertNotNull(example);assertTrue(example!!.prompt.isNotBlank());assertNotEquals(example.before,example.after)
            }
        }
        assertThrows(IllegalArgumentException::class.java){WordActivityCatalog.art("unknown")}
    }
    @Test fun scenesHaveExplicitBilingualChoicesAndBoundedRoundProgress() {
        for(theme in InterestTheme.entries){assertTrue(theme.choiceLabel().isNotBlank());assertTrue(theme.tamilLabel().isNotBlank())}
        assertEquals(0,playSceneStep(-1));assertEquals(0,playSceneStep(0));assertEquals(3,playSceneStep(3));assertEquals(3,playSceneStep(100))
    }
    @Test fun contextActionsAreSeparateFromPictureMatchesAndSpeechCounts() {
        val report=summarizeSession("s",0,1000,listOf(SessionEvent.ContextTurn("TA_WORD_0013")))
        assertEquals(1,report.activityContextTurns);assertEquals(0,report.activityChoices);assertEquals(0,report.activityMatches)
        assertEquals(0,report.attemptCount);assertNull(report.accuracyPercent)
    }
    @Test fun demonstrationCountersRestoreAndLegacyTalliesKeepZeroDefault() {
        val tally=SessionTally().record(SessionEvent.ContextTurn("TA_WORD_0013"))
        val report=SessionTally.decode(tally.encode()).report("s",0,1000)
        assertEquals(1,report.activityContextTurns);assertEquals(0,report.activityMatches)
        assertEquals(0,SessionTally.decode("1,0,0,0,0,0;TA_WORD_0001").report("s",0,1000).activityContextTurns)
        assertEquals(0,SessionTally().record(SessionEvent.ContextTurn("unknown")).contextTurns)
        assertEquals(0,SessionTally().record(SessionEvent.ContextTurn("TA_WORD_0001")).contextTurns)
    }
    @Test fun demonstrationCountsAreBoundedWithoutCreatingMatchesOrVoiceAttempts() {
        var tally=SessionTally();repeat(10020){tally=tally.record(SessionEvent.ContextTurn("TA_WORD_0013"))}
        val report=tally.report("s",0,1000)
        assertEquals(10000,report.activityContextTurns);assertEquals(0,report.activityMatches);assertEquals(0,report.attemptCount)
    }
    @Test fun forgedContextMatchesCannotEnterVersion2HistoryOrReports() {
        assertTrue(WordProgressCodec.decode("word-learning-2\nTA_WORD_0013|1|1|0|0|0|0|0|1").isEmpty())
        assertFalse(ConfirmedWordLearningWrites(emptyMap(),{true},{true}).put("TA_WORD_0013",PictureProgress(choices=1,matches=1)))
        val event=SessionEvent.PictureChoice("TA_WORD_0013",true,true)
        assertEquals(0,SessionTally().record(event).choices)
        assertEquals(0,summarizeSession("s",0,1000,listOf(event,SessionEvent.ContextTurn("unknown"))).activityChoices)
        assertEquals(0,summarizeSession("s",0,1000,listOf(SessionEvent.ContextTurn("unknown"))).activityContextTurns)
    }
}
