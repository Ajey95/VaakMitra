package com.team96.speakeasy.journey

import com.team96.speakeasy.viewmodel.AppViewModel
import org.junit.Assert.*
import org.junit.Test

class InterestSessionReportTest {
    @Test fun dec059UnownedOrOtherProfileReportsAreNeverAttributedToTheCurrentChild() {
        val old=LocalSessionReport("old",0,1000,1,1,1,0,1)
        assertNull(reportForProfile(old,null,"a"))
        assertNull(reportForProfile(old,"a","b"))
        assertNull(reportForProfile(old,"a",null))
        assertSame(old,reportForProfile(old,"a","a"))
    }
    @Test fun dec059PictureEventsAreSeparateFromVoiceAndNeverGenerateAccuracy() {
        val report=summarizeSession("public",0,1000,listOf(
            SessionEvent.PictureChoice("TA_WORD_0001",true,true),
            SessionEvent.PictureChoice("TA_WORD_0002",false,false),
            SessionEvent.PictureHelp("TA_WORD_0002"),
            SessionEvent.Attempt("TA_WORD_0001","PHONEME_TOKENS")))
        assertEquals(2,report.activityChoices);assertEquals(1,report.activityMatches)
        assertEquals(1,report.activityWithoutExtraHint);assertEquals(1,report.activityHelpRequests)
        assertEquals(1,report.attemptCount);assertEquals(1,report.unscorableCount);assertNull(report.accuracyPercent)
    }
    @Test fun dec059OlderReportConstructorsKeepZeroActivityCounts() {
        val old=LocalSessionReport("old",0,1000,1,1,1,0,1)
        assertEquals(0,old.activityChoices);assertEquals(0,old.activityMatches)
    }
    @Test fun dec059PublicPreviewLearnsOnlyInMemoryAndHasItsOwnInterest() {
        val vm=AppViewModel(preview=true,previewInterest="trains")
        assertEquals("trains",vm.practiceCarePlan.interest)
        val options=listOf("TA_WORD_0001","TA_WORD_0002")
        assertTrue(vm.choosePicture("TA_WORD_0001","TA_WORD_0001",options,1))
        assertEquals(1,vm.wordProgress.value["TA_WORD_0001"]!!.matches)
        assertTrue(vm.requestPictureHelp("TA_WORD_0001",1))
        assertEquals(1,vm.wordProgress.value["TA_WORD_0001"]!!.helps)
        assertFalse(vm.wordHistoryPersistent)
        assertTrue(AppViewModel(preview=true).wordProgress.value.isEmpty())
    }
    @Test fun dec059WordClockRestoreRequiresExplicitResume() {
        val clock=WordLearningPacing.start(CarePlan(focusMinutes=2,sessionMinutes=5)).tick(1000)
        assertTrue(WordLearningPacing.restore(clock.snapshot()).paused)
    }
}
