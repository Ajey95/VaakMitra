package com.team96.speakeasy.audio

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

class LocalWordPracticeTest {
    @Test fun dec079LearnerFeedbackHasNoDebugInstructionsOrClaimedScore() {
        for(result in listOf("DEV_PHONEMES","DEV_MATCH","DEV_TRY_AGAIN","DEV_UNCERTAIN","DEV_UNAVAILABLE")) {
            val outcome=LocalWordOutcome(reason="MODEL_UNAVAILABLE",developmentResult=result,predictedPhonemes=listOf("a"))
            val presentation=LocalWordPractice.present(outcome)
            assertFalse(Regex("experimental|development|engineering|preview|backend|UNSCORABLE|DEV_",RegexOption.IGNORE_CASE)
                .containsMatchIn(presentation.title+" "+presentation.guidance))
            assertNull(presentation.scoreLabel)
            assertEquals("UNSCORABLE",outcome.decision)
        }
    }
    @Test fun dec058PhonemePreviewCanVoluntarilyAdvanceWithoutAChildScore() {
        val outcome=LocalWordOutcome(reason="PHONEME_TOKENS",developmentResult="DEV_PHONEMES",predictedPhonemes=listOf("a"))
        val presentation=LocalWordPractice.present(outcome)
        assertEquals("Next word",presentation.primaryActionLabel)
        assertTrue(presentation.canAdvancePractice)
        assertEquals("UNSCORABLE",outcome.decision)
        assertNull(presentation.scoreLabel)
        assertFalse(LocalWordPractice.present(LocalWordOutcome(reason="NO_SPEECH")).canAdvancePractice)
    }
    @Test fun gov001NoUnvalidatedCaptureInReleaseBuild() {
        assertTrue(LocalWordPractice.canCapture(isDebugBuild = true))
        assertFalse(LocalWordPractice.canCapture(isDebugBuild = false))
    }

    @Test fun dec013ValidCaptureWithoutStudentAbstainsWithoutScore() {
        val voiced = ShortArray(16000) { if (it % 2 == 0) 3000 else -3000 }
        val outcome = LocalWordPractice.assess("அம்மா", voiced)
        assertEquals("UNSCORABLE", outcome.decision)
        assertEquals("MODEL_UNAVAILABLE", outcome.reason)
        assertNull(outcome.wordMatchProbability)
    }

    @Test fun au003ShortCaptureCannotBecomeAWordResult() {
        val outcome = LocalWordPractice.assess("அம்மா", ShortArray(3200) { 3000 })
        assertEquals("TOO_SHORT", outcome.reason)
        assertNull(outcome.wordMatchProbability)
    }

    @Test fun au004SilenceAndClippingAreRejectedLocally() {
        assertEquals("NO_SPEECH", LocalWordPractice.assess("அம்மா", ShortArray(16000)).reason)
        assertEquals("CLIPPED", LocalWordPractice.assess("அம்மா", ShortArray(16000) { Short.MAX_VALUE }).reason)
    }

    @Test fun au002UnsupportedRateAndMissingTargetAbstain() {
        val voiced = ShortArray(16000) { 3000 }
        assertEquals("UNSUPPORTED_SAMPLE_RATE", LocalWordPractice.assess("அம்மா", voiced, 8000).reason)
        assertEquals("TARGET_UNAVAILABLE", LocalWordPractice.assess("", voiced).reason)
    }

    @Test fun fus007MissingModelProducesNeutralRetryCopyWithoutAccuracy() {
        val presentation = LocalWordPractice.present(LocalWordOutcome(reason = "MODEL_UNAVAILABLE"))
        assertEquals("Nice practice", presentation.title)
        assertEquals("Try the whole word again when you are ready.", presentation.guidance)
        assertNull(presentation.scoreLabel)
    }

    @Test fun mst009InvalidCaptureExplainsWhyTheAttemptWasNotChecked() {
        val presentation = LocalWordPractice.present(LocalWordOutcome(reason = "NO_SPEECH"))
        assertEquals("I couldn't hear the word", presentation.title)
        assertEquals("Keep the phone about a hand-span away, wait for Listening, then say the whole word.", presentation.guidance)
        assertEquals("NO_SPEECH", presentation.detailCode)
    }

    @Test fun mst009TooShortCaptureRequestsTheWholeWordInsteadOfGenericRetry() {
        val presentation = LocalWordPractice.present(LocalWordOutcome(reason = "TOO_SHORT"))
        assertEquals("I need the whole word", presentation.title)
        assertEquals("TOO_SHORT", presentation.detailCode)
    }

    @Test fun mst007DevelopmentMatchIsLabeledWithoutChildScore() {
        val presentation = LocalWordPractice.present(
            LocalWordOutcome(reason = "ADULT_ENGINEERING_MATCH", developmentResult = "DEV_MATCH")
        )
        assertEquals("Nice practice", presentation.title)
        assertFalse(presentation.guidance.contains("development check"))
        assertFalse(presentation.guidance.contains("say the whole word once more", ignoreCase = true))
        assertEquals("Continue", presentation.primaryActionLabel)
        assertNull(presentation.scoreLabel)
    }

    @Test fun mst007DevelopmentRetryNeverClaimsFailureOrAccuracy() {
        val presentation = LocalWordPractice.present(
            LocalWordOutcome(reason = "ADULT_ENGINEERING_MISMATCH", developmentResult = "DEV_TRY_AGAIN")
        )
        assertEquals("Let's practise once more", presentation.title)
        assertFalse(presentation.guidance.contains("failed", ignoreCase = true))
        assertNull(presentation.scoreLabel)
    }

    @Test fun mst007LowMarginAsksForCleanRecapture() {
        val presentation = LocalWordPractice.present(
            LocalWordOutcome(reason = "LOW_MARGIN", developmentResult = "DEV_UNCERTAIN")
        )
        assertEquals("I couldn't tell clearly", presentation.title)
        assertNull(presentation.scoreLabel)
    }
}
