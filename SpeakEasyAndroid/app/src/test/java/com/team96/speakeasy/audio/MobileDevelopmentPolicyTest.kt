package com.team96.speakeasy.audio

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test

/** DEC-028/MST-007: review evidence never becomes a child score. */
class MobileDevelopmentPolicyTest {
    private val calibration = MobileEngineeringCalibration(
        labels = listOf("TA_WORD_0001", "OTHER"),
        lowThresholds = mapOf("TA_WORD_0001" to .35),
        highThresholds = mapOf("TA_WORD_0001" to .75),
        minimumMargin = .10,
        minimumSimilarity = .60,
    )
    private val references = mapOf("TA_WORD_0001" to floatArrayOf(1f, 0f))

    @Test fun mst007ExactDevelopmentBranchesRemainOfficiallyUnscorable() {
        val match = MobileDevelopmentPolicy.evaluate("TA_WORD_0001", floatArrayOf(.95f, .05f), floatArrayOf(1f, 0f), references, calibration)
        assertEquals("DEV_MATCH", match.developmentResult)
        assertEquals("UNSCORABLE", match.decision)
        assertNull(match.wordMatchProbability)

        assertEquals("DEV_TRY_AGAIN", MobileDevelopmentPolicy.evaluate("TA_WORD_0001", floatArrayOf(.1f, .9f), floatArrayOf(0f, 1f), references, calibration).developmentResult)
        assertEquals("DEV_UNCERTAIN", MobileDevelopmentPolicy.evaluate("TA_WORD_0001", floatArrayOf(.52f, .48f), floatArrayOf(1f, 0f), references, calibration).developmentResult)
        assertEquals("DEV_UNAVAILABLE", MobileDevelopmentPolicy.evaluate("MISSING", floatArrayOf(.95f, .05f), floatArrayOf(1f, 0f), references, calibration).developmentResult)
    }
}

