package com.team96.speakeasy.audio

import java.security.MessageDigest
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test

/** DEC-028/MST-006: no model session may open before full bundle verification. */
class MobileBundleVerifierTest {
    private fun sha(value: ByteArray): String = MessageDigest.getInstance("SHA-256")
        .digest(value).joinToString("") { "%02x".format(it) }

    @Test fun mst015ValidV1EngineeringBundleIsAcceptedButNeverChildApproved() {
        val files = MobileBundleVerifier.requiredFiles.associateWith { it.encodeToByteArray() }
        val hashes = files.mapValues { sha(it.value) }
        val manifest = MobileBundleManifest(
            bundleVersion = "vm-mobile-student-ta19-v1",
            architectureVersion = "raw-wave-temporal8-dc-rms-v1",
            labels = listOf("TA_WORD_0001", "OTHER"),
            files = hashes,
            approvedForChildScoring = false,
            releaseBuildEnabled = false,
        )
        val verified = MobileBundleVerifier.verify(manifest) { files.getValue(it) }
        assertEquals("vm-mobile-student-ta19-v1", verified.bundleVersion)
    }


    @Test fun mst015V1BundleRejectsMixedV0Architecture() {
        val files = MobileBundleVerifier.requiredFiles.associateWith { it.encodeToByteArray() }
        val hashes = files.mapValues { sha(it.value) }
        val manifest = MobileBundleManifest(
            "vm-mobile-student-ta19-v1",
            listOf("TA_WORD_0001", "OTHER"),
            hashes,
            false,
            false,
            architectureVersion = "raw-wave-global-pool-v0",
        )
        assertThrows(MobileBundleException::class.java) {
            MobileBundleVerifier.verify(manifest) { files.getValue(it) }
        }
    }

    @Test fun mst006ChangedFileAndApprovalFlagFailClosed() {
        val files = MobileBundleVerifier.requiredFiles.associateWith { it.encodeToByteArray() }
        val hashes = files.mapValues { sha(it.value) }
        val base = MobileBundleManifest("v", listOf("TA_WORD_0001", "OTHER"), hashes, false, false)
        assertThrows(MobileBundleException::class.java) {
            MobileBundleVerifier.verify(base) { name -> if (name.endsWith("onnx")) byteArrayOf(7) else files.getValue(name) }
        }
        assertThrows(MobileBundleException::class.java) {
            MobileBundleVerifier.verify(base.copy(approvedForChildScoring = true)) { files.getValue(it) }
        }
    }
}
