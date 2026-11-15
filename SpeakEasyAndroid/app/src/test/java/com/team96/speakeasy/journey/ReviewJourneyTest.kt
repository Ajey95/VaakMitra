package com.team96.speakeasy.journey

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Test

class ReviewJourneyTest {
    @Test
    fun `DEC-058 preserves nineteen routes and appends six experimental words`() {
        assertEquals(25, StarterWords.all.size)
        assertEquals("அம்மா", StarterWords.all.first().tamil)
        assertEquals("Amma", StarterWords.all.first().transliteration)
        assertEquals("சேர்ந்து", StarterWords.byNumericLessonId(19)?.tamil)
        assertEquals("வீடு", StarterWords.all.last().tamil)
        assertEquals(25, StarterWords.all.map { it.id }.distinct().size)
        assertEquals(listOf("என்ன", "நான்", "இது", "எனக்கு", "கை", "வீடு"), StarterWords.all.takeLast(6).map { it.tamil })
    }

    @Test
    fun `MST-009 successful development preview advances without retrying the same word`() {
        assertEquals(2, nextStarterLessonId(1))
        assertEquals(19, nextStarterLessonId(18))
        assertEquals(20, nextStarterLessonId(19))
        assertNull(nextStarterLessonId(25))
        assertNull(nextStarterLessonId(0))
    }

    @Test
    fun `DEC-058 focused itinerary uses original numeric routes and ends at eighteen`() {
        assertEquals(18, StarterWords.focusedLessonIds.size)
        assertEquals(18, StarterWords.focusedLessonIds.distinct().size)
        assertEquals(13, nextStarterLessonId(2, focused = true))
        assertEquals(25, nextStarterLessonId(24, focused = true))
        assertNull(nextStarterLessonId(25, focused = true))
        assertNull(nextStarterLessonId(19, focused = true))
        assertEquals("என்ன", LocalPromptLibrary.wordExample("என்ன"))
    }

    @Test
    fun `DEC-025 local speech prompt accepts only catalogue targets`() {
        assertEquals("அம்மா", LocalPromptLibrary.wordExample("அம்மா"))
        assertNull(LocalPromptLibrary.wordExample("unrestricted text"))
    }

    @Test
    fun `DEC-020 caregiver plan clamps values to the supported child session bounds`() {
        val plan = normalizeCarePlan(
            CarePlan(childAlias = "  Kavi  ", age = 16, sessionMinutes = 40, focusMinutes = 30, interest = "  trains  ")
        )

        assertEquals("Kavi", plan.childAlias)
        assertEquals(14, plan.age)
        assertEquals(20, plan.sessionMinutes)
        assertEquals(8, plan.focusMinutes)
        assertEquals("trains", plan.interest)
        assertFalse(plan.focusMinutes >= plan.sessionMinutes)
    }

    @Test
    fun `CHK-001 unknown assignment date never fabricates a due date`() {
        val status = checkupStatus(
            nowEpochMillis = 2_000_000L,
            therapistAssigned = true,
            assignmentEpochMillis = null,
            lastCompletedEpochMillis = null,
        )

        assertEquals(CheckupState.SCHEDULE_UNESTABLISHED, status.state)
        assertNull(status.dueEpochMillis)
    }

    @Test
    fun `CHK-001 due clock is fourteen days after latest authority timestamp`() {
        val day = 86_400_000L
        val status = checkupStatus(
            nowEpochMillis = 31 * day,
            therapistAssigned = true,
            assignmentEpochMillis = 2 * day,
            lastCompletedEpochMillis = 20 * day,
        )

        assertEquals(CheckupState.DUE_SOON, status.state)
        assertEquals(34 * day, status.dueEpochMillis)
    }

    @Test
    fun `DEC-021 session summary counts only observed events and never invents a score`() {
        val report = summarizeSession(
            sessionId = "LOCAL-1",
            startedAtEpochMillis = 1_000L,
            endedAtEpochMillis = 91_000L,
            events = listOf(
                SessionEvent.Attempt("TA_WORD_0001", "MODEL_UNAVAILABLE"),
                SessionEvent.Attempt("TA_WORD_0001", "NO_SPEECH"),
                SessionEvent.Break,
                SessionEvent.Attempt("TA_WORD_0002", "MODEL_UNAVAILABLE"),
            ),
        )

        assertEquals(90, report.durationSeconds)
        assertEquals(3, report.attemptCount)
        assertEquals(2, report.uniqueWordCount)
        assertEquals(1, report.breakCount)
        assertEquals(3, report.unscorableCount)
        assertNull(report.accuracyPercent)
    }
}
