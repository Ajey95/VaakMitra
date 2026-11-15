package com.team96.speakeasy.journey

import org.junit.Assert.*
import org.junit.Test

/** DEC070/PHN011: curricular feedback rules, not child speech accuracy or trained RL. */
class AutonomousPracticeTest {
    private val pictureProgress=mapOf(
        "TA_WORD_0001" to PictureProgress(choices=2,matches=2),
        "TA_WORD_0002" to PictureProgress(choices=2,matches=2),
    )
    private fun cycle(initial:AutonomousPracticeState,usable:Boolean=true,agree:Boolean=true,
        pictures:Map<String,PictureProgress> = emptyMap(),focus:String?=null):AutonomousPracticeState {
        var state=initial
        repeat(3){state=AutonomousPracticePolicy.advance(state,
            WordCycleSignal(usable=usable,sequenceAgreement=agree),pictures,focus,emptyMap()).state}
        return state
    }
    @Test fun phn011ACompleteCycleRepeatsTheWholeApprovedSet(){
        val state=AutonomousPracticePolicy.start(1,false,4)!!
        assertEquals(listOf(1,2,13),state.words)
        val one=AutonomousPracticePolicy.advance(state,WordCycleSignal(true,true),emptyMap(),null,emptyMap())
        assertEquals(2,one.nextLessonId);assertFalse(one.cycleFinished)
        val repeated=cycle(state)
        assertEquals(state.words,repeated.words);assertEquals(0,repeated.position)
        assertEquals(1,repeated.completedCycles)
    }
    @Test fun phn011ThreeConsistentCyclesAndIndependentTaskProgressPermitOneTierChallenge(){
        var state=AutonomousPracticePolicy.start(1,false,4)!!
        repeat(3){state=cycle(state,pictures=pictureProgress)}
        assertEquals(2,state.tier)
        assertTrue(state.words.all{StarterWords.byNumericLessonId(it)!!.difficulty<=2})
        assertEquals(3,state.completedCycles)
    }
    @Test fun phn011TokenAgreementAloneDoesNotPromoteAChild(){
        var state=AutonomousPracticePolicy.start(1,false,4)!!
        repeat(3){state=cycle(state)}
        assertEquals(1,state.tier)
    }
    @Test fun phn011FiveUnclearCyclesChangeToAGentlerSetInsteadOfRetryingForever(){
        var state=AutonomousPracticePolicy.start(3,false,4)!!
        val original=state.words
        repeat(5){state=cycle(state,usable=false,agree=false)}
        assertEquals(1,state.tier);assertNotEquals(original,state.words)
        assertEquals(0,state.cyclesOnSet)
    }
    @Test fun phn011ShorterFocusWindowUsesASmallerRepetitionBudget(){
        var shorter=AutonomousPracticePolicy.start(3,false,2)!!
        var longer=AutonomousPracticePolicy.start(3,false,4)!!
        repeat(3){shorter=cycle(shorter,usable=false,agree=false);longer=cycle(longer,usable=false,agree=false)}
        assertEquals(1,shorter.tier);assertEquals(2,longer.tier)
    }
    @Test fun phn011AllChangedSetsStayInTheCurrentFocusedCatalogue(){
        var state=AutonomousPracticePolicy.start(1,true,4)!!
        repeat(18){state=cycle(state,usable=false,agree=false)}
        assertTrue(state.words.size in 1..3)
        assertTrue(state.words.all{it in StarterWords.focusedLessonIds})
        assertNull(AutonomousPracticePolicy.start(999,true,4))
    }
    @Test fun phn011RepeatedSoundHypothesesRestoreSupportWithoutProvingFailure(){
        var state=AutonomousPracticePolicy.start(1,false,4)!!
        state=cycle(state,pictures=pictureProgress)
        assertEquals(listOf(1,2),AutonomousPracticePolicy.guidanceSteps(state,false,pictureProgress))
        assertEquals(listOf(0,1,2),AutonomousPracticePolicy.guidanceSteps(state,true,pictureProgress))
        repeat(3){state=cycle(state,pictures=pictureProgress,focus="m")}
        assertEquals(1,state.tier)
    }
    @Test fun phn011AutomaticCycleContinuationPreservesAndChargesTheFocusWindow(){
        val round=LetterSession.start(3,120000,300000).tick(90000).practice().practice().practice()
        val continued=WordLearningPacing.continueAutonomousRound(round,5000)
        assertEquals(95000L,continued.blockActiveMs);assertEquals(95000L,continued.totalActiveMs)
        assertEquals(0,continued.roundPractised)
        val focus=continued.tick(25000)
        assertEquals(LetterPause.FOCUS,focus.reason)
        assertEquals(focus,WordLearningPacing.continueAutonomousRound(focus,5000))
    }
    @Test fun phn011UserBackgroundSupportAndEndNeverAutoResume(){
        for(reason in listOf(LetterPause.USER,LetterPause.BACKGROUND,LetterPause.SUPPORT,LetterPause.END)){
            val paused=LetterSession.start(3,120000,300000).pause(reason)
            assertEquals(paused,WordLearningPacing.continueAutonomousRound(paused,1000))
        }
    }
    @Test fun phn011ZeroSettlingCannotResumeAnAlreadyExhaustedWindow(){
        val exhausted=LetterSession.start(3,120000,300000).copy(blockActiveMs=120000,totalActiveMs=120000,reason=LetterPause.ROUND)
        assertEquals(LetterPause.FOCUS,WordLearningPacing.continueAutonomousRound(exhausted,0).reason)
        assertEquals(LetterPause.END,WordLearningPacing.continueAutonomousRound(exhausted.copy(totalActiveMs=300000),0).reason)
    }
    @Test fun phn011SupportRotationRetainsAvailableSameSoundWordsAtTheLowestTier(){
        val references=mapOf("TA_WORD_0001" to listOf("a","m","m","aː"),"TA_WORD_0083" to listOf("aː","m"))
        var state=AutonomousPracticePolicy.start(1,true,2)!!
        repeat(9){state=AutonomousPracticePolicy.advance(state,WordCycleSignal(false,false),emptyMap(),"m",references).state}
        assertTrue(state.words.containsAll(listOf(1,13)))
        assertTrue(state.words.all{it in StarterWords.focusedLessonIds && StarterWords.byNumericLessonId(it)!!.difficulty==1})
    }
}
