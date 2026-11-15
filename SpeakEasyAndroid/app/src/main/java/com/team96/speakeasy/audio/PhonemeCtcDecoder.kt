package com.team96.speakeasy.audio

import java.security.MessageDigest
import kotlin.math.abs
import kotlin.math.exp
import kotlin.math.ln
import kotlin.math.ln1p
import kotlin.math.max

data class PhonemeDecoderConfig(val type: String = "greedy", val beamWidth: Int = 1, val nonblankTopK: Int = 1) {
    init {
        require(type in setOf("greedy", "ctc_prefix_beam"))
        require(if (type == "greedy") beamWidth == 1 && nonblankTopK == 1
                else beamWidth in 1..10 && nonblankTopK in 1..60)
    }
}

object PhonemeCtcDecoder {
    /** CTC merges repeats before removing blank; blank-separated doubles survive. */
    fun decode(frames: Array<FloatArray>, vocabularySize: Int, decoder: PhonemeDecoderConfig = PhonemeDecoderConfig()): IntArray {
        require(vocabularySize > 1)
        require(frames.all { it.size == vocabularySize && it.all { score -> score.isFinite() } })
        if (decoder.type == "ctc_prefix_beam") {
            require(decoder.nonblankTopK < vocabularySize)
            return prefixBeam(frames, decoder)
        }
        val result = mutableListOf<Int>()
        var previous = -1
        for (frame in frames) {
            require(frame.size == vocabularySize && frame.all { it.isFinite() })
            val token = frame.indices.maxByOrNull { frame[it] } ?: 0
            if (token != 0 && token != previous) result.add(token)
            previous = token
        }
        return result.toIntArray()
    }

    fun validateBundleDecoder(version: String, decoder: PhonemeDecoderConfig) {
        require(version in setOf("phoneme-ta19-v1", "phoneme-ta19-v2"))
        require(version != "phoneme-ta19-v1" || decoder.type == "greedy")
    }

    /** DEC-035: absent metadata is legacy greedy only; malformed fields fail closed. */
    fun parseDecoder(version: String, present: Boolean, fields: Map<String, Any?>?, vocabularySize: Int): PhonemeDecoderConfig {
        val config = if (!present) {
            require(version == "phoneme-ta19-v1")
            PhonemeDecoderConfig()
        } else {
            require(fields != null)
            when (fields["type"]) {
                "greedy" -> {
                    require(fields.keys == setOf("type"))
                    PhonemeDecoderConfig()
                }
                "ctc_prefix_beam" -> {
                    require(fields.keys == setOf("type", "beam_width", "nonblank_top_k"))
                    PhonemeDecoderConfig("ctc_prefix_beam",PhonemeAudio.exactInteger(fields["beam_width"]),PhonemeAudio.exactInteger(fields["nonblank_top_k"]))
                }
                else -> throw IllegalArgumentException("unknown phoneme decoder")
            }
        }
        validateBundleDecoder(version,config)
        require(vocabularySize > 1 && (config.type == "greedy" || config.nonblankTopK < vocabularySize))
        return config
    }

    private data class Mass(var blank: Double = Double.NEGATIVE_INFINITY, var nonblank: Double = Double.NEGATIVE_INFINITY)
    private fun logAdd(a: Double, b: Double): Double = when {
        a == Double.NEGATIVE_INFINITY -> b
        b == Double.NEGATIVE_INFINITY -> a
        else -> max(a, b) + ln1p(exp(-abs(a - b)))
    }
    private fun comparePrefix(a: List<Int>, b: List<Int>): Int {
        for (i in 0 until minOf(a.size, b.size)) {
            val order = a[i].compareTo(b[i]); if (order != 0) return order
        }
        return a.size.compareTo(b.size)
    }
    /** PHN-001/003: marginalize CTC paths; no lexicon, target word or length prior. */
    private fun prefixBeam(frames: Array<FloatArray>, decoder: PhonemeDecoderConfig): IntArray {
        var active = linkedMapOf<List<Int>, Mass>(emptyList<Int>() to Mass(0.0))
        val order = Comparator<Map.Entry<List<Int>, Mass>> { a, b ->
            val byScore = logAdd(b.value.blank,b.value.nonblank).compareTo(logAdd(a.value.blank,a.value.nonblank))
            if (byScore != 0) byScore else comparePrefix(a.key,b.key)
        }
        for (raw in frames) {
            val maximum = raw.maxOrNull()!!.toDouble()
            val shifted = DoubleArray(raw.size) { raw[it].toDouble() - maximum }
            val normalizer = ln(shifted.sumOf { exp(it) })
            val logp = DoubleArray(raw.size) { shifted[it] - normalizer }
            val labels = (1 until raw.size).sortedWith(compareByDescending<Int> { logp[it] }.thenBy { it }).take(decoder.nonblankTopK)
            val next = linkedMapOf<List<Int>, Mass>()
            fun push(prefix: List<Int>, blank: Double = Double.NEGATIVE_INFINITY, nonblank: Double = Double.NEGATIVE_INFINITY) {
                val mass = next.getOrPut(prefix) { Mass() }
                mass.blank = logAdd(mass.blank,blank); mass.nonblank = logAdd(mass.nonblank,nonblank)
            }
            for ((prefix,mass) in active) {
                push(prefix,blank=logAdd(mass.blank,mass.nonblank)+logp[0])
                for (label in labels) {
                    if (prefix.lastOrNull() == label) {
                        push(prefix,nonblank=mass.nonblank+logp[label])
                        push(prefix+label,nonblank=mass.blank+logp[label])
                    } else push(prefix+label,nonblank=logAdd(mass.blank,mass.nonblank)+logp[label])
                }
            }
            active = linkedMapOf<List<Int>, Mass>().apply {
                next.entries.sortedWith(order).take(decoder.beamWidth).forEach { put(it.key,it.value) }
            }
        }
        return active.entries.sortedWith(order).first().key.toIntArray()
    }

    fun verifySha(bytes: ByteArray, expected: String) {
        require(expected.matches(Regex("[0-9a-f]{64}")))
        val actual = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
        require(actual == expected) { "phoneme_bundle_hash_mismatch" }
    }
}

object PhonemeAudio {
    const val SAMPLES = 48_000
    // PHN-003: JSON coercion must not turn corrupt metadata into a legacy bundle.
    fun exactInteger(value: Any?): Int = when (value) {
        is Int -> value
        is Long -> {
            require(value in Int.MIN_VALUE.toLong()..Int.MAX_VALUE.toLong()) { "phoneme_contract_integer_overflow" }
            value.toInt()
        }
        else -> throw IllegalArgumentException("phoneme_contract_integer_required")
    }
    fun frameShift(present: Boolean, value: Any?): Int {
        if (!present) return 40
        return exactInteger(value).also {
            require(it in setOf(20, 40)) { "phoneme_frame_shift_invalid" }
        }
    }
    fun validateOutputFrames(frameShiftMs: Int, frames: Int): Int {
        require(frameShiftMs in setOf(20, 40)) { "phoneme_frame_shift_invalid" }
        require(frames == SAMPLES / (16 * frameShiftMs)) { "phoneme_output_frames_invalid" }
        return frames
    }
    fun prepare(samples: ShortArray): FloatArray {
        require(samples.isNotEmpty() && samples.size <= SAMPLES) { "phoneme_audio_length_invalid" }
        val output = FloatArray(SAMPLES)
        val offset = (SAMPLES - samples.size) / 2
        for (i in samples.indices) output[offset + i] = samples[i].toFloat() / 32768f
        return output
    }
}
