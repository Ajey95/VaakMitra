package com.team96.speakeasy.ui.screens

import android.Manifest
import android.content.pm.PackageManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.Text
import com.team96.speakeasy.ui.components.*
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.foundation.verticalScroll
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.core.content.ContextCompat
import androidx.navigation.NavController
import com.team96.speakeasy.audio.PeakOnlyRecorder
import com.team96.speakeasy.audio.PracticeAudioBoundary
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.team96.speakeasy.ui.components.AnimatedGradientBackground
import com.team96.speakeasy.ui.components.BouncyButton
import com.team96.speakeasy.ui.theme.GradientCalm
import com.team96.speakeasy.ui.theme.Sunny
import com.team96.speakeasy.ui.theme.Teal
import kotlinx.coroutines.delay

@Composable
fun CandleGameScreen(nav: NavController,preview:Boolean=false,input:com.team96.speakeasy.audio.CandleInput?=null) {
    val context = LocalContext.current
    val recorder = remember(input) { input ?: PeakOnlyRecorder() }

    var active by remember { mutableStateOf(false) }
    var progress by remember { mutableStateOf(0f) }   // 0 = full flame, 1 = blown out
    var blowing by remember { mutableStateOf(false) }
    var won by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    val boundary=remember{PracticeAudioBoundary({},{recorder.cancel()},{})}
    var pendingPermission by remember{mutableStateOf<Long?>(null)}
    val lifecycle=LocalLifecycleOwner.current.lifecycle
    DisposableEffect(lifecycle){
        val pause=LifecycleEventObserver{_,event->if(event==Lifecycle.Event.ON_PAUSE){active=false;blowing=false}}
        lifecycle.addObserver(boundary);lifecycle.addObserver(pause)
        onDispose{lifecycle.removeObserver(boundary);lifecycle.removeObserver(pause);boundary.close()}
    }

    fun startGame() {
        if(!boundary.isForeground)return
        progress = 0f; won = false; error = null
        if (recorder.start()) active = true else error = "Microphone is busy. Try again."
    }

    val micPermission = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        val valid=boundary.consumePermission(pendingPermission);pendingPermission=null
        if (valid && granted) startGame() else if(valid) error = "Microphone permission is needed for this optional activity."
    }

    fun tryStart() {
        if(preview)return
        if(input!=null){boundary.foreground();startGame();return}
        val has = ContextCompat.checkSelfPermission(context, Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED
        boundary.foreground()
        if (has) startGame() else {pendingPermission=boundary.requestPermission();if(pendingPermission!=null)micPermission.launch(Manifest.permission.RECORD_AUDIO)}
    }

    // Game loop: sample mic amplitude and shrink the flame as the child blows.
    LaunchedEffect(active) {
        if (!active) return@LaunchedEffect
        while (active && progress < 1f) {
            if(!recorder.isRunning){
                recorder.cancel();active=false;blowing=false
                error="Microphone stopped. Tap Start Blowing to try again."
                return@LaunchedEffect
            }
            val amp = recorder.amplitude() / 32767f
            blowing = amp > 0.18f
            if (blowing) progress = (progress + 0.05f).coerceAtMost(1f)
            else progress = (progress - 0.012f).coerceAtLeast(0f) // flame recovers slightly
            delay(70)
        }
        if (progress >= 1f) {
            recorder.cancel()
            active = false
            won = true
        }
    }

    HeritagePage {
      Column(Modifier.fillMaxSize().safeDrawingPadding()) {
        Column(Modifier.weight(1f).fillMaxWidth().verticalScroll(androidx.compose.foundation.rememberScrollState()).padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally) {
            Spacer(Modifier.height(34.dp))
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                BackCircle { recorder.cancel(); nav.popBackStack() }
                Spacer(Modifier.width(14.dp))
                Column {
                    Text("Candle Game", color = HeritageInk, fontFamily = FontFamily.Serif, fontSize = 26.sp, fontWeight = FontWeight.Bold)
                    Text("An optional, gentle breathing game", color = HeritageMuted, fontSize = 14.sp)
                }
            }

            Spacer(Modifier.height(24.dp))
            // Progress bar
            Box(
                Modifier.fillMaxWidth().height(16.dp).clip(RoundedCornerShape(10.dp)).background(HeritageCard)
            ) {
                Box(
                    Modifier.fillMaxWidth(progress).height(16.dp).clip(RoundedCornerShape(10.dp))
                        .background(Brush.horizontalGradient(listOf(Sunny, Color(0xFFFF7043))))
                )
            }
            Spacer(Modifier.height(8.dp))
            Text("${(progress * 100).toInt()}%", color = HeritageInk, fontWeight = FontWeight.Bold)

            Spacer(Modifier.height(20.dp))
            Box(Modifier.fillMaxWidth().height(320.dp), contentAlignment = Alignment.Center) {
                CandleArt(flame = 1f - progress)
            }

            when {
                won -> {
                    Text("You did it! Candle's out! 🎂", color = HeritageInk, fontSize = 20.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
                    Spacer(Modifier.height(14.dp))
                    BouncyButton("Play Again", listOf(Teal, Color(0xFF856B58))) { tryStart() }
                }
                active -> {
                    Text("Take a comfortable breath. Stop whenever you like.",color=HeritageInk,textAlign=TextAlign.Center)
                }
                else -> {
                    BouncyButton("Start Blowing", listOf(Sunny, Color(0xFFFFB74D))) { tryStart() }
                }
            }
            error?.let {
                Spacer(Modifier.height(10.dp))
                Text(it, color = HeritageMaroon, fontWeight = FontWeight.Medium, textAlign = TextAlign.Center)
            }
            Spacer(Modifier.height(16.dp))
        }
        if(active){
            Column(Modifier.fillMaxWidth().background(HeritagePaper).padding(horizontal=20.dp,vertical=12.dp),horizontalAlignment=Alignment.CenterHorizontally){
                Text("Listening · microphone on",color=HeritageMaroon,fontWeight=FontWeight.Bold,fontSize=16.sp)
                Spacer(Modifier.height(8.dp))
                HeritageButton("Break / Stop",onClick={boundary.background();active=false;blowing=false},danger=true,modifier=Modifier.fillMaxWidth())
            }
        }
      }

    }
}

@Composable
private fun CandleArt(flame: Float) {

    Canvas(Modifier.size(220.dp, 320.dp)) {
        val w = size.width
        val h = size.height
        val candleW = w * 0.34f
        val candleLeft = (w - candleW) / 2f
        val candleTop = h * 0.42f

        // Candle body (striped fun colors)
        drawRoundRect(
            brush = Brush.verticalGradient(listOf(Color(0xFFB88D54), Color(0xFF9B643D))),
            topLeft = Offset(candleLeft, candleTop),
            size = Size(candleW, h - candleTop),
            cornerRadius = androidx.compose.ui.geometry.CornerRadius(18f, 18f)
        )
        // Wick
        drawRect(
            color = Color(0xFF4A4A4A),
            topLeft = Offset(w / 2f - 2f, candleTop - 18f),
            size = Size(4f, 18f)
        )
        // Flame (scales with `flame` 0..1)
        if (flame > 0.02f) {
            val flameH = 70f * flame
            val flameW = 34f * flame
            val cx = w / 2f
            val baseY = candleTop - 18f
            // Outer flame
            drawOval(
                brush = Brush.verticalGradient(listOf(Color(0xFFFFE082), Color(0xFFFF7043))),
                topLeft = Offset(cx - flameW / 2f, baseY - flameH),
                size = Size(flameW, flameH)
            )
            // Inner flame
            drawOval(
                color = Color(0xFFFFF59D),
                topLeft = Offset(cx - flameW / 4f, baseY - flameH * 0.6f),
                size = Size(flameW / 2f, flameH * 0.5f)
            )
            // Glow
            drawCircle(
                color = Color(0x33FFD54F),
                radius = flameH,
                center = Offset(cx, baseY - flameH / 2f)
            )
        } else {
            // Smoke puff when out
            drawCircle(color = Color(0x55BDBDBD), radius = 14f, center = Offset(w / 2f, candleTop - 40f))
            drawCircle(color = Color(0x33BDBDBD), radius = 18f, center = Offset(w / 2f + 10f, candleTop - 70f))
        }
    }
}
