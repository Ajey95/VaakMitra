package com.team96.speakeasy.audio

import java.io.File

/** DEC075/PHN016: candidate graph shares only the exact authenticated base blob. */
data class SharedBackboneVariantContract(
    val modelFile:String,val modelSha256:String,val modelBytes:Long,val androidVerified:Boolean,
) {
    companion object {
        fun parse(fields:Map<String,Any?>,base:BackboneBundleContract,allowCalibrationOnly:Boolean=false):SharedBackboneVariantContract {
            fun text(key:String)=fields[key] as? String ?: throw IllegalArgumentException("shared_$key")
            fun number(key:String)=PhonemeAudio.exactInteger(fields[key]).toLong()
            fun flag(key:String)=fields[key] as? Boolean ?: throw IllegalArgumentException("shared_$key")
            require(text("schema")=="vaakmitra.shared_backbone.v1" && text("model_file")=="phoneme.shared.onnx")
            require(base.modelFile=="phoneme.fp32.onnx" && text("base_sha256")==base.modelSha256 && number("base_bytes")==base.modelBytes)
            require(text("vocabulary_sha256")==base.vocabularySha256 && text("relative_base")=="shared/phoneme.fp32.onnx")
            val sha=text("model_sha256");require(sha.matches(Regex("[0-9a-f]{64}")))
            val bytes=number("model_bytes");require(bytes in 1..48L*1024*1024)
            require(flag("raw_preview_qualified") && flag("desktop_verified"))
            require(!flag("sound_corrections_qualified") && !flag("approved_for_child_scoring") && !flag("clinical_assessment"))
            val native=flag("android_verified");require(native || allowCalibrationOnly){"shared_android_validation_required"}
            val maximum=number("max_external_tensors");require(maximum in 1..1024)
            val source=fields["external_ranges"] as? List<*> ?: throw IllegalArgumentException("shared_ranges")
            require(source.isNotEmpty() && source.size<=maximum)
            val ranges=source.map{value->
                val row=value as? List<*> ?: throw IllegalArgumentException("shared_range")
                require(row.size==2)
                val offset=PhonemeAudio.exactInteger(row[0]).toLong();val length=PhonemeAudio.exactInteger(row[1]).toLong()
                require(offset>=0 && length>0 && offset+length<=base.modelBytes)
                offset to length
            }.sortedBy{it.first}
            require(ranges.distinct().size==ranges.size)
            require(ranges.zipWithNext().all{(left,right)->left.first+left.second<=right.first})
            return SharedBackboneVariantContract(text("model_file"),sha,bytes,native)
        }
    }
}

data class BackboneVariantChoice(val file:File,val modelSha256:String)

/** A failed optional candidate never masks the verified baseline's availability. */
fun <T> openBackboneWithFallback(base:File,baseSha256:String,candidate:BackboneVariantChoice?,open:(File)->T):Pair<T,String> {
    if(candidate!=null){
        try{return open(candidate.file) to candidate.modelSha256}catch(_:Exception){/* open owns failed-session disposal. */}
    }
    return open(base) to baseSha256
}
