package com.team96.speakeasy.audio

import com.squareup.moshi.Json
import java.security.MessageDigest

data class MobileBundleManifest(
    @Json(name = "bundle_version")
    val bundleVersion: String,
    val labels: List<String>,
    val files: Map<String, String>,
    @Json(name = "approved_for_child_scoring")
    val approvedForChildScoring: Boolean,
    @Json(name = "release_build_enabled")
    val releaseBuildEnabled: Boolean,
    @Json(name = "architecture_version")
    val architectureVersion: String = "raw-wave-global-pool-v0",
    val vad: MobileVadConfiguration = MobileVadConfiguration(),
)

data class MobileVadConfiguration(
    val threshold: Double = 0.5,
    @Json(name = "minimum_speech_ms") val minimumSpeechMs: Int = 200,
    @Json(name = "merge_tolerance_ms") val mergeToleranceMs: Int = 700,
)

class MobileBundleException(message: String) : IllegalStateException(message)

/** DEC-028/029 and MST-006/015: verify version and bytes before inference. */
object MobileBundleVerifier {
    val requiredFiles = listOf(
        "mobile_word_student.int8.onnx",
        "labels.json",
        "reference_bank.json",
        "adult_engineering_calibration.json",
        "silero_vad.onnx",
    )

    fun verify(manifest: MobileBundleManifest, readBytes: (String) -> ByteArray): MobileBundleManifest {
        if (manifest.approvedForChildScoring) throw MobileBundleException("child_scoring_must_be_false")
        if (
            manifest.bundleVersion == "vm-mobile-student-ta19-v1" &&
            manifest.architectureVersion != "raw-wave-temporal8-dc-rms-v1"
        ) throw MobileBundleException("bundle_architecture_mismatch")
        if (manifest.labels.size < 2 || manifest.labels.last() != "OTHER") throw MobileBundleException("bundle_labels_invalid")
        requiredFiles.forEach { name ->
            val expected = manifest.files[name] ?: throw MobileBundleException("bundle_file_missing:$name")
            val actual = MessageDigest.getInstance("SHA-256").digest(readBytes(name))
                .joinToString("") { "%02x".format(it) }
            if (actual != expected) throw MobileBundleException("bundle_hash_mismatch:$name")
        }
        return manifest
    }
}
