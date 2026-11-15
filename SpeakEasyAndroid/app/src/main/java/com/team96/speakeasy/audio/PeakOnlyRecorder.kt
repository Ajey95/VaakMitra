package com.team96.speakeasy.audio
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicInteger
import kotlin.math.abs
/** DEC057/PRV001: transient candle peak samples only, no audio buffer, file or network. */
class PeakOnlyRecorder(private val sourceFactory:()->PcmSource={AndroidPcmSource()}):CandleInput{
 private class Session(val source:PcmSource){val running=AtomicBoolean(true);val closed=AtomicBoolean(false);val peak=AtomicInteger();var thread:Thread?=null
  fun close(){if(closed.compareAndSet(false,true)){runCatching{source.stop()};runCatching{source.release()}}}
 }
 private var session:Session?=null
 override val isRunning:Boolean @Synchronized get()=session?.running?.get()==true
 @Synchronized override fun start():Boolean{
  if(session?.running?.get()==true)return false
  session=null
  val source=runCatching{sourceFactory()}.getOrNull()?:return false
  if(!runCatching{source.start()}.getOrDefault(false)){runCatching{source.release()};return false}
  val current=Session(source);session=current
  current.thread=Thread({val chunk=ShortArray(2048)
   try{while(current.running.get()){
    val count=source.read(chunk);if(count<=0)break
    try{var highest=0;for(i in 0 until minOf(count,chunk.size))highest=maxOf(highest,abs(chunk[i].toInt()));current.peak.accumulateAndGet(highest){a,b->maxOf(a,b)}}finally{chunk.fill(0)}
   }}catch(_:Exception){}finally{
    chunk.fill(0);current.running.set(false);current.close();current.peak.set(0)
    synchronized(this@PeakOnlyRecorder){if(session===current)session=null}
   }
  },"vaakmitra-game-level").also{it.isDaemon=true;it.start()}
  return true
 }
 @Synchronized override fun amplitude():Int=if(isRunning)session?.peak?.getAndSet(0)?:0 else 0
 override fun cancel(){val current=synchronized(this){session.also{session=null}}?:return;current.running.set(false);current.close();current.thread?.join(1000);current.peak.set(0)}
}
