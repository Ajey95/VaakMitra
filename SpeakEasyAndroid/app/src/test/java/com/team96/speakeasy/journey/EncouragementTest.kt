package com.team96.speakeasy.journey

import org.junit.Assert.*
import org.junit.Test

/** DEC062/PRS001..006: praise is participation, independent of unapproved speech output. */
class EncouragementTest {
 @Test fun dec066LegacyDemoCreditsCannotBecomeCurrentRoundParticipation(){
  for(raw in listOf<Any?>(null,0,1,2,3,"3",listOf(0,3),listOf(1,-1),listOf(1,6)))assertEquals(0,restoreRoundParticipation(raw))
  for(count in 0..5)assertEquals(count,restoreRoundParticipation(roundParticipationSnapshot(count)))
 }
 @Test fun dec066OnlyCompletedRoundEventsMayAutomaticallyCelebrate(){
  for(event in PraiseEvent.entries)assertEquals(event==PraiseEvent.ROUND,automaticCelebrationEligible(event))
 }
 @Test fun dec066AnEarnedRoundNeedsAtLeastThreeParticipatingCompletions(){
  assertFalse(earnedPraiseRound(LetterPause.ROUND,1,1))
  assertFalse(earnedPraiseRound(LetterPause.ROUND,2,3))
  assertTrue(earnedPraiseRound(LetterPause.ROUND,3,3))
  assertFalse(earnedPraiseRound(LetterPause.ROUND,3,5))
  assertTrue(earnedPraiseRound(LetterPause.ROUND,5,5))
  for(reason in LetterPause.entries.filter{it!=LetterPause.ROUND})assertFalse(earnedPraiseRound(reason,3,3))
 }
 @Test fun dec063CompletionTicketIsOwnerBoundAndCanOnlyBeClaimedOnce(){
  val box=PraiseMailbox();val token=box.issue("child-a")
  assertFalse(box.claim("child-b",token));assertFalse(box.claim("child-a",token))
  val next=box.issue("child-a");assertTrue(box.claim("child-a",next));assertFalse(box.claim("child-a",next))
 }
 @Test fun dec063NewCompletionsReplacePendingWorkRatherThanQueueOldCheers(){
  val box=PraiseMailbox();val old=box.issue("child-a");val fresh=box.issue("child-a")
  assertFalse(box.claim("child-a",old));assertTrue(box.claim("child-a",fresh))
  assertFalse(box.isCurrent("child-a",old));assertTrue(box.isCurrent("child-a",fresh))
 }
 @Test fun dec063CancellingAnOldScreenCannotCancelANewSummaryTicket(){
  val box=PraiseMailbox();val old=box.issue("child-a");val summary=box.issue("child-a")
  box.cancel(old);assertTrue(box.claim("child-a",summary))
  val paused=box.issue("child-a");box.cancel(paused);assertFalse(box.claim("child-a",paused))
 }
 @Test fun tamilNameIsLocalPlainTextAndEmptyNamesHaveNoInventedIdentity(){
  assertEquals("கவின்",praiseName("  கவின்\n "))
  assertEquals("",praiseName("<>&123😀"))
  assertEquals("",praiseName("Friend"))
  val line=praiseLine("கவின்",PraiseStyle.HERO,PraiseEvent.PRACTICE)
  assertTrue(line.contains("கவின்"));assertTrue(line.contains("முயற்சி"));assertFalse(line.contains("சரி"))
  assertFalse(praiseLine("",PraiseStyle.CALM,PraiseEvent.PRACTICE).startsWith(","))
 }
 @Test fun dec063CompletionIsAutomaticallyAppreciatedWithClosedBoundedStyles(){
  val settings=PraiseSettings();assertTrue(settings.automaticSpeech);assertTrue(settings.motion)
  assertEquals(PraiseStyle.HERO,PraiseStyle.from("untrusted"))
  for(style in PraiseStyle.entries){assertTrue(style.rate in .8f..1.1f);assertTrue(style.pitch in .8f..1.1f)}
  assertEquals(3,PraiseStyle.entries.size)
 }
 @Test fun elapsedTimeBreaksAndUnscorableStatusAloneNeverEarnAnEffortStamp(){
  val empty=LocalSessionReport("x",0,10000,10,0,0,5,0)
  assertFalse(hasPraiseParticipation(empty));assertFalse(hasPraiseParticipation(null))
  assertTrue(hasPraiseParticipation(empty.copy(attemptCount=1)))
  assertTrue(hasPraiseParticipation(empty.copy(activityChoices=1)))
  assertTrue(hasPraiseParticipation(empty.copy(activityContextTurns=1)))
  assertFalse(hasPraiseParticipation(empty.copy(activityHelpRequests=2)))
 }
 @Test fun everyOriginalStyleAndEventPraisesEffortWithoutDiagnosisOrFilmClaims(){
  for(style in PraiseStyle.entries)for(event in PraiseEvent.entries){
   val line=praiseLine("Maya",style,event)
   assertTrue(line.length in 10..140);assertTrue(line.contains("Maya"))
   assertFalse(line.contains("%"));assertFalse(line.contains("PASS"));assertFalse(line.contains("wrong"))
  }
  assertEquals(3,PraiseStyle.entries.map{praiseLine("Maya",it,PraiseEvent.PRACTICE)}.distinct().size)
 }
 @Test fun aDeliveredEventCannotReplayAfterRecreationOrEnablingSpeech(){
  val first=consumePraise(null,"turn-1",true,true,false);assertTrue(first.play)
  assertFalse(consumePraise(first.consumed,"turn-1",true,true,false).play)
  val quiet=consumePraise(null,"turn-2",true,false,false);assertFalse(quiet.play)
  assertFalse(consumePraise(quiet.consumed,"turn-2",true,true,false).play)
 }
 @Test fun backgroundAndBusyEventsAreConsumedRatherThanQueuedForLater(){
  val background=consumePraise(null,"turn-1",false,true,false);assertFalse(background.play)
  assertFalse(consumePraise(background.consumed,"turn-1",true,true,false).play)
  val busy=consumePraise(null,"turn-2",true,true,true);assertFalse(busy.play)
  assertFalse(consumePraise(busy.consumed,"turn-2",true,true,false).play)
 }
 @Test fun failedOrStalePreferenceWritePreservesLastConfirmedSettings(){
  val old=PraiseSettings();val next=old.copy(automaticSpeech=!old.automaticSpeech)
  val confirmed=ConfirmedPraiseSettings("owner",old)
  assertFalse(confirmed.save("other",next){true});assertEquals(old,confirmed.value)
  assertFalse(confirmed.save("owner",next){false});assertEquals(old,confirmed.value)
  assertTrue(confirmed.save("owner",next){true});assertEquals(next,confirmed.value)
 }
 @Test fun praiseTextNeverRequiresAChildToContinueOrRewardsSittingStill(){
  for(style in PraiseStyle.entries){
   val line=praiseLine("Sample learner",style,PraiseEvent.SESSION)
   assertTrue(line.isNotBlank());assertFalse(line.contains("again"));assertFalse(line.contains("sit"))
  }
 }
}
