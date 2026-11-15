package com.team96.speakeasy.audio

import kotlinx.coroutines.asCoroutineDispatcher
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.util.concurrent.Executors
import java.util.concurrent.RejectedExecutionException
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicLong
import java.util.concurrent.atomic.AtomicReference

/** DEC069/MIC001: native capture ownership is independent of UI and model inference workers. */
class PracticeMicrophone(private val recorder:WordPcmRecorder=WordPcmRecorder()):AutoCloseable {
    private val worker=Executors.newSingleThreadExecutor{task->Thread(task,"vaakmitra-practice-mic").apply{isDaemon=true}}
    private val dispatcher=worker.asCoroutineDispatcher()
    private val generation=AtomicLong(0)
    private val closed=AtomicBoolean(false)
    private val requested=AtomicBoolean(false)
    private fun current(ticket:Long)=!closed.get()&&generation.get()==ticket
    private fun cleanup(){try{worker.execute{recorder.cancel()}}catch(_:RejectedExecutionException){/* Closed worker already owns final cleanup. */}}

    suspend fun start():Boolean {
        if(closed.get() || !requested.compareAndSet(false,true))return false
        val ticket=generation.incrementAndGet();var published=false
        try {
            val started=withContext(dispatcher){
                if(!current(ticket))false else {
                    val accepted=recorder.start()
                    if(!current(ticket)){recorder.cancel();false}else accepted
                }
            }
            currentCoroutineContext().ensureActive()
            published=started && current(ticket)
            return published
        } finally {
            if(!published && generation.compareAndSet(ticket,ticket+1)){requested.set(false);cleanup()}
        }
    }
    suspend fun stop():ShortArray {
        if(closed.get())return ShortArray(0)
        val ticket=generation.get();val pending=AtomicReference<ShortArray?>(null);var delivered=false
        try {
            withContext(dispatcher){
                if(current(ticket))pending.set(recorder.stop())
            }
            currentCoroutineContext().ensureActive()
            if(!current(ticket))return ShortArray(0)
            requested.set(false)
            delivered=true
            return pending.getAndSet(null)?:ShortArray(0)
        } finally {
            pending.getAndSet(null)?.fill(0)
            if(!delivered && generation.compareAndSet(ticket,ticket+1)){requested.set(false);cleanup()}
        }
    }
    /** Immediate invalidation; native stop/release/join are never performed by the caller. */
    fun cancel(){generation.incrementAndGet();requested.set(false);cleanup()}
    override fun close(){if(closed.compareAndSet(false,true)){cancel();dispatcher.close()}}
}
