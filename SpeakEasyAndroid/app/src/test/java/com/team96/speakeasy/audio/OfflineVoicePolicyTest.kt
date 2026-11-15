package com.team96.speakeasy.audio
import org.junit.Assert.*
import org.junit.Test
/** DEC025/056 review R4: installed offline voice only, current async errors are visible. */
class OfflineVoicePolicyTest {
 @Test fun notInstalledAndNetworkVoicesCannotBeSelected() {
  val installed=OfflineVoiceCandidate("local","ta",false,false)
  assertEquals(installed,chooseOfflineTamilVoice(listOf(OfflineVoiceCandidate("download","ta",false,true),OfflineVoiceCandidate("cloud","ta",true,false),OfflineVoiceCandidate("english","en",false,false),installed)))
  assertNull(chooseOfflineTamilVoice(listOf(installed.copy(notInstalled=true))))
 }
 @Test fun selectionFailureAndDifferentActiveVoiceNeverBecomeReady() {
  val voice=OfflineVoiceCandidate("local","ta",false,false)
  assertFalse(isSelectedOfflineTamilVoice(voice,false,voice))
  assertFalse(isSelectedOfflineTamilVoice(voice,true,voice.copy(name="fallback")))
  assertFalse(isSelectedOfflineTamilVoice(voice,true,voice.copy(networkRequired=true)))
  assertTrue(isSelectedOfflineTamilVoice(voice,true,voice))
 }
 @Test fun asyncFailureIsReportedButStoppedUtteranceCannotChangeTheNextTarget() {
  val speaking=mutableListOf<Boolean>();var unavailable=0
  val guard=VoicePlaybackGuard({speaking.add(it)},{unavailable++})
  guard.begin("first");guard.started("first");guard.failed("first")
  assertEquals(listOf(true,false),speaking);assertEquals(1,unavailable)
  guard.begin("old");guard.stop();guard.begin("new");guard.failed("old");guard.started("old")
  assertEquals(1,unavailable);guard.started("new");guard.finished("new");assertEquals(false,speaking.last())
 }
}
