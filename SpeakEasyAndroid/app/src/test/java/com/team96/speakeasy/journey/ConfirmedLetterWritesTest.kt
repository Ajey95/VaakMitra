package com.team96.speakeasy.journey
import org.junit.Assert.*
import org.junit.Test
/** DEC053 review R3: fake SharedPreferences changes memory while disk write fails twice. */
class ConfirmedLetterWritesTest {
 @Test fun dirtyMemoryNeverAcknowledgesAnUncommittedMark() {
  var memory=LetterJourneySnapshot();var disk=memory;var writes=0
  val writer=ConfirmedLetterWrites(memory){candidate->memory=candidate;writes++;if(writes<=2)false else{disk=candidate;true}}
  val first=TamilAlphabet.all.first().id
  repeat(2){assertTrue(runCatching{writer.complete(first)}.isFailure);assertEquals(1,memory.progress.completedCount);assertEquals(0,disk.progress.completedCount);assertEquals(0,writer.load().progress.completedCount)}
  assertEquals(1,writer.complete(first).progress.completedCount);assertEquals(1,disk.progress.completedCount);assertEquals(3,writes)
  writer.complete(first);assertEquals(3,writes)
 }
 @Test fun failedSettingsCannotCarryAnUnconfirmedProgressWrite() {
  var durable=LetterJourneySnapshot();var success=false
  val writer=ConfirmedLetterWrites(durable){candidate->if(success){durable=candidate;true}else false}
  assertTrue(runCatching{writer.complete(TamilAlphabet.all[0].id)}.isFailure)
  success=true;writer.saveSettings(LetterPracticeSettings(1,false))
  assertEquals(0,durable.progress.completedCount);assertEquals(LetterPracticeSettings(1,false),durable.settings)
 }
}
