package com.team96.speakeasy.audio
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean

class CaptureLifetimeTest {
    @Test fun cancelDuringBlockedReadAndStopReturnsBeforeNativeCleanupFinishes() {
        val reading=CountDownLatch(1);val stopped=CountDownLatch(1);val release=CountDownLatch(1);val cleaned=CountDownLatch(1)
        val recorder=WordPcmRecorder(sourceFactory={object:PcmSource {
            override fun start()=true
            override fun read(samples:ShortArray):Int {reading.countDown();release.await(2,TimeUnit.SECONDS);return -1}
            override fun stop(){stopped.countDown();release.await(2,TimeUnit.SECONDS)}
            override fun release(){}
        }})
        val gate=CaptureLifetime{RecordingCleanup.dispatch{try{recorder.cancel()}finally{cleaned.countDown()}}}
        assertTrue(gate.start{recorder.start()});assertTrue(reading.await(1,TimeUnit.SECONDS))
        try {
            val tick=System.nanoTime();gate.cancel()
            assertTrue(System.nanoTime()-tick<TimeUnit.MILLISECONDS.toNanos(200))
            assertTrue(stopped.await(1,TimeUnit.SECONDS));assertFalse(gate.publish{fail("Late read result")})
        } finally {release.countDown();assertTrue(cleaned.await(3,TimeUnit.SECONDS))}
        assertEquals(0,recorder.stop().size)
    }
    @Test fun cancelNeverWaitsForBlockedNativeStartupAndDiscardsLatePublication() {
        val entered=CountDownLatch(1);val resume=CountDownLatch(1);val finished=CountDownLatch(1)
        val released=AtomicBoolean(false);val started=AtomicBoolean(true)
        val gate=CaptureLifetime{released.set(true)}
        val worker=Thread{try{started.set(gate.start{entered.countDown();resume.await(2,TimeUnit.SECONDS);true})}finally{finished.countDown()}}
        worker.start()
        try {
            assertTrue(entered.await(1,TimeUnit.SECONDS));val tick=System.nanoTime();gate.cancel()
            assertTrue("UI invalidation must not wait for startup",System.nanoTime()-tick<TimeUnit.MILLISECONDS.toNanos(200))
            assertTrue(released.get());assertFalse(gate.publish{fail("Late publication")})
            assertFalse(gate.start{fail("Cancelled lifetime cannot restart");true})
        } finally {resume.countDown();assertTrue(finished.await(2,TimeUnit.SECONDS));worker.join(1000)}
        assertFalse(started.get())
    }
}
