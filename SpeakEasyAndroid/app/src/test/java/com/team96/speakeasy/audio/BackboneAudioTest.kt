package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test
import kotlin.math.sqrt

/** DEC068/PHN008: new dynamic contract is separate from the legacy61unit model. */
class BackboneAudioTest {
    @Test fun exactConvolutionFramesAreNotRoundedDurationFrames() {
        assertEquals(1,BackboneAudio.validFrames(400))
        assertEquals(49,BackboneAudio.validFrames(16000))
        assertEquals(149,BackboneAudio.validFrames(48000))
    }
    @Test fun actualAudioIsNormalizedWithoutPaddingAndCanBeErased() {
        val pcm=ShortArray(400){if(it%2==0)128 else -128}
        val input=BackboneAudio.prepare(pcm)
        val raw=128.0/32768.0;val expected=(raw/sqrt(raw*raw+1e-7)).toFloat()
        assertEquals(400,input.waveform.size);assertEquals(400,input.mask.size)
        assertTrue(input.mask.all{it==1L});assertEquals(1,input.validFrames)
        assertEquals(expected,input.waveform[0],1e-6f)
        assertEquals(-expected,input.waveform[1],1e-6f)
        assertEquals(128.toShort(),pcm[0])
        input.erase();assertTrue(input.waveform.all{it==0f});assertTrue(input.mask.all{it==0L})
    }
    @Test(expected=IllegalArgumentException::class) fun longAudioIsRejectedInsteadOfCropped() {BackboneAudio.prepare(ShortArray(48001))}
    @Test(expected=IllegalArgumentException::class) fun underReceptiveFieldAudioIsRejected() {BackboneAudio.prepare(ShortArray(399))}
    @Test fun compoundsExpandAfterCtcWhileDoublesAffricatesAndUnknownsSurvive() {
        val tokens=listOf("<blank>","a","m","aː","aj","aʋ","kʂ","t͡ʃ","[UNK]","|")+(0..28).map{"unit$it"}
        val path=intArrayOf(1,1,0,2,0,2,3,4,5,6,7,8,9)
        val frames=path.map{p->FloatArray(39){if(it==p)30f else -30f}}.toTypedArray()
        assertEquals(listOf("a","m","m","aː","a","j","a","ʋ","k","ʂ","t͡ʃ","[UNK]"),BackbonePhones.decode(frames,tokens))
    }
    @Test(expected=IllegalArgumentException::class) fun aLegacy61WidthCannotUseTheNewDecoder() {
        BackbonePhones.decode(arrayOf(FloatArray(61)),List(61){if(it==0) "<blank>" else "unit$it"})
    }
}
