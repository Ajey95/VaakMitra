package com.team96.speakeasy.audio

import android.util.Log
import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import org.junit.runner.RunWith
import kotlin.math.abs
import kotlin.math.sin

/** DEC-028/MST-006..009: execute the shipped hashes and native ORT runtime on Android. */
@RunWith(AndroidJUnit4::class)
class MobileStudentInstrumentedTest {
    @Test fun mst006ShippedBundleVerifiesAndStudentExecutes() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val bundle = AndroidMobileBundleLoader.load(context)
        assertFalse(bundle.manifest.approvedForChildScoring)
        assertFalse(bundle.manifest.releaseBuildEnabled)
        assertEquals(20, bundle.manifest.labels.size)

        OnnxMobileWordStudent(bundle.modelBytes).use { student ->
            val latenciesMs = mutableListOf<Long>()
            lateinit var output: MobileStudentOutput
            repeat(5) {
                val started = System.nanoTime()
                output = student.infer(FloatArray(32_000))
                latenciesMs += (System.nanoTime() - started) / 1_000_000
            }
            assertEquals(20, output.probabilities.size)
            assertEquals(64, output.embedding.size)
            assertTrue(abs(output.probabilities.sum() - 1f) < 0.0001f)
            assertTrue("five model passes must remain bounded: $latenciesMs", latenciesMs.max() < 5_000)
            Log.i("VaakMitraEvidence", "MST-009 five-pass student latency ms=$latenciesMs")
        }
    }

    @Test fun mst008FullOfflinePipelineKeepsOfficialDecisionUnscorable() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val voiceLike = ShortArray(16_000) { index ->
            val envelope = if (index < 1_000 || index > 15_000) 0.0 else 1.0
            (envelope * 7_000.0 * (sin(index * .047) + .35 * sin(index * .103))).toInt().toShort()
        }
        val started = System.nanoTime()
        val outcome = MobileWordPracticeEngine.create(context, enabled = true).use { engine ->
            engine.assess("TA_WORD_0001", voiceLike)
        }
        val latencyMs = (System.nanoTime() - started) / 1_000_000

        assertEquals("UNSCORABLE", outcome.decision)
        assertNull(outcome.wordMatchProbability)
        assertTrue("native VAD/model execution must not be hidden as unavailable", outcome.reason != "MODEL_UNAVAILABLE")
        assertTrue(outcome.developmentResult in setOf("DEV_MATCH", "DEV_TRY_AGAIN", "DEV_UNCERTAIN", "DEV_UNAVAILABLE", "DEV_PHONEMES"))
        assertTrue("runtime should complete in a bounded review window: ${latencyMs}ms", latencyMs < 30_000)
    }
}
