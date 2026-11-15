package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test

/** DEC068/PHN008: new models cannot inherit permissive legacy parsing. */
class BackboneBundleTest {
    private fun fields()=mutableMapOf<String,Any?>(
        "bundle_version" to "phoneme-ta-backbone-v1","model_kind" to "wav2vec2_ctc",
        "model_file" to "phoneme.int8.onnx","model_sha256" to "a".repeat(64),"model_bytes" to 433000000,
        "vocabulary_file" to "vocabulary.json","vocabulary_sha256" to "b".repeat(64),"tokens" to 39,
        "sample_rate" to 16000,"min_input_samples" to 400,"max_input_samples" to 48000,"max_output_frames" to 149,
        "frame_shift_ms" to 20,"preprocessing" to "wav2vec2_mean_variance_eps1e-7_dynamic",
        "input_mask" to "contiguous_ones","engineering_qualified_for_preview" to true,"native_verified" to false,
        "production_ready" to false,"approved_for_child_scoring" to false,
        "decoder" to mapOf("type" to "ctc_prefix_beam","beam_width" to 5,"nonblank_top_k" to 8),
    )
    @Test fun calibrationOnlyBundleIsExplicitlyForValidationUntilPhoneChecksPass() {
        val contract=BackboneBundleContract.parse(fields(),allowCalibrationOnly=true)
        assertEquals("a".repeat(64),contract.modelSha256);assertFalse(contract.nativeVerified)
        var rejected=false
        try {BackboneBundleContract.parse(fields())}catch(_:IllegalArgumentException){rejected=true}
        assertTrue(rejected)
        assertTrue(BackboneBundleContract.parse(fields().apply{put("native_verified",true)}).nativeVerified)
    }
    @Test fun captureProfilesAreExplicitAndCannotBeCoerced() {
        assertEquals(BackboneCaptureProfile.LEGACY,BackboneBundleContract.parse(fields(),true).captureProfile)
        assertEquals(BackboneCaptureProfile.CONSERVATIVE_V1,BackboneBundleContract.parse(fields().apply{put("capture_preprocessing","backbone_conservative_v1")},true).captureProfile)
        for(value in listOf("target_duration",true,"unknown")) {
            var rejected=false;try{BackboneBundleContract.parse(fields().apply{put("capture_preprocessing",value)},true)}catch(_:IllegalArgumentException){rejected=true}
            assertTrue(rejected)
        }
    }
    @Test fun malformedCountsAndLegacyFramesAreRejectedWithoutCoercion() {
        for((key,value)in listOf("tokens" to 61,"max_output_frames" to 150,"sample_rate" to "16000","max_input_samples" to 48000.0,
            "min_input_samples" to 399,"frame_shift_ms" to 40,"model_bytes" to Long.MAX_VALUE)) {
            var rejected=false
            try {BackboneBundleContract.parse(fields().apply{put(key,value)},true)}catch(_:IllegalArgumentException){rejected=true}
            assertTrue("Must reject $key=$value",rejected)
        }
    }
    @Test fun missingSafetyFlagsOrTargetConditionedDecodersCannotLoad() {
        val invalid=listOf(fields().apply{remove("production_ready")},fields().apply{put("approved_for_child_scoring",true)},
            fields().apply{put("engineering_qualified_for_preview","true")},fields().apply{put("model_file","../other.onnx")},
            fields().apply{put("decoder",mapOf("type" to "ctc_prefix_beam","beam_width" to 5,"nonblank_top_k" to 8,"target" to "Amma"))})
        for(value in invalid){var rejected=false;try{BackboneBundleContract.parse(value,true)}catch(_:IllegalArgumentException){rejected=true};assertTrue(rejected)}
    }
}
