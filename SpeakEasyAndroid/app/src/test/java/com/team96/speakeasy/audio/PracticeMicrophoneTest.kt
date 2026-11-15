package com.team96.speakeasy.audio

import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

/** DEC069/MIC001: deliberately stalled native boundaries must never stall their UI owner. */
class PracticeMicrophoneTest {
    private class Source(val startGate:CountDownLatch=CountDownLatch(0),val stopGate:CountDownLatch=CountDownLatch(0)):PcmSource {
        val entered=CountDownLatch(1);val read=CountDownLatch(1);val released=CountDownLatch(1)
        @Volatile var active=true
        override fun start():Boolean {entered.countDown();startGate.await(3,TimeUnit.SECONDS);return true}
        override fun read(samples:ShortArray):Int {samples.fill(1234);Thread.sleep(10);read.countDown();return samples.size}
        override fun stop(){stopGate.await(3,TimeUnit.SECONDS);active=false}
        override fun release(){released.countDown()}
    }
    @Test fun mic001BlockedStartupDoesNotBlockOwnerAndCancelInvalidatesLateSuccess()=runBlocking {
        val gate=CountDownLatch(1);val source=Source(startGate=gate)
        val mic=PracticeMicrophone(WordPcmRecorder{source})
        try {
            val tick=System.nanoTime();val pending=async{mic.start()};yield()
            assertTrue("Owner must remain responsive during native startup",TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-tick)<250)
            assertTrue(withContext(Dispatchers.IO){source.entered.await(1,TimeUnit.SECONDS)})
            val cancelTick=System.nanoTime();mic.cancel()
            assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-cancelTick)<100)
            gate.countDown();assertFalse(pending.await())
            assertTrue(withContext(Dispatchers.IO){source.released.await(1,TimeUnit.SECONDS)})
            assertEquals(0,mic.stop().size)
        } finally {gate.countDown();mic.close()}
    }
    @Test fun mic001CancelWhileStopIsBlockedDoesNotWaitOnUi()=runBlocking {
        val gate=CountDownLatch(1);val source=Source(stopGate=gate)
        val mic=PracticeMicrophone(WordPcmRecorder{source})
        try {
            assertTrue(mic.start());assertTrue(withContext(Dispatchers.IO){source.read.await(1,TimeUnit.SECONDS)})
            val stopped=async{mic.stop()};yield();delay(30)
            val tick=System.nanoTime();mic.cancel()
            assertTrue(TimeUnit.NANOSECONDS.toMillis(System.nanoTime()-tick)<100)
            gate.countDown();assertEquals(0,stopped.await().size)
        } finally {gate.countDown();mic.close()}
    }
    @Test fun mic001OrdinaryStopReturnsOwnedAudioAndCloseIsFinal()=runBlocking {
        val source=Source();val mic=PracticeMicrophone(WordPcmRecorder{source})
        assertTrue(mic.start());assertTrue(withContext(Dispatchers.IO){source.read.await(1,TimeUnit.SECONDS)})
        val samples=mic.stop()
        try {assertTrue(samples.isNotEmpty());assertTrue(samples.all{it==1234.toShort()})}
        finally {samples.fill(0);mic.close()}
        mic.close();assertFalse(mic.start());assertEquals(0,mic.stop().size)
    }
    @Test fun mic001CancelledStartupCoroutineCannotLeaveMicrophoneRunning()=runBlocking {
        val gate=CountDownLatch(1);val source=Source(startGate=gate)
        val mic=PracticeMicrophone(WordPcmRecorder{source})
        try {
            val pending=launch{mic.start()};yield()
            assertTrue(withContext(Dispatchers.IO){source.entered.await(1,TimeUnit.SECONDS)})
            pending.cancel();gate.countDown();pending.join()
            assertTrue(withContext(Dispatchers.IO){source.released.await(1,TimeUnit.SECONDS)})
        } finally {gate.countDown();mic.close()}
    }
    @Test fun mic001FailedSourceCanRetryWithoutLeakingItsOwner()=runBlocking {
        val source=Source();var attempts=0
        val recorder=WordPcmRecorder{if(attempts++==0)object:PcmSource {
            override fun start()=false;override fun read(samples:ShortArray)=-1
            override fun stop(){};override fun release(){}
        }else source}
        val mic=PracticeMicrophone(recorder)
        try{assertFalse(mic.start());assertTrue(mic.start());mic.cancel()}
        finally{mic.close()}
    }
    @Test fun mic001CancelledStopCoroutineReleasesOwnershipForTheNextAttempt()=runBlocking {
        val gate=CountDownLatch(1);val first=Source(stopGate=gate);val second=Source();var count=0
        val mic=PracticeMicrophone(WordPcmRecorder{if(count++==0)first else second})
        try {
            assertTrue(mic.start());assertTrue(withContext(Dispatchers.IO){first.read.await(1,TimeUnit.SECONDS)})
            val stopping=async{mic.stop()};yield();delay(30)
            stopping.cancel();gate.countDown();runCatching{stopping.await()}
            assertTrue("A cancelled stop must not leave the controller busy",mic.start())
        }finally{gate.countDown();mic.close()}
    }
}
