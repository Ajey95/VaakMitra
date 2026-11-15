package com.team96.speakeasy.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.outlined.StarBorder
import androidx.compose.material3.Icon
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.drawscope.DrawScope
import androidx.compose.ui.unit.dp
import com.team96.speakeasy.ui.theme.Sunny
import kotlin.math.cos
import kotlin.math.sin

/**
 * DEC-027/UX-010: a slow, low-amplitude warm gradient; content does not depend on motion.
 */
@Composable
fun AnimatedGradientBackground(
    colors: List<Color>,
    modifier: Modifier = Modifier,
    content: @Composable () -> Unit = {}
) {
    Box(modifier.fillMaxSize().background(Brush.verticalGradient(colors))) {
        Canvas(Modifier.fillMaxSize()) {
            val unit=28.dp.toPx()
            var x=0f
            while(x<size.width){
                val border=Path().apply{moveTo(x,size.height-14.dp.toPx());lineTo(x+unit/2,size.height-5.dp.toPx());lineTo(x+unit,size.height-14.dp.toPx())}
                drawPath(border,Color(0xFFE7CC95).copy(alpha=.22f),style=androidx.compose.ui.graphics.drawscope.Stroke(1.4.dp.toPx()))
                x+=unit
            }
        }
        content()
    }
}

/** Quiet translucent forms inspired by the owned calm-market backdrop language. */
@Composable
private fun FloatingBlobs() {
    val t = rememberInfiniteTransition(label = "blobs")
    val phase by t.animateFloat(
        initialValue = 0f,
        targetValue = (2 * Math.PI).toFloat(),
        animationSpec = infiniteRepeatable(tween(12000, easing = LinearEasing)),
        label = "phase"
    )
    Canvas(Modifier.fillMaxSize()) {
        val blobs = listOf(
            Triple(0.18f, 0.20f, 120f),
            Triple(0.82f, 0.16f, 80f),
            Triple(0.70f, 0.55f, 150f),
            Triple(0.20f, 0.75f, 100f),
            Triple(0.90f, 0.85f, 70f),
        )
        blobs.forEachIndexed { i, (fx, fy, r) ->
            val dx = (cos((phase + i).toDouble()) * 24.0).toFloat()
            val dy = (sin((phase * 1.3f + i).toDouble()) * 28.0).toFloat()
            drawCircleBlob(
                cx = size.width * fx + dx,
                cy = size.height * fy + dy,
                radius = r,
            )
        }
    }
}

private fun DrawScope.drawCircleBlob(cx: Float, cy: Float, radius: Float) {
    drawCircle(
        color = Color.White.copy(alpha = 0.10f),
        radius = radius,
        center = Offset(cx, cy)
    )
}

/** A row of stars (filled / outlined) used for difficulty and rewards. */
@Composable
fun StarRow(
    filled: Int,
    total: Int = 3,
    starSize: Int = 22,
    color: Color = Sunny,
    modifier: Modifier = Modifier
) {
    androidx.compose.foundation.layout.Row(modifier) {
        repeat(total) { i ->
            if (i < filled) {
                Icon(
                    Icons.Filled.Star,
                    contentDescription = null,
                    tint = color,
                    modifier = Modifier.size(starSize.dp)
                )
            } else {
                Icon(
                    Icons.Outlined.StarBorder,
                    contentDescription = null,
                    tint = Color.White.copy(alpha = 0.55f),
                    modifier = Modifier.size(starSize.dp)
                )
            }
        }
    }
}

/** Reusable circle shape accessor (kept here so screens share one import). */
val Circle = CircleShape
