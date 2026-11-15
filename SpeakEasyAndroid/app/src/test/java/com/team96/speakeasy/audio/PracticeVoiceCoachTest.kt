package com.team96.speakeasy.audio

import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

/** COA001/DEC071: automatic spoken help is neutral, cancellable and never an error diagnosis. */
class PracticeVoiceCoachTest {
    private val fast=GuideCadence(1,1,1,1)
    @Test fun coa002UnqualifiedAlignmentCannotSelectSoundSpecificVoiceHelp(){
        val alignment=PauseAlignmentResult("diagnostic_only",listOf(AlignedPhone("m","s","possible_substitution")))
        assertEquals(PracticeCoachCue.TOGETHER,PracticeVoiceCoach.choose(LocalWordOutcome(reason="PHONEME_TOKENS",pauseAlignment=alignment)))
        assertNull(PracticeVoiceCoach.focusSound(alignment,listOf("a","m","m","aː")))
    }
    @Test fun coa002UnqualifiedDifferenceDoesNotEnterCoachingContract(){
        val alignment=PauseAlignmentResult("diagnostic_only",listOf(AlignedPhone("m",null,"possible_omission")))
        val result=PracticeVoiceCoach.toolResult("TA_WORD_0001",alignment,PracticeCoachCue.TOGETHER)
        assertTrue(result.possibleDifferences.isEmpty())
        assertEquals("insufficient_evidence",result.evidenceStatus)
    }
    @Test fun coa001QuietRecordingInvitesCloserPhoneWithoutScoring(){
        val cue=checkNotNull(PracticeVoiceCoach.choose(LocalWordOutcome(reason="VAD_NO_SPEECH"),PcmCaptureEvidence(16000,100,20.0,1.0)))
        assertEquals(PracticeCoachCue.QUIET,cue)
        assertTrue(cue.caption.contains("closer"))
    }
    @Test fun coa001DurationAloneNeverClaimsChildTooSlowOrFast(){
        val cue=checkNotNull(PracticeVoiceCoach.choose(LocalWordOutcome(reason="TOO_LONG"),PcmCaptureEvidence(128000,3000,500.0,1.0)))
        assertEquals(PracticeCoachCue.OWN_PACE,cue)
        assertFalse(cue.caption.contains("too slow"))
        assertFalse(cue.caption.contains("too fast"))
    }
    @Test fun coa001PredictedMismatchDemonstratesInsteadOfDeclaringWrong(){
        val cue=checkNotNull(PracticeVoiceCoach.choose(LocalWordOutcome(reason="PHONEME_TOKENS",predictedPhonemes=listOf("s"))))
        assertEquals(PracticeCoachCue.TOGETHER,cue)
        assertFalse(cue.caption.contains("wrong"))
    }
    @Test fun coa001NoCaptureOrUnavailableModelDoesNotInventAnAudioIssue(){
        assertNull(PracticeVoiceCoach.choose(LocalWordOutcome(reason="MODEL_UNAVAILABLE")))
        assertNull(PracticeVoiceCoach.choose(LocalWordOutcome(reason="TARGET_UNAVAILABLE")))
    }
    @Test fun coa001SpokenFeedbackPrecedesTargetCueAndHonorsCancellation()=runBlocking {
        val events=mutableListOf<String>();var allowed=true
        val completed=runCoachPreface(fast,{allowed},{events.add("coach")},{false},{})
        assertTrue(completed);events.add("word")
        assertEquals(listOf("coach","word"),events)
        assertFalse(runCoachPreface(fast,{allowed},{allowed=false;true},{false},{}))
    }
    @Test fun coa001CancelledCoachCannotStartWordExample()=runBlocking {
        var stopped=false;var word=false
        val job=launch{if(runCoachPreface(fast.copy(visualMs=2000),{true},{false},{false},{stopped=true}))word=true}
        yield();job.cancelAndJoin()
        assertTrue(stopped);assertFalse(word)
    }
    @Test fun coa001SmallPartInvitationActuallyRestoresFullGuide(){
        assertTrue(PracticeVoiceCoach.needsFullGuide(PracticeCoachCue.OWN_PACE))
        assertTrue(PracticeVoiceCoach.needsFullGuide(PracticeCoachCue.UNCLEAR))
        assertFalse(PracticeVoiceCoach.needsFullGuide(PracticeCoachCue.TOGETHER))
        assertFalse(PracticeVoiceCoach.needsFullGuide(null))
    }
    @Test fun coa001ToolContractOmitsObservedAudioDerivedSequences(){
        val alignment=PauseAlignmentResult("diagnostic_only",listOf(AlignedPhone("m","s","possible_substitution")))
        val fields=PracticeVoiceCoach.toolResult("TA_WORD_0001",alignment,PracticeCoachCue.SOUND_EXAMPLE).toToolFields()
        val text=fields.toString()
        assertFalse(text.contains("observed"))
        assertFalse(text.contains("transcript"))
        assertFalse(text.contains("embedding"))
        assertEquals(false,fields["clinical_assessment"])
        assertNull(fields["child_correctness"])
    }
    @Test fun coa001AcceptedSequenceVariantCannotTriggerCorrectionCue(){
        val outcome=LocalWordOutcome(reason="PHONEME_TOKENS",soundPracticeEvidence=SoundPracticeEvidence("TA_WORD_0049",emptySet(),true),
            pauseAlignment=PauseAlignmentResult("diagnostic_only",listOf(AlignedPhone("m","s","possible_substitution"))))
        assertEquals(PracticeCoachCue.TOGETHER,PracticeVoiceCoach.choose(outcome))
    }
    @Test fun coa001EmptyCaptureDoesNotClaimQuietSpeech(){
        assertEquals(PracticeCoachCue.UNCLEAR,PracticeVoiceCoach.choose(LocalWordOutcome(reason="TOO_SHORT"),PcmCaptureEvidence(0,0,0.0,0.0)))
    }
    @Test fun coa001UntrustedToolValuesCannotEscapeClosedContract(){
        org.junit.Assert.assertThrows(IllegalArgumentException::class.java){PracticeVoiceCoach.toolResult("TA_WORD_9999",null,null)}
        org.junit.Assert.assertThrows(IllegalArgumentException::class.java){
            CoachToolResult("TA_WORD_0001","secret filename.wav",null,emptyList()).toToolFields()
        }
    }
}
