package com.team96.speakeasy.audio

import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

/** DEC070/PHN011: automatic cue cadence cannot outlive the foreground owner. */
class AutonomousGuideTest {
    private val fast=GuideCadence(visualMs=1,imitationMs=1,voiceStartMs=1,voiceFinishMs=1)
    @Test fun phn011CueStagesAdvanceWithoutChildSelections()=runBlocking {
        val stages=mutableListOf<Int>();var stopped=false
        assertTrue(runGuideCues(listOf(0,1,2),fast,{true},{stages.add(it)},{false},{false},{stopped=true}))
        assertEquals(listOf(0,1,2),stages);assertTrue(stopped)
    }
    @Test fun phn011LostForegroundBlocksNextStageAndStopsSpeech()=runBlocking {
        val stages=mutableListOf<Int>();var allowed=true;var stopped=false
        assertFalse(runGuideCues(listOf(0,1,2),fast,{allowed},{stages.add(it);allowed=false},{false},{false},{stopped=true}))
        assertEquals(listOf(0),stages);assertTrue(stopped)
    }
    @Test fun phn011CoroutineCancellationCannotPublishALaterCue()=runBlocking {
        val stages=mutableListOf<Int>();var stopped=false
        val job=launch{runGuideCues(listOf(0,1,2),fast.copy(visualMs=2000),{true},{stages.add(it)},{false},{false},{stopped=true})}
        yield();job.cancelAndJoin()
        assertEquals(listOf(0),stages);assertTrue(stopped)
    }
    @Test fun phn011StuckVoiceCallbackIsBoundedAndStoppedBeforeCompletion()=runBlocking {
        var speaking=true
        assertTrue(runGuideCues(listOf(2),fast,{true},{},{true},{speaking},{speaking=false}))
        assertFalse(speaking)
    }
}
