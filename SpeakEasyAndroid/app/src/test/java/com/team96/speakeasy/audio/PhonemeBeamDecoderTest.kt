package com.team96.speakeasy.audio

import kotlin.math.ln
import org.junit.Assert.*
import org.junit.Test

/** PHN-001/003/006: no expected word or language prior enters these cases. */
class PhonemeBeamDecoderTest {
    private val beam = PhonemeDecoderConfig("ctc_prefix_beam", 5, 1)
    @Test fun agreesWithPythonFloat32GoldenCases() {
        val stream=javaClass.getResourceAsStream("/phoneme-decoder-golden.txt")
        assertNotNull("PHN-006 cross-runtime fixture is required",stream)
        val lines=stream!!.bufferedReader().use { it.readLines() }
        assertEquals(73,lines.size)
        lines.forEach { line ->
            val fields=line.split('|')
            val frames=fields[0].split(';').map { frame -> frame.split(',').map { it.toFloat() }.toFloatArray() }.toTypedArray()
            val expected=if(fields[1].isEmpty()) intArrayOf() else fields[1].split(',').map { it.toInt() }.toIntArray()
            assertArrayEquals(expected,PhonemeCtcDecoder.decode(frames,frames[0].size,PhonemeDecoderConfig("ctc_prefix_beam",5,fields[2].toInt())))
        }
    }
    @Test fun sumsAlternativeCtcPaths() {
        val frames = Array(2) { floatArrayOf(ln(.55).toFloat(), ln(.45).toFloat()) }
        assertArrayEquals(intArrayOf(), PhonemeCtcDecoder.decode(frames, 2))
        assertArrayEquals(intArrayOf(1), PhonemeCtcDecoder.decode(frames, 2, beam))
    }
    @Test fun keepsBlankSeparatedRepeatedPhones() {
        val frames = arrayOf(floatArrayOf(-9f,9f),floatArrayOf(9f,-9f),floatArrayOf(-9f,9f))
        assertArrayEquals(intArrayOf(1,1), PhonemeCtcDecoder.decode(frames,2,beam))
    }
    @Test fun emptyInputStaysEmpty() {
        assertArrayEquals(intArrayOf(),PhonemeCtcDecoder.decode(emptyArray(),2,beam))
    }
    @Test(expected = IllegalArgumentException::class) fun rejectsNonfiniteLogits() {
        PhonemeCtcDecoder.decode(arrayOf(floatArrayOf(0f,Float.NaN)),2,beam)
    }
    @Test fun rejectsUnknownOrUnboundedConfigurations() {
        listOf(Triple("unknown",1,1),Triple("greedy",5,1),Triple("ctc_prefix_beam",11,8),Triple("ctc_prefix_beam",5,61)).forEach {
            var rejected=false
            try { PhonemeDecoderConfig(it.first,it.second,it.third) } catch (_:IllegalArgumentException) { rejected=true }
            assertTrue(rejected)
        }
    }
    @Test fun beamRequiresNewBundleVersionToProtectLegacyReaders() {
        PhonemeCtcDecoder.validateBundleDecoder("phoneme-ta19-v1", PhonemeDecoderConfig())
        PhonemeCtcDecoder.validateBundleDecoder("phoneme-ta19-v2", beam)
        var rejected=false
        try { PhonemeCtcDecoder.validateBundleDecoder("phoneme-ta19-v1",beam) } catch (_:IllegalArgumentException) { rejected=true }
        assertTrue(rejected)
    }
    @Test fun parsesStrictVersionedDecoderMetadata() {
        assertEquals(PhonemeDecoderConfig(),PhonemeCtcDecoder.parseDecoder("phoneme-ta19-v1",false,null,61))
        val valid=mapOf("type" to "ctc_prefix_beam","beam_width" to 5,"nonblank_top_k" to 8)
        assertEquals(PhonemeDecoderConfig("ctc_prefix_beam",5,8),PhonemeCtcDecoder.parseDecoder("phoneme-ta19-v2",true,valid,61))
        val invalid=listOf(null,valid+mapOf("beam_width" to 5.0),valid+mapOf("extra" to 1),valid+mapOf("nonblank_top_k" to 61),mapOf("type" to "unknown"))
        invalid.forEach { config ->
            var rejected=false
            try { PhonemeCtcDecoder.parseDecoder("phoneme-ta19-v2",true,config,61) } catch (_:IllegalArgumentException) { rejected=true }
            assertTrue(rejected)
        }
        var rejected=false
        try { PhonemeCtcDecoder.parseDecoder("phoneme-ta19-v2",false,null,61) } catch (_:IllegalArgumentException) { rejected=true }
        assertTrue(rejected)
    }
}
