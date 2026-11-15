package com.team96.speakeasy.audio

/** DEC068: a separate, strict contract prevents legacy padding/frames from leaking into XLS-R. */
data class BackboneBundleContract(val modelFile:String,val modelSha256:String,val modelBytes:Long,
    val vocabularySha256:String,val nativeVerified:Boolean,val captureProfile:BackboneCaptureProfile=BackboneCaptureProfile.LEGACY) {
    companion object {
        fun parse(fields:Map<String,Any?>,allowCalibrationOnly:Boolean=false):BackboneBundleContract {
            fun text(key:String)=fields[key] as? String ?: throw IllegalArgumentException("backbone_$key")
            fun number(key:String)=PhonemeAudio.exactInteger(fields[key])
            fun flag(key:String)=fields[key] as? Boolean ?: throw IllegalArgumentException("backbone_$key")
            require(text("bundle_version")=="phoneme-ta-backbone-v1" && text("model_kind")=="wav2vec2_ctc")
            val filename=text("model_file");require(filename in setOf("phoneme.int8.onnx","phoneme.fp32.onnx"))
            require(text("vocabulary_file")=="vocabulary.json")
            val modelSha=text("model_sha256");val vocabularySha=text("vocabulary_sha256")
            require(listOf(modelSha,vocabularySha).all{it.matches(Regex("[0-9a-f]{64}"))})
            val bytes=number("model_bytes");require(bytes in 1..1_500_000_000)
            require(number("tokens")==39 && number("sample_rate")==16000 && number("min_input_samples")==400)
            require(number("max_input_samples")==48000 && number("max_output_frames")==149 && number("frame_shift_ms")==20)
            require(text("preprocessing")=="wav2vec2_mean_variance_eps1e-7_dynamic" && text("input_mask")=="contiguous_ones")
            require(flag("engineering_qualified_for_preview") && !flag("production_ready") && !flag("approved_for_child_scoring"))
            val native=flag("native_verified");require(native || allowCalibrationOnly){"backbone_native_validation_required"}
            val decoder=fields["decoder"] as? Map<*,*> ?: throw IllegalArgumentException("backbone_decoder")
            require(decoder.keys==setOf("type","beam_width","nonblank_top_k") && decoder["type"]=="ctc_prefix_beam")
            require(PhonemeAudio.exactInteger(decoder["beam_width"])==5 && PhonemeAudio.exactInteger(decoder["nonblank_top_k"])==8)
            val capture=if(!fields.containsKey("capture_preprocessing"))BackboneCaptureProfile.LEGACY else when(text("capture_preprocessing")) {
                "legacy_energy_v1" -> BackboneCaptureProfile.LEGACY
                "backbone_conservative_v1" -> BackboneCaptureProfile.CONSERVATIVE_V1
                else -> throw IllegalArgumentException("backbone_capture_profile_unknown")
            }
            return BackboneBundleContract(filename,modelSha,bytes.toLong(),vocabularySha,native,capture)
        }
    }
}
