package com.team96.speakeasy.audio

import java.util.concurrent.atomic.AtomicBoolean

/** Debug operator capture: invalidate immediately, with no monitor held over native startup. */
class CaptureLifetime(private val cancelOwner:()->Unit) {
    private val cancelled=AtomicBoolean(false)
    fun cancel(){if(cancelled.compareAndSet(false,true))cancelOwner()}
    fun start(action:()->Boolean):Boolean {
        if(cancelled.get())return false
        val started=try{action()}catch(error:Throwable){cancel();throw error}
        if(cancelled.get()){cancelOwner();return false}
        return started
    }
    /** Lifecycle adapters publish on their foreground owner's main thread. */
    fun publish(action:()->Unit):Boolean {
        if(cancelled.get())return false
        action();return true
    }
}

/** Separate from model cleanup, which can wait for a long inference. */
object RecordingCleanup {
    private val worker=java.util.concurrent.Executors.newSingleThreadExecutor{task->
        Thread(task,"vaakmitra-diagnostic-mic-release").apply{isDaemon=true}
    }
    fun dispatch(action:()->Unit){worker.execute{runCatching{action()}}}
}
