package com.team96.speakeasy.audio

import kotlin.math.sqrt

/** DEC068/PHN008: actual16kHz audio only, without legacy centering or truncation. */
data class BackboneInput(val waveform:FloatArray,val mask:LongArray,val validFrames:Int) {
    fun erase(){waveform.fill(0f);mask.fill(0L)}
}

object BackboneAudio {
    const val MAX_SAMPLES=48000
    fun validFrames(samples:Int):Int {
        require(samples in 400..MAX_SAMPLES){"backbone_audio_length_invalid"}
        var result=samples
        for((kernel,stride)in listOf(10 to 5,3 to 2,3 to 2,3 to 2,3 to 2,2 to 2,2 to 2))result=(result-kernel)/stride+1
        return result
    }
    fun prepare(samples:ShortArray):BackboneInput {
        val frames=validFrames(samples.size)
        val mean=samples.sumOf{it.toDouble()/32768.0}/samples.size
        val variance=samples.sumOf{val value=it.toDouble()/32768.0-mean;value*value}/samples.size
        val scale=1.0/sqrt(variance+1e-7)
        return BackboneInput(FloatArray(samples.size){((samples[it].toDouble()/32768.0-mean)*scale).toFloat()},LongArray(samples.size){1L},frames)
    }
}

object BackbonePhones {
    private val compounds=mapOf("aj" to listOf("a","j"),"aʋ" to listOf("a","ʋ"),"kʂ" to listOf("k","ʂ"))
    private val decoder=PhonemeDecoderConfig("ctc_prefix_beam",5,8)
    fun known(tokens:List<String>)=tokens.flatMap{compounds[it]?:listOf(it)}.toSet()
    fun supported(phones:List<String>)=phones.isNotEmpty() && phones.none{it in setOf("[UNK]","்","<blank>","[PAD]")}
    fun decode(frames:Array<FloatArray>,tokens:List<String>):List<String> {
        require(tokens.size==39 && tokens.distinct().size==39 && tokens.first()=="<blank>" && tokens.all{it.isNotEmpty()})
        require(frames.size in 1..149 && frames.all{it.size==39 && it.all(Float::isFinite)})
        val ids=PhonemeCtcDecoder.decode(frames,39,decoder)
        return try {ids.map{tokens[it]}.filter{it!="|"}.flatMap{compounds[it]?:listOf(it)}}finally{ids.fill(0)}
    }
}
