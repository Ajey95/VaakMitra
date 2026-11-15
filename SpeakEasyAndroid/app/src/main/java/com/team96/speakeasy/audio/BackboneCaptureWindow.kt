package com.team96.speakeasy.audio

import kotlin.math.sqrt

enum class BackboneCaptureProfile(val vadPaddingSamples:Int) {
    LEGACY(1600),CONSERVATIVE_V1(4000),
}

/** DEC068/PHN008: lower-energy word edges survive; VAD still gates every inference. */
object BackboneCaptureWindow {
    fun trim(samples:ShortArray):ShortArray {
        if(samples.isEmpty())return ShortArray(0)
        val frameSize=320
        val frames=(samples.size+frameSize-1)/frameSize
        val rms=DoubleArray(frames){frame->
            val start=frame*frameSize;val end=minOf(samples.size,start+frameSize)
            var square=0.0
            for(i in start until end){val value=samples[i].toDouble();square+=value*value}
            sqrt(square/(end-start))
        }
        val threshold=maxOf(16.0,(rms.maxOrNull()?:0.0)*.02)
        val first=rms.indexOfFirst{it>=threshold};val last=rms.indexOfLast{it>=threshold}
        if(first<0 || last<first)return ShortArray(0)
        val start=(first*frameSize-1920).coerceAtLeast(0)
        val end=((last+1)*frameSize+1920).coerceAtMost(samples.size)
        return if(end-start>=3200)samples.copyOfRange(start,end)else ShortArray(0)
    }
}
