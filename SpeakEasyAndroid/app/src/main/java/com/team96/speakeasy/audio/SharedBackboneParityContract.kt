package com.team96.speakeasy.audio

import java.security.MessageDigest

data class SharedParityFixture(
    val sourceId:String,val samples:Int,val frames:Int,val units:Int,val valuesFile:String,val logpFile:String,
    val valuesSha256:String,val logpSha256:String,val phones:List<String>,
)

/** PHN016: a numerical validation cannot pass an empty or substituted fixture panel. */
object SharedBackboneParityContract {
    const val SELECTED_MODEL="7103c31f472593f5bf9b50bf4ee6c29736cd2abe353f1113380a5ab03be9ae16"
    private val ids=listOf("mswc-ta-62298757f74a1b7bce74bf5c","mswc-ta-8cf15be71e9089a21001b097","mswc-ta-ca7bfca77348594ad88eee93")
    fun parse(fields:Map<String,Any?>,actualModelSha256:String):List<SharedParityFixture> {
        require(actualModelSha256==SELECTED_MODEL && fields["model_sha256"]==SELECTED_MODEL)
        require(fields["schema"]=="PHN016-explicit-native-parity" && fields["reference"]=="CPU PyTorch exact merged weights" && fields["no_recording"]==true)
        val cases=fields["cases"] as? List<*> ?: throw IllegalArgumentException("parity_cases")
        require(cases.size==3)
        return cases.mapIndexed{index,value->
            val row=value as? Map<*,*> ?: throw IllegalArgumentException("parity_case")
            fun number(key:String)=PhonemeAudio.exactInteger(row[key])
            fun text(key:String)=row[key] as? String ?: throw IllegalArgumentException("parity_$key")
            require(number("index")==index && text("source_id")==ids[index])
            require(number("samples")==16000 && number("frames")==49 && number("units")==39)
            require(text("values_file")=="values-$index.f32" && text("logp_file")=="logp-$index.f32")
            val valuesSha=text("values_sha256");val logpSha=text("logp_sha256")
            require(listOf(valuesSha,logpSha).all{it.matches(Regex("[0-9a-f]{64}"))})
            val phones=row["phones"] as? List<*> ?: throw IllegalArgumentException("parity_phones")
            require(phones.isNotEmpty() && phones.size<=12 && phones.all{it is String && it.isNotEmpty()})
            SharedParityFixture(ids[index],16000,49,39,text("values_file"),text("logp_file"),valuesSha,logpSha,phones.map{it as String})
        }
    }
    fun verifyBytes(bytes:ByteArray,expectedBytes:Int,expectedSha256:String) {
        require(bytes.size==expectedBytes)
        val sha=MessageDigest.getInstance("SHA-256").digest(bytes).joinToString(""){"%02x".format(it)}
        require(sha==expectedSha256){"parity_fixture_digest"}
    }
    fun verifyOutput(frames:Array<FloatArray>,expectedFrames:Int,units:Int) {
        require(expectedFrames>0 && units>0 && frames.size==expectedFrames)
        require(frames.all{it.size==units && it.all(Float::isFinite)}){"parity_output_shape_or_nonfinite"}
    }
}

