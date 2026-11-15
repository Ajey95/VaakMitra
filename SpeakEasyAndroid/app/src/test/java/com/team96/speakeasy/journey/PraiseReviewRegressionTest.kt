package com.team96.speakeasy.journey

import com.team96.speakeasy.audio.SpeechOwnership
import com.team96.speakeasy.audio.SpeechKind
import com.team96.speakeasy.viewmodel.AppViewModel
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test

/** DEC064/PRS007: actual review boundaries, not acoustic correctness. */
class PraiseReviewRegressionTest {
 @Test fun teachingExampleKeepsOwnershipWhenOldPraisePanelStops(){
  val voice=SpeechOwnership();val pending=PraiseMailbox();val cheer=pending.issue("A");assertTrue(pending.claim("A",cheer))
  pending.cancel(cheer);voice.begin("speaker","example",SpeechKind.EXAMPLE)
  assertFalse(pending.isCurrent("A",cheer));assertFalse(voice.stop("speaker",SpeechKind.PRAISE));assertTrue(voice.owns("speaker","example"))
 }
 @Test fun anOldSpeakerAndLateCallbackCannotStopANewScreensVoice(){
  val voice=SpeechOwnership();voice.begin("old","praise-1",SpeechKind.PRAISE);voice.begin("new","praise-2",SpeechKind.PRAISE)
  assertFalse(voice.stop("old"));voice.finished("old","praise-1");assertTrue(voice.owns("new","praise-2"));assertTrue(voice.stop("new"))
 }
 @Test fun staleCompletionIssuanceCannotReplaceTheNewOwnersTicket(){
  val mailbox=PraiseMailbox();val b=mailbox.issueFor("B","B")!!
  assertNull(mailbox.issueFor("A","B"));assertTrue(mailbox.claim("B",b))
 }
 @Test fun unidentifiedSoundOffSurvivesTwoDistinctPanelReads(){
  val cache=PraisePreferenceCache();cache.load("session-A"){PraiseSettings()}
  assertTrue(cache.save("session-A","session-A",PraiseSettings(automaticSpeech=false),{PraiseSettings()}){true})
  assertFalse(cache.load("session-A"){PraiseSettings()}.automaticSpeech)
  assertTrue(cache.load("session-B"){PraiseSettings()}.automaticSpeech)
 }
 @Test fun failedWriterDirtyReadCannotOverrideLastConfirmedSoundOff(){
  var disk=PraiseSettings(automaticSpeech=false);val cache=PraisePreferenceCache();cache.load("A"){disk}
  assertFalse(cache.save("A","A",disk.copy(automaticSpeech=true),{disk}){disk=it;false})
  assertFalse(cache.load("A"){disk}.automaticSpeech)
 }
 @Test fun reportWriteCanFinishAfterBackgroundWithoutArmingResumeSpeech()=runBlocking {
  val started=CompletableDeferred<Unit>();val release=CompletableDeferred<Unit>();var saves=0
  val vm=AppViewModel(reportWriter={saves++;started.complete(Unit);release.await()},identityProvider={"A"},verifiedIdentityProvider={"A"})
  val report=LocalSessionReport("r",0,1,1,1,1,0,1)
  val ticket=vm.issuePraise("A")!!
  val job=launch{vm.savePracticeReport(report,"A",ticket)};started.await();vm.invalidatePraiseForBackground();release.complete(Unit);job.join()
  assertEquals(1,saves);assertNotNull(vm.currentSessionSummary);assertNull(vm.summaryPraiseTicket("r"))
 }
 @Test fun finishIsIdempotentAndBoundToItsOrigin(){
  val gate=SessionFinishGate("A");assertFalse(gate.begin("B"));assertTrue(gate.begin("A"));assertFalse(gate.begin("A"))
 }
 @Test fun onlyGenuineNonemptyCapturesQualifyRegardlessOfDecoder(){
  assertFalse(hasRecordedSamples(0));assertTrue(hasRecordedSamples(1600))
  assertFalse(recordedPraiseEligible(0,false,true));assertTrue(recordedPraiseEligible(1600,false,false))
  assertFalse(recordedPraiseEligible(1600,true,false));assertTrue(recordedPraiseEligible(1600,true,true))
 }
 @Test fun supportAndEmptyMoreBreaksAreNotEarnedRounds(){
  assertFalse(earnedPraiseRound(LetterPause.ROUND,0,3));assertFalse(earnedPraiseRound(LetterPause.SUPPORT,3,3));assertTrue(earnedPraiseRound(LetterPause.ROUND,3,3))
 }
 @Test fun startupBudgetUsesElapsedTimeRatherThanNumberOfPolls(){
  assertTrue(praiseWithinBudget(1000,4999));assertFalse(praiseWithinBudget(1000,5000));assertFalse(praiseWithinBudget(1000,7000));assertFalse(praiseWithinBudget(1000,999))
 }
}
