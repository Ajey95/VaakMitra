package com.team96.speakeasy.journey

import java.security.MessageDigest
import java.util.Locale

/** DEC-053: participation only, never pronunciation mastery or inferred attention. */
data class LetterProgress private constructor(val completedCount: Int) {
    val nextLetter: TamilLetter? get() = TamilAlphabet.all.getOrNull(completedCount)
    fun canOpen(id: String): Boolean {
        val index = TamilAlphabet.all.indexOfFirst { it.id == id }
        return index >= 0 && index <= completedCount
    }
    fun isPractised(id: String): Boolean {
        val index = TamilAlphabet.all.indexOfFirst { it.id == id }
        return index >= 0 && index < completedCount
    }
    fun complete(id: String): LetterProgress =
        if (nextLetter?.id == id) LetterProgress(completedCount + 1) else this
    companion object {
        fun restore(count: Int, version: Int = 1): LetterProgress =
            LetterProgress(if (version == 1 && count in 0..247) count else 0)
    }
}

data class LetterPracticeSettings(val roundSize: Int = 3, val rewardsEnabled: Boolean = true) {
    companion object {
        fun normalize(size: Int, rewards: Boolean) = LetterPracticeSettings(if (size in listOf(1, 3, 5)) size else 3, rewards)
    }
}

data class LetterJourneySnapshot(
    val progress: LetterProgress = LetterProgress.restore(0),
    val settings: LetterPracticeSettings = LetterPracticeSettings(),
)

/** Account and child aliases are scoped in memory; only the digest enters preference keys. */
fun letterProfileScope(account: String, child: String): String {
    val a = account.trim().lowercase(Locale.ROOT)
    val c = child.trim().lowercase(Locale.ROOT)
    val raw = "${a.length}:$a${c.length}:$c"
    return MessageDigest.getInstance("SHA-256").digest(raw.toByteArray(Charsets.UTF_8))
        .take(16).joinToString("") { "%02x".format(it) }
}

enum class LetterPause { NONE, USER, ROUND, FOCUS, BACKGROUND, END, SUPPORT }

/** DEC-054/020: elapsed foreground activity supports voluntary breaks, not attention measurement. */
data class LetterSession private constructor(
    val roundSize: Int,
    val focusMs: Long,
    val sessionMs: Long,
    val roundPractised: Int = 0,
    val totalActiveMs: Long = 0,
    val blockActiveMs: Long = 0,
    val reason: LetterPause = LetterPause.NONE,
) {
    val paused: Boolean get() = reason != LetterPause.NONE
    val ended: Boolean get() = reason == LetterPause.END
    fun practice(): LetterSession {
        if (paused) return this
        val count = minOf(roundSize, roundPractised + 1)
        return copy(roundPractised = count, reason = if (count == roundSize) LetterPause.ROUND else LetterPause.NONE)
    }
    fun tick(deltaMs: Long): LetterSession {
        if (paused || deltaMs <= 0) return this
        val delta = minOf(deltaMs, sessionMs - totalActiveMs)
        val total = totalActiveMs + delta
        val block = blockActiveMs + delta
        return copy(totalActiveMs = total, blockActiveMs = block,
            reason = when { total >= sessionMs -> LetterPause.END; block >= focusMs -> LetterPause.FOCUS; else -> LetterPause.NONE })
    }
    fun pause(why: LetterPause = LetterPause.USER): LetterSession =
        if (ended || paused || why == LetterPause.NONE) this else copy(reason = why)
    fun resume(): LetterSession =
        if (ended || !paused) this else copy(roundPractised = 0, blockActiveMs = 0, reason = LetterPause.NONE)
    fun snapshot(): List<Long> = listOf(roundSize.toLong(), focusMs, sessionMs, roundPractised.toLong(), totalActiveMs, blockActiveMs, reason.ordinal.toLong())
    companion object {
        fun start(roundSize: Int, focusMs: Long, sessionMs: Long): LetterSession {
            require(sessionMs in 1..1_200_000 && focusMs in 1..sessionMs)
            return LetterSession(LetterPracticeSettings.normalize(roundSize, true).roundSize, focusMs, sessionMs)
        }
        fun restore(values: List<Long>): LetterSession {
            val fallback = start(3, 120000, 300000).pause(LetterPause.BACKGROUND)
            if (values.size != 7 || values[0] !in listOf(1L, 3L, 5L) || values[2] !in 1..1_200_000L || values[1] !in 1..values[2] || values[3] !in 0..values[0] || values[4] !in 0..values[2] || values[5] !in 0..values[4] || values[6] !in 0L..LetterPause.entries.lastIndex.toLong()) return fallback
            val saved = LetterSession(values[0].toInt(), values[1], values[2], values[3].toInt(), values[4], values[5], LetterPause.entries[values[6].toInt()])
            return if (saved.totalActiveMs >= saved.sessionMs) saved.copy(reason = LetterPause.END) else saved
        }
    }
}
