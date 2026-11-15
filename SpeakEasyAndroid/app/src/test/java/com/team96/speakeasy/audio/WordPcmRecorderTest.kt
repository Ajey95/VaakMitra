package com.team96.speakeasy.audio

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit

class WordPcmRecorderTest {
    private class FakeSource(private val starts: Boolean = true) : PcmSource {
        val readOnce = CountDownLatch(1)
        @Volatile var stopped = false
        @Volatile var released = false

        override fun start(): Boolean = starts

        override fun read(samples: ShortArray): Int {
            samples.fill(1200)
            readOnce.countDown()
            Thread.sleep(2)
            return samples.size
        }

        override fun stop() { stopped = true }
        override fun release() { released = true }
    }

    @Test fun prv001StopReturnsBoundedPcmAndReleasesSource() {
        val source = FakeSource()
        val recorder = WordPcmRecorder { source }
        assertTrue(recorder.start())
        assertTrue(source.readOnce.await(2, TimeUnit.SECONDS))
        val samples = recorder.stop()
        assertTrue(samples.isNotEmpty())
        assertTrue(samples.size <= 128000)
        assertTrue(source.stopped)
        assertTrue(source.released)
        samples.fill(0)
    }

    @Test fun prv001CancelDropsAudioAndIsIdempotent() {
        val source = FakeSource()
        val recorder = WordPcmRecorder { source }
        assertTrue(recorder.start())
        assertTrue(source.readOnce.await(2, TimeUnit.SECONDS))
        recorder.cancel()
        recorder.cancel()
        assertTrue(source.released)
        assertEquals(0, recorder.stop().size)
    }

    @Test fun dec051DiagnosticSampleCapReleasesSourceWithoutUiProgress() {
        val source = FakeSource()
        val recorder = WordPcmRecorder(maxSamples = 40000) { source }
        assertTrue(recorder.start())
        val end = System.nanoTime() + TimeUnit.SECONDS.toNanos(2)
        while (!source.released && System.nanoTime() < end) Thread.sleep(2)
        assertTrue("Sample cap must release microphone even if UI is stalled", source.released)
        val pcm = recorder.stop()
        assertEquals(40000, pcm.size)
        pcm.fill(0)
    }

    @Test fun au001FailedStartReleasesMicrophone() {
        val source = FakeSource(starts = false)
        val recorder = WordPcmRecorder { source }
        assertFalse(recorder.start())
        assertTrue(source.released)
        assertEquals(0, recorder.stop().size)
    }
}
