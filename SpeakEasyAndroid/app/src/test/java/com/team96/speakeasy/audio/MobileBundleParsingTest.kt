package com.team96.speakeasy.audio

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Test

/** DEC-028/MST-006: snake-case bundle fields must survive Android parsing exactly. */
class MobileBundleParsingTest {
    @Test fun mst006ParsesManifestAndCalibrationWithoutChangingPolicyFlags() {
        val manifest = AndroidMobileBundleLoader.parseManifest(
            """{
              "bundle_version":"vm-test",
              "labels":["TA_WORD_0001","OTHER"],
              "files":{"mobile_word_student.int8.onnx":"abc"},
              "approved_for_child_scoring":false,
              "release_build_enabled":false,
              "vad":{"threshold":0.5,"minimum_speech_ms":200,"merge_tolerance_ms":700}
            }"""
        )
        assertEquals("vm-test", manifest.bundleVersion)
        assertFalse(manifest.approvedForChildScoring)
        assertEquals(200, manifest.vad.minimumSpeechMs)

        val calibration = AndroidMobileBundleLoader.parseCalibration(
            """{
              "high_thresholds":{"TA_WORD_0001":0.7},
              "low_thresholds":{"TA_WORD_0001":0.2},
              "target_duration_samples":{"TA_WORD_0001":7025},
              "minimum_margin":0.1,
              "minimum_similarity":0.6
            }""",
            manifest.labels,
        )
        assertEquals(0.7, calibration.highThresholds.getValue("TA_WORD_0001"), 0.0)
        assertEquals(0.1, calibration.minimumMargin, 0.0)
        assertEquals(7025, calibration.targetDurationSamples.getValue("TA_WORD_0001"))
    }

    @Test fun mst006ParsesReferenceCentroids() {
        val references = AndroidMobileBundleLoader.parseReferences(
            """{"references":{"TA_WORD_0001":{"centroid":[0.1,-0.2],"sample_ids":["a"],"speaker_count":1}}}"""
        )
        assertEquals(listOf("TA_WORD_0001"), references.keys.toList())
        assertEquals(-0.2f, references.getValue("TA_WORD_0001")[1], 0f)
    }
}
