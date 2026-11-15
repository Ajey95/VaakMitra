package com.team96.speakeasy.audio

import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.currentCoroutineContext
import kotlinx.coroutines.ensureActive
import kotlinx.coroutines.withContext
import java.util.concurrent.atomic.AtomicReference

/** DEC-056 review R5: native resources have an owner before any rendered state publication. */
class AsyncResourceOwner<T:AutoCloseable>(private val release:((()->Unit)->Unit)={it()}):AutoCloseable {
    private var resource:T?=null
    private var closed=false
    @Synchronized private fun adopt(value:T):Boolean {
        if(closed || resource!=null){release{value.close()};return false}
        resource=value
        return true
    }
    suspend fun load(factory:()->T):T? {
        val pending=AtomicReference<T?>(null)
        try {
            withContext(Dispatchers.IO){pending.set(factory())}
            currentCoroutineContext().ensureActive()
            val value=checkNotNull(pending.getAndSet(null))
            return if(adopt(value))value else null
        } finally {pending.getAndSet(null)?.let{value->release{value.close()}}}
    }
    @Synchronized override fun close(){
        if(closed)return
        closed=true
        val value=resource;resource=null
        value?.let{release{it.close()}}
    }
}

/** Inference owns its native lock; navigation must never wait for it on the UI thread. */
object ModelResourceRelease {
    private val worker=java.util.concurrent.Executors.newSingleThreadExecutor{task->
        Thread(task,"vaakmitra-model-release").apply{isDaemon=true}
    }
    fun dispatch(task:()->Unit){worker.execute{runCatching{task()}}}
}
