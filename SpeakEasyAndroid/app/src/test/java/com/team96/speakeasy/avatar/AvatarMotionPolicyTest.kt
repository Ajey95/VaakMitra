package com.team96.speakeasy.avatar
import org.junit.Assert.*
import org.junit.Test
/** DEC-026/AVT-004..006: visible mode distinction and immediate suppression. */
class AvatarMotionPolicyTest {
 @Test fun gentleIsVisibleAndReducedReallyLimitsDistance(){
  val gentle=avatarMotionSpec(AvatarMotion.GENTLE,AvatarPhase.IDLE)
  val reduced=avatarMotionSpec(AvatarMotion.REDUCED,AvatarPhase.IDLE)
  assertTrue(gentle.breathDistance>=6f);assertTrue(reduced.breathDistance>0f&&reduced.breathDistance<gentle.breathDistance)
  assertTrue(reduced.gestureScale>0f&&reduced.gestureScale<gentle.gestureScale)
  assertTrue(reduced.breathHalfCycleMs>gentle.breathHalfCycleMs);assertTrue(reduced.gestureDurationMs>gentle.gestureDurationMs)
 }
 @Test fun stillNeverBreathesOrGesturesInAnyPhase(){for(phase in AvatarPhase.entries){val s=avatarMotionSpec(AvatarMotion.STILL,phase);assertEquals(0f,s.breathDistance,0f);assertEquals(0f,s.gestureScale,0f)}}
 @Test fun quietSessionStatesHaveNoNonessentialMovement(){for(mode in AvatarMotion.entries)for(phase in listOf(AvatarPhase.LISTENING,AvatarPhase.PROCESSING,AvatarPhase.BREAK,AvatarPhase.ERROR)){val s=avatarMotionSpec(mode,phase);assertEquals(0f,s.breathDistance,0f);assertEquals(0f,s.gestureScale,0f)}}
 @Test fun backgroundAndSystemAnimationOffSuppressImmediately(){for(mode in AvatarMotion.entries)for(phase in AvatarPhase.entries)for(s in listOf(avatarMotionSpec(mode,phase,foreground=false),avatarMotionSpec(mode,phase,systemAnimations=false))){assertEquals(0f,s.breathDistance,0f);assertEquals(0f,s.gestureScale,0f)}}
 @Test fun idleBlinkCurveClosesBrieflyAndReturnsToOpen(){
  for(p in listOf(Float.NaN,-1f,0f,.1f,.3f,1f,2f))assertEquals(0f,avatarBlinkAmount(p),0f)
  assertTrue(avatarBlinkAmount(.23f)>.99f)
  for(i in 0..100)assertTrue(avatarBlinkAmount(i/100f) in 0f..1f)
  val g=avatarMotionSpec(AvatarMotion.GENTLE,AvatarPhase.IDLE);val r=avatarMotionSpec(AvatarMotion.REDUCED,AvatarPhase.IDLE)
  assertTrue(g.blinkPeriodMs>=4000);assertTrue(r.blinkPeriodMs>g.blinkPeriodMs);assertTrue(g.greetingDurationMs>0&&r.greetingDurationMs>g.greetingDurationMs)
 }
 @Test fun greetingCurveIsBoundedAndSettlesToRest(){
  for(p in listOf(Float.NaN,-1f,0f,1f,2f))assertEquals(0f,avatarGreetingAmount(p),0f)
  assertTrue(avatarGreetingAmount(.2f)>.99f)
  for(i in 0..100)assertTrue(avatarGreetingAmount(i/100f) in 0f..1f)
  for(mode in AvatarMotion.entries)for(phase in AvatarPhase.entries){
   val off=avatarMotionSpec(mode,phase,foreground=false);assertEquals(0,off.blinkPeriodMs);assertEquals(0,off.greetingDurationMs)
   if(mode==AvatarMotion.STILL||phase!=AvatarPhase.IDLE){val quiet=avatarMotionSpec(mode,phase);assertEquals(0,quiet.blinkPeriodMs);assertEquals(0,quiet.greetingDurationMs)}
  }
 }
}
