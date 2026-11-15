package com.team96.speakeasy.audio
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
/** DEC057/PRV001: candle samples are transient; no microphone/file in this fake-source test. */
class PeakOnlyRecorderTest {
 @Test fun peakIsReportedThenResetAndEveryChunkIsErasedOnCancel(){
  val read=CountDownLatch(1);val unblock=CountDownLatch(1);var chunk:ShortArray?=null;var stops=0;var releases=0
  val source=object:PcmSource{var first=true;override fun start()=true
   override fun read(samples:ShortArray):Int{chunk=samples;if(first){first=false;samples[0]=12345;read.countDown();return 1};unblock.await(5,TimeUnit.SECONDS);return -1}
   override fun stop(){stops++;unblock.countDown()};override fun release(){releases++}}
  val recorder=PeakOnlyRecorder{source};assertTrue(recorder.start());assertTrue(read.await(5,TimeUnit.SECONDS))
  val end=System.nanoTime()+TimeUnit.SECONDS.toNanos(2);var peak=0
  while(peak==0 && System.nanoTime()<end){peak=recorder.amplitude();Thread.yield()}
  assertEquals(12345,peak);assertEquals(0,recorder.amplitude());recorder.cancel()
  assertEquals(1,stops);assertEquals(1,releases);assertTrue(checkNotNull(chunk).all{it==0.toShort()})
 }
 @Test fun failedStartReleasesSourceAndReportsNoLevel(){
  var releases=0;val recorder=PeakOnlyRecorder{object:PcmSource{override fun start()=false;override fun read(samples:ShortArray)=0;override fun stop(){};override fun release(){releases++}}}
  assertFalse(recorder.start());assertEquals(0,recorder.amplitude());assertEquals(1,releases);recorder.cancel()
 }
 @Test fun stoppedOrThrowingReadersAreNotSilenceAndCanRestart(){
  for(mode in 0..2){
   val released=CountDownLatch(1);var closes=0
   val recorder=PeakOnlyRecorder{object:PcmSource{
    override fun start()=true
    override fun read(samples:ShortArray):Int=when(mode){0->0;1->-1;else->throw IllegalStateException("public fake input ended")}
    override fun stop(){};override fun release(){closes++;released.countDown()}
   }}
   assertTrue(recorder.start());assertTrue(released.await(5,TimeUnit.SECONDS))
   assertFalse("Ended input must leave listening state",recorder.isRunning)
   assertEquals(0,recorder.amplitude());assertEquals(1,closes)
   assertTrue("Ended input must allow a fresh start",recorder.start());recorder.cancel()
  }
 }
 @Test fun anOldReaderCannotDetachItsReplacement(){
  val releasing=CountDownLatch(1);val finishRelease=CountDownLatch(1);val secondRead=CountDownLatch(1);val stopSecond=CountDownLatch(1);var created=0;var oldReader:Thread?=null
  val recorder=PeakOnlyRecorder{if(created++==0)object:PcmSource{
   override fun start()=true;override fun read(samples:ShortArray)=-1;override fun stop(){}
   override fun release(){oldReader=Thread.currentThread();releasing.countDown();finishRelease.await(5,TimeUnit.SECONDS)}
  }else object:PcmSource{
   override fun start()=true;override fun read(samples:ShortArray):Int{secondRead.countDown();stopSecond.await(5,TimeUnit.SECONDS);return -1}
   override fun stop(){stopSecond.countDown()};override fun release(){}
  }}
  try{
   assertTrue(recorder.start());assertTrue(releasing.await(5,TimeUnit.SECONDS));assertFalse(recorder.isRunning)
   assertTrue(recorder.start());assertTrue(secondRead.await(5,TimeUnit.SECONDS));finishRelease.countDown()
   checkNotNull(oldReader).join(5000);assertFalse(checkNotNull(oldReader).isAlive);assertTrue("Old cleanup detached the fresh reader",recorder.isRunning)
  }finally{finishRelease.countDown();recorder.cancel()}
 }
}
