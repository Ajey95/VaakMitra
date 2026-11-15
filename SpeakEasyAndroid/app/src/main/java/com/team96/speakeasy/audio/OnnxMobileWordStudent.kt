package com.team96.speakeasy.audio

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.FloatBuffer
import kotlin.math.exp

data class MobileStudentOutput(val probabilities: FloatArray, val embedding: FloatArray)

/** DEC-028/MST-008: deterministic local CPU/XNNPACK inference; no network or NNAPI path. */
class OnnxMobileWordStudent(modelBytes: ByteArray) : AutoCloseable {
    private val environment = OrtEnvironment.getEnvironment()
    private val options = OrtSession.SessionOptions().apply {
        setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
        setIntraOpNumThreads(1)
        setInterOpNumThreads(1)
        addConfigEntry("session.intra_op.allow_spinning", "0")
        addXnnpack(mapOf("intra_op_num_threads" to "2"))
    }
    private val session = environment.createSession(modelBytes, options)

    init {
        require(session.inputNames == setOf("waveform")) { "student_input_contract_invalid" }
        require(session.outputNames.containsAll(setOf("embedding", "logits"))) { "student_output_contract_invalid" }
    }

    fun infer(waveform: FloatArray): MobileStudentOutput {
        require(waveform.size == 32_000) { "student_waveform_length_invalid" }
        OnnxTensor.createTensor(environment, FloatBuffer.wrap(waveform), longArrayOf(1, 32_000)).use { input ->
            session.run(mapOf("waveform" to input)).use { result ->
                val embedding = matrix(required(result, "embedding")).single().copyOf()
                val logits = matrix(required(result, "logits")).single()
                return MobileStudentOutput(softmax(logits), embedding)
            }
        }
    }

    override fun close() {
        session.close()
        options.close()
    }

    private fun matrix(value: ai.onnxruntime.OnnxValue): Array<FloatArray> =
        @Suppress("UNCHECKED_CAST")
        (value.value as? Array<FloatArray>) ?: throw MobileBundleException("student_output_shape_invalid")

    private fun required(result: OrtSession.Result, name: String): ai.onnxruntime.OnnxValue {
        val value = result.get(name)
        return if (value.isPresent) value.get() else throw MobileBundleException("student_output_missing:$name")
    }

    private fun softmax(logits: FloatArray): FloatArray {
        if (logits.isEmpty() || logits.any { !it.isFinite() }) throw MobileBundleException("student_logits_invalid")
        val maximum = logits.max()
        val exponential = DoubleArray(logits.size) { index -> exp((logits[index] - maximum).toDouble()) }
        val total = exponential.sum()
        if (!total.isFinite() || total <= 0.0) throw MobileBundleException("student_softmax_invalid")
        return FloatArray(logits.size) { index -> (exponential[index] / total).toFloat() }
    }
}
