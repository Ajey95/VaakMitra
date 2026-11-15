package com.team96.speakeasy.audio

import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.delay
import kotlinx.coroutines.ensureActive

/** DEC070: bounded imitation time, never microphone capture or a correctness assessment. */
data class GuideCadence(val visualMs:Long=1800,val imitationMs:Long=1000,val voiceStartMs:Long=1000,val voiceFinishMs:Long=4000) {
    init{require(listOf(visualMs,imitationMs,voiceStartMs,voiceFinishMs).all{it in 1..10000})}
}

/** Caller owns the speech lease; its stop callback must reject a superseded generation. */
suspend fun runGuideCues(
    steps:List<Int>,cadence:GuideCadence=GuideCadence(),allowed:()->Boolean,
    onStep:(Int)->Unit,play:(Int)->Boolean,isSpeaking:()->Boolean,stop:()->Unit,
):Boolean {
    suspend fun pause(ms:Long):Boolean {
        val until=System.nanoTime()+ms.coerceAtLeast(0)*1_000_000
        while(System.nanoTime()<until){
            currentCoroutineContext().ensureActive()
            if(!allowed())return false
            val remaining=((until-System.nanoTime())/1_000_000).coerceAtLeast(1)
            delay(minOf(25L,remaining))
        }
        currentCoroutineContext().ensureActive()
        return allowed()
    }
    suspend fun waitFor(ms:Long,predicate:()->Boolean):Boolean {
        val until=System.nanoTime()+ms*1_000_000
        while(!predicate() && System.nanoTime()<until){if(!pause(10))return false}
        return allowed()
    }
    try {
        for(step in steps){
            require(step in 0..2)
            currentCoroutineContext().ensureActive()
            if(!allowed())return false
            val tick=System.nanoTime();onStep(step)
            if(!allowed())return false
            if(runCatching{play(step)}.getOrDefault(false)){
                if(!waitFor(cadence.voiceStartMs,isSpeaking))return false
                if(isSpeaking() && !waitFor(cadence.voiceFinishMs){!isSpeaking()})return false
            }
            stop()
            val elapsed=(System.nanoTime()-tick)/1_000_000
            if(!pause((cadence.visualMs-elapsed).coerceAtLeast(0)) || !pause(cadence.imitationMs))return false
        }
        return allowed()
    } finally {stop()}
}
