package com.team96.speakeasy.audio
import org.junit.Assert.*
import org.junit.Test
/** DEC-056/UX003 review R2: background wins without any rendered frame. */
class PracticeAudioBoundaryTest {
 @Test fun backgroundImmediatelyCancelsAndInvalidatesPendingPermission() {
  val generation=AttemptGeneration();val attempt=generation.next();val calls=mutableListOf<String>()
  val boundary=PracticeAudioBoundary({generation.invalidate()},{calls.add("cancel")},{calls.add("stop")})
  val ticket=boundary.requestPermission()
  boundary.onStateChanged(object:androidx.lifecycle.LifecycleOwner{override val lifecycle:androidx.lifecycle.Lifecycle get()=error("No rendered frame")},androidx.lifecycle.Lifecycle.Event.ON_PAUSE)
  assertEquals(listOf("cancel","stop"),calls);assertFalse(generation.isCurrent(attempt));assertFalse(boundary.isForeground)
  boundary.foreground();assertFalse(boundary.consumePermission(ticket))
  val fresh=boundary.requestPermission();assertTrue(boundary.consumePermission(fresh));assertFalse(boundary.consumePermission(fresh))
 }
 @Test fun closedOwnerNeverRestartsFromResumeOrPermission() {
  val boundary=PracticeAudioBoundary({},{},{})
  val pending=boundary.requestPermission();boundary.close();boundary.foreground()
  assertFalse(boundary.isForeground);assertNull(boundary.requestPermission());assertFalse(boundary.consumePermission(pending))
 }
}
