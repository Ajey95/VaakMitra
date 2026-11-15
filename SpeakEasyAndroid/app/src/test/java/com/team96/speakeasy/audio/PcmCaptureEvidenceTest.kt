package com.team96.speakeasy.audio

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class PcmCaptureEvidenceTest {
    @Test fun mst009AllZeroCaptureIsReportedAsSilentPcm() {
        val evidence = PcmCaptureEvidence.analyze(ShortArray(16_000))

        assertEquals(16_000, evidence.sampleCount)
        assertEquals(0, evidence.peakAbsolute)
        assertEquals(0.0, evidence.rms, 0.0)
        assertEquals(0.0, evidence.nonZeroRatio, 0.0)
        assertTrue(evidence.isSilent)
    }

    @Test fun mst009AudibleCaptureIsNotCollapsedIntoNoSpeech() {
        val evidence = PcmCaptureEvidence.analyze(
            ShortArray(16_000) { index -> if (index % 2 == 0) 3_000 else -3_000 },
        )

        assertEquals(3_000, evidence.peakAbsolute)
        assertEquals(3_000.0, evidence.rms, 0.001)
        assertEquals(1.0, evidence.nonZeroRatio, 0.0)
        assertFalse(evidence.isSilent)
    }

    @Test fun mst009VeryLowLevelCaptureIsReportedAsSilentPcm() {
        val evidence = PcmCaptureEvidence.analyze(ShortArray(16_000) { 8 })

        assertTrue(evidence.isSilent)
    }

    @Test fun mst009VadEvidencePreservesRejectionCause() {
        val rejected = SpeechVadEvidence(
            maximumProbability = 0.42f,
            speechSamples = 2_560,
            sampleRate = 16_000,
            threshold = 0.5,
            minimumSpeechMs = 200,
        )
        val accepted = rejected.copy(speechSamples = 3_584, maximumProbability = 0.81f)

        assertEquals(160L, rejected.speechMilliseconds)
        assertFalse(rejected.hasEnoughSpeech)
        assertEquals(224L, accepted.speechMilliseconds)
        assertTrue(accepted.hasEnoughSpeech)
    }

    @Test fun mst001ModelInputUsesDetectedSpeechInsteadOfEightSecondCaptureCentre() {
        val capture = ShortArray(10_000) { it.toShort() }
        val evidence = SpeechVadEvidence(
            maximumProbability = 0.99f,
            speechSamples = 2_000,
            sampleRate = 16_000,
            threshold = 0.5,
            minimumSpeechMs = 200,
            firstSpeechSample = 3_000,
            lastSpeechSampleExclusive = 5_000,
        )

        val speechWindow = evidence.extractSpeech(capture, paddingSamples = 1_600)

        assertEquals(5_200, speechWindow.size)
        assertEquals(1_400, speechWindow.first().toInt())
        assertEquals(6_599, speechWindow.last().toInt())
    }
}
