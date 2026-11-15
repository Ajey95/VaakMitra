package com.team96.speakeasy.ui.components

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.animation.core.updateTransition
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.Stable
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import com.team96.speakeasy.ui.theme.Pink
import com.team96.speakeasy.ui.theme.Purple
import com.team96.speakeasy.ui.theme.Sky
import com.team96.speakeasy.ui.theme.Sunny
import com.team96.speakeasy.ui.theme.Teal
import com.team96.speakeasy.ui.theme.Coral
import kotlin.random.Random

@Stable
private data class Particle(
    val xFrac: Float,
    val delay: Float,
    val color: Color,
    val size: Float,
    val drift: Float,
    val rotationSpeed: Float,
)

/**
 * A celebratory confetti burst overlay. Pass [play] = true to start it falling.
 * Drives off a single transition so it animates smoothly without timers.
 */
@Composable
fun ConfettiOverlay(play: Boolean, modifier: Modifier = Modifier) {
    val palette = listOf(Purple, Pink, Sky, Sunny, Teal, Coral)
    val particles = remember {
        List(70) { i ->
            Particle(
                xFrac = Random.nextFloat(),
                delay = Random.nextFloat() * 0.25f,
                color = palette[i % palette.size],
                size = 10f + Random.nextFloat() * 14f,
                drift = (Random.nextFloat() - 0.5f) * 200f,
                rotationSpeed = (Random.nextFloat() - 0.5f) * 12f,
            )
        }
    }
    val transition = updateTransition(targetState = play, label = "confetti")
    val progress by transition.animateFloat(
        transitionSpec = { tween(1800, easing = LinearEasing) },
        label = "fall"
    ) { if (it) 1f else 0f }

    if (progress <= 0f) return

    Canvas(modifier.fillMaxSize()) {
        particles.forEach { p ->
            val local = ((progress - p.delay) / (1f - p.delay)).coerceIn(0f, 1f)
            if (local <= 0f) return@forEach
            val x = size.width * p.xFrac + p.drift * local
            val y = -40f + (size.height + 80f) * local
            val alpha = (1f - local).coerceIn(0f, 1f)
            drawConfettiPiece(p.color.copy(alpha = alpha), Offset(x, y), p.size)
        }
    }
}

private fun androidx.compose.ui.graphics.drawscope.DrawScope.drawConfettiPiece(
    color: Color, center: Offset, s: Float
) {
    drawRect(
        color = color,
        topLeft = Offset(center.x - s / 2, center.y - s / 2),
        size = Size(s, s * 0.6f)
    )
}
