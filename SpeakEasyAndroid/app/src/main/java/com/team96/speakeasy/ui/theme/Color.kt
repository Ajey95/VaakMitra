package com.team96.speakeasy.ui.theme

import androidx.compose.ui.graphics.Color

/** DEC-027/UX-010: calm-market structure translated to the approved snuff/maroon system. */
val Maroon = Color(0xFF6F2338)
val MaroonDark = Color(0xFF4B1727)
val Snuff = Color(0xFF9A7A63)
val SnuffDark = Color(0xFF705747)
val SnuffLight = Color(0xFFC7AE98)
val WarmCream = Color(0xFFFFF8EF)
val Parchment = Color(0xFFF1E3D5)
val DustyRose = Color(0xFFA55366)
val MutedOlive = Color(0xFF7C7561)

// Compatibility aliases keep inherited screens semantic while removing the saturated rainbow.
val Purple = Maroon
val PurpleDark = MaroonDark
val Pink = DustyRose
val HotPink = Color(0xFF8C3B50)
val Orange = Color(0xFFA76849)
val Mango = Color(0xFFB8865E)
val Sunny = Color(0xFFD5B482)
val Lemon = Color(0xFFEADBC7)
val Teal = SnuffDark
val Mint = SnuffLight
val Sky = Color(0xFFAC8D78)
val Ocean = Color(0xFF7F604F)
val Grass = Color(0xFFA29179)
val Leaf = MutedOlive
val Coral = Color(0xFFA95E5E)

val InkDark = Color(0xFF382726)
val InkSoft = Color(0xFF6E5952)
val CloudWhite = WarmCream
val CardWhite = Color(0xFFFFFFFF)

// Deep, low-saturation backgrounds keep white child-facing copy readable.
val GradientPlay = listOf(MaroonDark, Maroon, SnuffDark)
val GradientCalm = listOf(Color(0xFF4D3B35), SnuffDark, Color(0xFF775165))
val GradientWarm = listOf(Color(0xFF704535), Maroon, Color(0xFF8A5E4D))
val GradientStar = listOf(SnuffLight, Snuff, Maroon)

// Per-word cards stay varied enough to scan while remaining inside the warm family.
val LessonColors = listOf(
    listOf(Color(0xFF8E3F52), MaroonDark),
    listOf(Color(0xFF9B6A55), Color(0xFF704535)),
    listOf(Color(0xFF80685A), Color(0xFF59463E)),
    listOf(Color(0xFF877D67), Color(0xFF5F5B49)),
    listOf(Color(0xFFA8645D), Color(0xFF78433F)),
    listOf(Color(0xFF8C5B70), Color(0xFF63394D)),
)
