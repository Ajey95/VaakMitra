package com.team96.speakeasy.audio

import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.LifecycleOwner

/** DEC-056/UX003 review R2: lifecycle cancellation never waits for another Compose frame. */
class PracticeAudioBoundary(
    private val invalidateAttempt: () -> Unit,
    private val cancelRecorder: () -> Unit,
    private val stopSpeaker: () -> Unit,
) : LifecycleEventObserver, AutoCloseable {
    private var active=true
    private var closed=false
    private var permissionGeneration=0L
    @get:Synchronized val isForeground: Boolean get()=active && !closed
    @Synchronized fun requestPermission():Long? = if(isForeground) ++permissionGeneration else null
    @Synchronized fun consumePermission(ticket:Long?):Boolean {
        if(!isForeground || ticket==null || ticket!=permissionGeneration)return false
        permissionGeneration++
        return true
    }
    @Synchronized fun background(){
        active=false;permissionGeneration++
        invalidateAttempt();cancelRecorder();stopSpeaker()
    }
    @Synchronized fun foreground(){if(!closed)active=true}
    @Synchronized override fun close(){if(!closed){closed=true;background()}}
    override fun onStateChanged(source:LifecycleOwner,event:Lifecycle.Event){
        when(event){
            Lifecycle.Event.ON_PAUSE,Lifecycle.Event.ON_STOP->background()
            Lifecycle.Event.ON_RESUME->foreground()
            Lifecycle.Event.ON_DESTROY->close()
            else->Unit
        }
    }
}
