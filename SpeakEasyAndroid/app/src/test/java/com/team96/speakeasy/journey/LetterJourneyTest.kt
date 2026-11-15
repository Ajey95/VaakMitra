package com.team96.speakeasy.journey

import org.junit.Assert.*
import org.junit.Test

/** DEC-053/054: explicit practice, sequential unlock, voluntary break, no inference. */
class LetterJourneyTest {
    @Test fun dec053OnlyNextLetterUnlocksAndReplayCannotSkip() {
        var progress = LetterProgress.restore(0)
        assertTrue(progress.canOpen(TamilAlphabet.all[0].id))
        assertFalse(progress.canOpen(TamilAlphabet.all[1].id))
        assertEquals(progress, progress.complete(TamilAlphabet.all[2].id))
        assertEquals(progress, progress.complete("unknown"))
        TamilAlphabet.all.forEachIndexed { i, letter ->
            assertEquals(i, progress.completedCount)
            assertEquals(letter, progress.nextLetter)
            progress = progress.complete(letter.id)
            assertTrue(progress.isPractised(letter.id))
            assertEquals(progress, progress.complete(letter.id))
        }
        assertEquals(247, progress.completedCount)
        assertNull(progress.nextLetter)
        assertFalse(progress.canOpen("unknown"))
    }
    @Test fun dec053CorruptProgressFailsClosed() {
        for (bad in listOf(-1,248,Int.MAX_VALUE)) assertEquals(0, LetterProgress.restore(bad).completedCount)
        assertEquals(31, LetterProgress.restore(31).completedCount)
        assertEquals(0, LetterProgress.restore(31, version = 99).completedCount)
        assertNotEquals(letterProfileScope("a", "child"), letterProfileScope("b", "child"))
        assertNotEquals(letterProfileScope("a", "first"), letterProfileScope("a", "second"))
        assertEquals(letterProfileScope("a", "child"), letterProfileScope("a", "child"))
    }
    @Test fun dec054RoundEndsWithBreakAndPauseDoesNotAdvanceTime() {
        var session = LetterSession.start(roundSize = 3, focusMs = 120000, sessionMs = 300000)
        session = session.practice().practice().practice()
        assertTrue(session.paused)
        assertEquals(LetterPause.ROUND, session.reason)
        assertEquals(session, session.tick(10000))
        val resumed = session.resume()
        assertFalse(resumed.paused)
        assertEquals(0, resumed.roundPractised)
        assertEquals(LetterPause.USER, resumed.pause().reason)
        assertEquals(LetterPause.BACKGROUND, resumed.pause(LetterPause.BACKGROUND).reason)
    }
    @Test fun dec054ForegroundBudgetBreakAndTerminalSessionCannotResume() {
        var session = LetterSession.start(roundSize = 3, focusMs = 120000, sessionMs = 300000)
        session = session.tick(120000)
        assertEquals(LetterPause.FOCUS, session.reason)
        assertEquals(120000L, session.totalActiveMs)
        session = session.resume().tick(120000).resume().tick(60000)
        assertTrue(session.ended)
        assertEquals(LetterPause.END, session.reason)
        assertEquals(session, session.resume())
        assertEquals(session, session.practice())
        assertEquals(300000L, session.totalActiveMs)
    }
    @Test fun dec054SessionRestoresWithoutLosingBudgetOrBreak() {
        val paused = LetterSession.start(3,120000,300000).tick(50000).practice().pause(LetterPause.BACKGROUND)
        assertEquals(paused, LetterSession.restore(paused.snapshot()))
        assertTrue(LetterSession.restore(emptyList()).paused)
        assertEquals(LetterPause.END, LetterSession.restore(LetterSession.start(1,1,1).tick(1).snapshot()).reason)
    }
    @Test fun dec054SettingsAndInvalidClockInputStayBounded() {
        assertEquals(3, LetterPracticeSettings.normalize(999, true).roundSize)
        assertFalse(LetterPracticeSettings.normalize(1, false).rewardsEnabled)
        val session = LetterSession.start(3,120000,300000)
        assertEquals(session, session.tick(-100))
        assertEquals(session.pause(), session.pause().practice())
    }
}
