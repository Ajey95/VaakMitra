package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test

class BackboneGuidanceTest {
    @Test fun optionalHelpNeverBlocksProgressOrClaimsTheChildMadeAnError() {
        val outcome=LocalWordOutcome(reason="PHONEME_TOKENS",developmentResult="DEV_PHONEMES",
            predictedPhonemes=listOf("a","m","aː"),supportAction="adult_example")
        val view=LocalWordPractice.present(outcome)
        assertEquals("UNSCORABLE",outcome.decision);assertTrue(view.canAdvancePractice)
        assertEquals("Next word",view.primaryActionLabel);assertNull(view.scoreLabel)
        assertTrue(view.guidance.contains("Listen"));assertFalse(view.guidance.contains("incorrect",true))
        assertEquals("a m aː",view.tokenSequence)
    }
}
