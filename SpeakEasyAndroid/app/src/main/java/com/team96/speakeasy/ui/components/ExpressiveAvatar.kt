package com.team96.speakeasy.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.runtime.key
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import android.animation.ValueAnimator
import com.team96.speakeasy.avatar.avatarMotionSpec
import com.team96.speakeasy.avatar.avatarBlinkAmount
import com.team96.speakeasy.avatar.avatarGreetingAmount
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Rect
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.graphics.drawscope.rotate
import androidx.compose.ui.graphics.drawscope.withTransform
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import com.team96.speakeasy.avatar.AvatarExpression
import com.team96.speakeasy.avatar.AvatarGesture
import com.team96.speakeasy.avatar.AvatarId
import com.team96.speakeasy.avatar.AvatarMouth
import com.team96.speakeasy.avatar.AvatarPalette
import com.team96.speakeasy.avatar.AvatarPhase
import com.team96.speakeasy.avatar.AvatarPreference
import com.team96.speakeasy.avatar.AvatarPresentation

private data class RigColors(val skin: Color, val shadow: Color, val hair: Color, val shirt: Color, val accent: Color)

private fun colors(preference: AvatarPreference): RigColors {
    val identity = when (preference.avatarId) {
        AvatarId.MEERA -> RigColors(Color(0xFFB96F49), Color(0xFF955033), Color(0xFF2B2032), Color(0xFF168D92), Color(0xFFF07E6E))
        AvatarId.KAVIN -> RigColors(Color(0xFF9B5C3D), Color(0xFF78412E), Color(0xFF241C24), Color(0xFF386FC7), Color(0xFFF5C15B))
        AvatarId.NILA -> RigColors(Color(0xFF7E4C37), Color(0xFF613726), Color(0xFF3A253E), Color(0xFF9A5BC3), Color(0xFF55C8BB))
        AvatarId.PIPPIN -> RigColors(Color(0xFFE4974E), Color(0xFFBC6C35), Color(0xFF57382B), Color(0xFF168D92), Color(0xFFF07E6E))
    }
    return when (preference.palette) {
        AvatarPalette.CORAL_TEAL -> identity.copy(shirt = Color(0xFF168D92), accent = Color(0xFFF07E6E))
        AvatarPalette.SUNRISE -> identity.copy(shirt = Color(0xFFD86651), accent = Color(0xFFF4BE55))
        AvatarPalette.LOTUS -> identity.copy(shirt = Color(0xFF8B5BB5), accent = Color(0xFFE486A5))
    }
}

internal data class AvatarMotionEnvironment(val foreground:Boolean,val systemAnimations:Boolean)
/** The Android animation-off preference and actual activity lifecycle outrank decorative motion. */
@Composable internal fun rememberAvatarMotionEnvironment():AvatarMotionEnvironment {
 val lifecycle=LocalLifecycleOwner.current.lifecycle
 var environment by remember(lifecycle){mutableStateOf(AvatarMotionEnvironment(lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED),ValueAnimator.areAnimatorsEnabled()))}
 DisposableEffect(lifecycle){
  val observer=LifecycleEventObserver{_,event->when(event){
   Lifecycle.Event.ON_RESUME->environment=AvatarMotionEnvironment(true,ValueAnimator.areAnimatorsEnabled())
   Lifecycle.Event.ON_PAUSE,Lifecycle.Event.ON_STOP,Lifecycle.Event.ON_DESTROY->environment=environment.copy(foreground=false)
   else->Unit
  }}
  lifecycle.addObserver(observer);onDispose{lifecycle.removeObserver(observer)}
 }
 return environment
}

/** DEC-026/AVT-003..006: dependency-free native vector rig with bounded presentation states. */
@Composable
fun ExpressiveAvatar(
    preference: AvatarPreference,
    phase: AvatarPhase,
    modifier: Modifier = Modifier,
    speaking: Boolean = false,
    audioLevel: Float = 0f,
    greetingKey:Int=0,
) {
    val presentation = AvatarPresentation.forPhase(phase, preference.motion)
    val environment=rememberAvatarMotionEnvironment()
    val motion=avatarMotionSpec(preference.motion,phase,environment.foreground,environment.systemAnimations)
    val idleEnabled=motion.breathDistance>0f
    // Removed branches have no frame loop in Still, quiet states, background or system-off.
    val idle=if(idleEnabled)key(preference.avatarId,preference.motion,greetingKey){
        val transition=rememberInfiniteTransition(label="avatar idle")
        val breath=transition.animateFloat(0f,motion.breathDistance,infiniteRepeatable(tween(motion.breathHalfCycleMs),RepeatMode.Reverse),label="avatar breath")
        val blink=transition.animateFloat(0f,1f,infiniteRepeatable(tween(motion.blinkPeriodMs,easing=LinearEasing)),label="avatar blink")
        breath to blink
    }else rememberUpdatedState(0f) to rememberUpdatedState(0f)
    val greeting=remember(preference.avatarId,preference.motion,greetingKey){Animatable(0f)}
    var greeted by remember(preference.avatarId,preference.motion,greetingKey){mutableStateOf(false)}
    // Consume on start: cancellation must not become another greeting on resume.
    LaunchedEffect(greeting,idleEnabled){
        if(idleEnabled&&!greeted){greeted=true;greeting.snapTo(0f);greeting.animateTo(1f,tween(motion.greetingDurationMs,easing=LinearEasing))}
        else greeting.snapTo(1f)
    }
    val gesture=if(motion.gestureScale>0f&&phase!=AvatarPhase.IDLE)remember(phase,preference.motion){Animatable(0f)}else null
    if(gesture!=null)LaunchedEffect(gesture,motion.gestureScale,motion.gestureDurationMs){gesture.animateTo(motion.gestureScale,tween(motion.gestureDurationMs))}
    val mouth = AvatarPresentation.mouth(speaking, audioLevel)
    val label = "${preference.avatarId.displayName}, ${phase.name.lowercase()} practice guide"

    Canvas(modifier.fillMaxWidth().aspectRatio(320f / 390f).semantics { contentDescription = label }) {
        val sx = size.width / 320f
        val sy = size.height / 390f
        val wave=if(idleEnabled)avatarGreetingAmount(greeting.value)*motion.gestureScale else 0f
        val pose=if(wave>0f)AvatarGesture.EXPLAIN else presentation.gesture
        val amount=if(phase==AvatarPhase.IDLE)wave else gesture?.value?:0f
        val blink=if(idleEnabled)avatarBlinkAmount(idle.second.value)else 0f
        withTransform({ scale(sx, sy, Offset.Zero); translate(top = -idle.first.value) }) {
            if (preference.avatarId == AvatarId.PIPPIN) drawPippin(colors(preference), presentation.expression, pose, amount, mouth,blink)
            else drawHuman(preference.avatarId, colors(preference), presentation.expression, pose, amount, mouth,blink)
        }
    }
}

private fun DrawScope.drawHuman(id: AvatarId, c: RigColors, expression: AvatarExpression, gesture: AvatarGesture, amount: Float, mouth: AvatarMouth, blink:Float) {
    drawOval(Color(0x22342841), Offset(68f, 352f), Size(184f, 25f))
    drawArm(c, false, armDegrees(gesture, false) * amount)
    drawArm(c, true, armDegrees(gesture, true) * amount)
    drawPath(Path().apply { moveTo(82f, 366f); lineTo(101f, 267f); quadraticBezierTo(160f, 226f, 219f, 267f); lineTo(239f, 366f); close() }, c.shirt)
    drawPath(Path().apply { moveTo(128f, 252f); lineTo(160f, 290f); lineTo(192f, 252f); close() }, c.accent)
    drawRoundRect(c.skin, Offset(142f, 226f), Size(36f, 49f), androidx.compose.ui.geometry.CornerRadius(10f))

    if (id == AvatarId.NILA) {
        listOf(Offset(111f,72f),Offset(151f,54f),Offset(194f,70f),Offset(215f,107f),Offset(102f,110f)).forEach { drawCircle(c.hair, 31f, it) }
    } else {
        drawOval(c.hair, Offset(if (id == AvatarId.KAVIN) 91f else 88f, 35f), Size(if (id == AvatarId.KAVIN) 143f else 148f, if (id == AvatarId.KAVIN) 138f else 216f))
    }
    drawRoundRect(c.skin, Offset(141f, 202f), Size(38f, 65f), androidx.compose.ui.geometry.CornerRadius(8f))
    val headTilt = when (expression) { AvatarExpression.ATTENTIVE, AvatarExpression.REASSURING -> -2f; AvatarExpression.THINKING -> 3f; else -> 0f }
    rotate(headTilt * amount, Offset(160f, 188f)) {
        drawOval(c.skin, Offset(92f, 67f), Size(136f, 160f))
        drawPath(Path().apply { moveTo(96f, 116f); quadraticBezierTo(111f, 48f, 164f, 48f); quadraticBezierTo(216f, 49f, 230f, 116f); quadraticBezierTo(197f, 106f, 175f, 75f); quadraticBezierTo(145f, 107f, 96f, 116f); close() }, c.hair)
        drawFace(c, expression, mouth,blink=blink)
        if (id == AvatarId.MEERA) drawCircle(Color(0xFF9E294A), 4f, Offset(160f, 105f))
    }
}

private fun DrawScope.drawPippin(c: RigColors, expression: AvatarExpression, gesture: AvatarGesture, amount: Float, mouth: AvatarMouth, blink:Float) {
    drawOval(Color(0x22342841), Offset(70f, 352f), Size(180f, 25f))
    drawArm(c, false, armDegrees(gesture, false) * amount)
    drawArm(c, true, armDegrees(gesture, true) * amount)
    drawPath(Path().apply { moveTo(82f, 366f); lineTo(105f, 263f); quadraticBezierTo(160f, 228f, 215f, 263f); lineTo(238f, 366f); close() }, c.shirt)
    drawPath(Path().apply { moveTo(116f, 264f); lineTo(160f, 295f); lineTo(204f, 264f); lineTo(193f, 247f); lineTo(127f, 247f); close() }, c.accent)
    drawPath(Path().apply { moveTo(105f, 110f); lineTo(85f, 43f); lineTo(143f, 79f); close(); moveTo(215f, 110f); lineTo(235f, 43f); lineTo(177f, 79f); close() }, c.skin)
    drawPath(Path().apply { moveTo(101f, 85f); lineTo(93f, 57f); lineTo(122f, 79f); close(); moveTo(219f, 85f); lineTo(227f, 57f); lineTo(198f, 79f); close() }, Color(0xFFF3B5A4))
    drawOval(c.skin, Offset(85f, 69f), Size(150f, 158f))
    drawPath(Path().apply { moveTo(111f, 108f); quadraticBezierTo(160f, 57f, 209f, 108f); quadraticBezierTo(160f, 85f, 111f, 108f); close() }, Color(0x66FFF4DA))
    drawFace(c, expression, mouth, cat = true,blink=blink)
}

private fun DrawScope.drawArm(c: RigColors, right: Boolean, degrees: Float) {
    val pivot = Offset(if (right) 216f else 104f, 269f)
    rotate(degrees, pivot) {
        val left = if (right) 217f else 54f
        drawRoundRect(c.skin, Offset(left, 265f), Size(49f, 88f), androidx.compose.ui.geometry.CornerRadius(24f))
        drawCircle(c.skin, 18f, Offset(if (right) 261f else 59f, 342f))
    }
}

private fun armDegrees(gesture: AvatarGesture, right: Boolean): Float = when (gesture) {
    AvatarGesture.EXPLAIN, AvatarGesture.LISTEN -> if (right) -38f else 0f
    AvatarGesture.CELEBRATE -> if (right) -55f else 55f
    AvatarGesture.DEMONSTRATE -> if (right) 0f else 31f
    AvatarGesture.INVITE -> if (right) -18f else 18f
    else -> 0f
}

private fun DrawScope.drawFace(c: RigColors, expression: AvatarExpression, mouth: AvatarMouth, cat: Boolean = false,blink:Float=0f) {
    val eyeY = 149f
    val openness=(1f-blink.coerceIn(0f,1f)).coerceAtLeast(.05f)
    val eyeHeight = ((if (expression == AvatarExpression.JOY) 8f else 28f)*openness).coerceAtLeast(1.5f)
    val browLift = if (expression == AvatarExpression.ENCOURAGING || expression == AvatarExpression.ATTENTIVE) -3f else 0f
    drawOval(Color.White, Offset(118f, eyeY - eyeHeight / 2), Size(25f, eyeHeight))
    drawOval(Color.White, Offset(177f, eyeY - eyeHeight / 2), Size(25f, eyeHeight))
    withTransform({scale(1f,openness,Offset(160f,eyeY))}) {
        drawCircle(Color(0xFF332C31), 7f, Offset(132f, eyeY + 1f)); drawCircle(Color(0xFF332C31), 7f, Offset(188f, eyeY + 1f))
    }
    drawLine(Color(0xFF3A292A), Offset(116f, 128f + browLift), Offset(146f, 126f - browLift), 5f)
    drawLine(Color(0xFF3A292A), Offset(174f, 126f - browLift), Offset(204f, 128f + browLift), 5f)
    drawOval(Color(0x55ED887F), Offset(102f, 171f), Size(34f, 15f)); drawOval(Color(0x55ED887F), Offset(185f, 171f), Size(34f, 15f))
    if (cat) drawPath(Path().apply { moveTo(151f, 169f); lineTo(160f, 178f); lineTo(169f, 169f); close() }, Color(0xFF6E3D41))
    else drawLine(c.shadow, Offset(159f, 148f), Offset(155f, 171f), 3f)
    drawMouth(mouth)
}

private fun DrawScope.drawMouth(mouth: AvatarMouth) {
    val color = Color(0xFF71343F)
    when (mouth) {
        AvatarMouth.NEUTRAL -> drawArc(color, 8f, 164f, false, Offset(143f, 184f), Size(34f, 22f), style = Stroke(5f))
        AvatarMouth.M -> drawLine(color, Offset(145f, 195f), Offset(175f, 195f), 6f)
        AvatarMouth.A -> drawOval(color, Offset(145f, 181f), Size(30f, 27f))
        AvatarMouth.E -> drawOval(color, Offset(142f, 187f), Size(36f, 16f))
        AvatarMouth.O -> drawOval(color, Offset(150f, 181f), Size(20f, 28f))
    }
}
