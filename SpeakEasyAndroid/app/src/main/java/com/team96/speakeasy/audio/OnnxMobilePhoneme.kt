package com.team96.speakeasy.audio

import android.content.Context
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer
import org.json.JSONObject

/** Local provisional phoneme prediction; receives no target word and produces no score. */
class OnnxMobilePhoneme(context: Context) : AutoCloseable {
    private val environment = OrtEnvironment.getEnvironment()
    private val options = OrtSession.SessionOptions().apply {
        setIntraOpNumThreads(2)
        setInterOpNumThreads(1)
        addConfigEntry("session.intra_op.allow_spinning", "0")
    }
    private val session: OrtSession
    private val tokens: List<String>
    private val outputFrames: Int
    private val decoder: PhonemeDecoderConfig

    init {
        val assets = context.applicationContext.assets
        val manifest = JSONObject(assets.open("$ROOT/bundle.json").bufferedReader().use { it.readText() })
        val bundleVersion = manifest.getString("bundle_version")
        require(!manifest.getBoolean("approved_for_child_scoring"))
        require(!manifest.getBoolean("production_ready"))
        require(PhonemeAudio.exactInteger(manifest.get("input_samples")) == PhonemeAudio.SAMPLES)
        val frameShiftMs = PhonemeAudio.frameShift(manifest.has("frame_shift_ms"), manifest.opt("frame_shift_ms"))
        outputFrames = PhonemeAudio.validateOutputFrames(frameShiftMs, PhonemeAudio.exactInteger(manifest.get("output_frames")))
        val filename = manifest.getString("model_file")
        require(filename in setOf("phoneme.fp32.onnx", "phoneme.int8.onnx"))
        val vocabulary = assets.open("$ROOT/vocabulary.json").use { it.readBytes() }
        PhonemeCtcDecoder.verifySha(vocabulary, manifest.getString("vocabulary_sha256"))
        val payload = JSONObject(String(vocabulary, Charsets.UTF_8))
        require(PhonemeAudio.frameShift(payload.has("frame_shift_ms"), payload.opt("frame_shift_ms")) == frameShiftMs)
        val array = payload.getJSONArray("tokens")
        tokens = List(array.length()) { array.getString(it) }
        require(tokens.first() == "<blank>" && tokens.distinct().size == tokens.size)
        require(tokens.size == PhonemeAudio.exactInteger(manifest.get("tokens")))
        val rawDecoder = manifest.opt("decoder") as? JSONObject
        val decoderFields = rawDecoder?.keys()?.asSequence()?.associateWith { rawDecoder.get(it) }
        decoder = PhonemeCtcDecoder.parseDecoder(bundleVersion,manifest.has("decoder"),decoderFields,tokens.size)
        val bytes = assets.open("$ROOT/$filename").use { it.readBytes() }
        try {
            PhonemeCtcDecoder.verifySha(bytes, manifest.getString("model_sha256"))
            session = environment.createSession(bytes, options)
        } finally { bytes.fill(0); vocabulary.fill(0) }
        require(session.inputNames == setOf("waveform"))
        require(session.outputNames == setOf("logits"))
    }

    @Synchronized
    fun inferIds(samples: ShortArray): IntArray {
        val waveform = PhonemeAudio.prepare(samples)
        try {
            OnnxTensor.createTensor(environment, FloatBuffer.wrap(waveform), longArrayOf(1, waveform.size.toLong())).use { input ->
                session.run(mapOf("waveform" to input)).use { result ->
                    @Suppress("UNCHECKED_CAST")
                    val output = result[0].value as Array<Array<FloatArray>>
                    require(output.size == 1 && output[0].size == outputFrames)
                    return PhonemeCtcDecoder.decode(output[0], tokens.size,decoder)
                }
            }
        } finally { waveform.fill(0f) }
    }

    fun infer(samples: ShortArray): List<String> = tokensAndErase(inferIds(samples), tokens)

    override fun close() { session.close(); options.close() }

    companion object {
        /** DEC-051: returned labels are transient UI data; wrapper IDs are owned here. */
        internal fun tokensAndErase(ids: IntArray, tokens: List<String>): List<String> =
            try { ids.map { tokens[it] } } finally { ids.fill(0) }

        const val ROOT = "vaakmitra/phoneme-ta19-v1"
    }
}
