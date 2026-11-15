package com.team96.speakeasy.audio
import org.junit.Assert.*
import org.junit.Test

class BackboneCaptureWindowTest {
    @Test fun quietNonzeroWordEndingSurvivesTheBackboneWindow() {
        val samples=ShortArray(9600)
        for(i in 1600 until 4800)samples[i]=if(i%2==0)5000 else -5000
        for(i in 4800 until 8000)samples[i]=if(i%2==0)100 else -100
        val original=samples.copyOf()
        val old=MobilePcmPreprocessor.trimActiveWord(samples)
        val retained=BackboneCaptureWindow.trim(samples)
        assertTrue("Legacy8%energy trimming removes part of the quiet ending",old.size<retained.size)
        assertArrayEquals(samples,retained);assertArrayEquals(original,samples)
        assertEquals(4000,BackboneCaptureProfile.CONSERVATIVE_V1.vadPaddingSamples)
        assertEquals(1600,BackboneCaptureProfile.LEGACY.vadPaddingSamples)
    }
    @Test fun emptyOrTooShortWindowsDoNotBecomeVoicedEvidence() {
        assertTrue(BackboneCaptureWindow.trim(ShortArray(8000)).isEmpty())
        assertTrue(BackboneCaptureWindow.trim(shortArrayOf(100)).isEmpty())
    }
}
