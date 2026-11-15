package com.team96.speakeasy.avatar

/** DEC-026/AVT-004..006: distances use the existing 320x390 rig coordinates. */
data class AvatarMotionSpec(val breathDistance:Float=0f,val breathHalfCycleMs:Int=2400,val gestureScale:Float=0f,val gestureDurationMs:Int=360,val blinkPeriodMs:Int=0,val greetingDurationMs:Int=0)
fun avatarMotionSpec(motion:AvatarMotion,phase:AvatarPhase,foreground:Boolean=true,systemAnimations:Boolean=true):AvatarMotionSpec {
 if(!foreground||!systemAnimations||motion==AvatarMotion.STILL||phase in setOf(AvatarPhase.LISTENING,AvatarPhase.PROCESSING,AvatarPhase.BREAK,AvatarPhase.ERROR))return AvatarMotionSpec()
 val gentle=motion==AvatarMotion.GENTLE
 return AvatarMotionSpec(
  breathDistance=if(phase==AvatarPhase.IDLE)if(gentle)8f else 1.5f else 0f,
  breathHalfCycleMs=if(gentle)2400 else 4200,
  gestureScale=if(gentle)1f else .35f,
  gestureDurationMs=if(gentle)360 else 650,
  blinkPeriodMs=if(phase==AvatarPhase.IDLE)if(gentle)5600 else 8400 else 0,
  greetingDurationMs=if(phase==AvatarPhase.IDLE)if(gentle)1800 else 2600 else 0,
 )
}

private fun smoothAvatarStep(value:Float):Float {val t=value.coerceIn(0f,1f);return t*t*(3f-2f*t)}
/** Open eyes at the cycle boundary prevent a frozen closed eye when animations are disabled. */
fun avatarBlinkAmount(progress:Float):Float {
 if(!progress.isFinite()||progress<=.20f||progress>=.26f)return 0f
 return if(progress<.23f)smoothAvatarStep((progress-.20f)/.03f)else 1f-smoothAvatarStep((progress-.23f)/.03f)
}
private val greetingPoses=floatArrayOf(0f,1f,.6f,1f,.6f,0f)
fun avatarGreetingAmount(progress:Float):Float {
 if(!progress.isFinite()||progress<=0f||progress>=1f)return 0f
 val position=progress*5f;val index=position.toInt().coerceIn(0,4);val blend=smoothAvatarStep(position-index)
 return (greetingPoses[index]+(greetingPoses[index+1]-greetingPoses[index])*blend).coerceIn(0f,1f)
}
