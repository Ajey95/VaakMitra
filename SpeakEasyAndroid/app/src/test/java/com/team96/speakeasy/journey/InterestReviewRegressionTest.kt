package com.team96.speakeasy.journey

import org.junit.Assert.*
import org.junit.Test

/** DEC060 / ILR011: five final-review failure paths, not speech assessments. */
class InterestReviewRegressionTest {
    @Test fun restoredCountersRetainPictureActivityAndMicWordSet() {
        val tally=SessionTally().record(SessionEvent.PictureChoice("TA_WORD_0002",true,false))
            .record(SessionEvent.Attempt("TA_WORD_0001","UNSCORABLE"))
        val restored=SessionTally.decode(tally.encode())
        val report=restored.report("same-session",1000,3000)
        assertEquals(1,report.activityMatches);assertEquals(1,report.attemptCount)
        assertEquals(1,report.uniqueWordCount);assertNull(report.accuracyPercent)
    }
    @Test fun loadingCannotAcknowledgeATapAndDelayedOldOwnerCannotWrite() {
        var current="a";var writes=0
        val binding=ScopedPictureBinding{current}
        binding.begin("a",true)
        assertFalse(binding.update("a","TA_WORD_0001",PictureProgress()){writes++;true})
        current="b";binding.begin("b",true);binding.loaded("b",emptyMap())
        assertFalse(binding.loaded("a",mapOf("TA_WORD_0001" to PictureProgress(choices=1,matches=1))))
        assertFalse(binding.update("a","TA_WORD_0001",PictureProgress()){writes++;true})
        assertEquals(0,writes);assertTrue(binding.load().isEmpty())
    }
    @Test fun failedSaveKeepsConfirmedHistoryWhileDisplayedHelpControlsHintFreeCounts() {
        val earned=PictureProgress(choices=4,matches=4,help=PromptHelp.YOUR_TURN)
        val binding=ScopedPictureBinding{"a"};binding.begin("a",true);binding.loaded("a",mapOf("TA_WORD_0001" to earned))
        val shown=earned.requestedHelp(2)
        assertFalse(binding.update("a","TA_WORD_0001",shown){false})
        assertEquals(PromptHelp.YOUR_TURN,binding.load()["TA_WORD_0001"]!!.help)
        val answer=pictureSelection("TA_WORD_0001","TA_WORD_0001",listOf("TA_WORD_0001","TA_WORD_0002"),shown,2)
        assertEquals(PromptHelp.GUIDED,shown.help);assertEquals(0,answer.progress.noExtraHintMatches)
        assertTrue(binding.update("a","TA_WORD_0001",answer.progress){true})
        assertEquals(1,binding.load()["TA_WORD_0001"]!!.helps)
    }
    @Test fun allTargetsExcludeConfusableSymbolPairsAcrossTurns() {
        val pairs=listOf(setOf("TA_WORD_0017","TA_WORD_0101"),setOf("TA_WORD_0013","TA_WORD_0084"))
        for(word in StarterWords.all.filter{WordActivityCatalog.isMatch(it.id)})for(turn in 0..100)for(count in 2..3){
            val options=learningOptions(word.id,count,turn)
            assertTrue("${word.id}/$turn/$options",pairs.none{options.containsAll(it)})
        }
    }
    @Test fun failedOrEphemeralReportStillShowsCurrentSessionAndRejectsLateOwner() {
        val report=SessionTally().record(SessionEvent.PictureChoice("TA_WORD_0001",true,false)).report("s",0,1000)
        val handoff=SessionReportHandoff("a",report,false)
        assertSame(report,handoff.visible("a")!!.report)
        assertFalse(handoff.visible("a")!!.saved)
        assertNull(handoff.visible("b"))
        assertFalse(reportWriteAllowed("a","b",true))
        assertFalse(reportWriteAllowed("session-only:a","session-only:a",false))
        assertTrue(reportWriteAllowed("a","a",true))
    }
    @Test fun viewModelCarriesFailedSaveSummaryAndDoesNotPublishLateOwner()=kotlinx.coroutines.runBlocking{
        var owner="a";var writes=0
        val report=SessionTally().record(SessionEvent.PictureChoice("TA_WORD_0001",true,false)).report("s",0,1000)
        val failed=com.team96.speakeasy.viewmodel.AppViewModel(reportWriter={writes++;error("disk failure")},identityProvider={owner},verifiedIdentityProvider={owner})
        assertFalse(failed.savePracticeReport(report,"a"));assertEquals(1,writes)
        assertSame(report,failed.currentSessionSummary!!.report);assertTrue(failed.currentSessionSummary!!.saveFailed)
        val late=com.team96.speakeasy.viewmodel.AppViewModel(reportWriter={owner="b"},identityProvider={owner},verifiedIdentityProvider={owner})
        assertFalse(late.savePracticeReport(report,"a"));assertNull(late.currentSessionSummary)
        assertFalse(late.savePracticeReport(report,"a"));assertNull(late.currentSessionSummary)
        val ephemeral=com.team96.speakeasy.viewmodel.AppViewModel(preview=true)
        assertFalse(ephemeral.savePracticeReport(report));assertSame(report,ephemeral.currentSessionSummary!!.report)
    }
}
