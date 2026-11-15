package com.team96.speakeasy.audio

import kotlin.math.sqrt

data class MobileEngineeringCalibration(
    val labels: List<String>,
    val lowThresholds: Map<String, Double>,
    val highThresholds: Map<String, Double>,
    val minimumMargin: Double,
    val minimumSimilarity: Double,
    val targetDurationSamples: Map<String, Int> = emptyMap(),
)

/** DEC-028/MST-007: adult engineering evidence is separate from official scoring. */
object MobileDevelopmentPolicy {
    fun evaluate(
        targetId: String,
        probabilities: FloatArray,
        embedding: FloatArray,
        references: Map<String, FloatArray>,
        calibration: MobileEngineeringCalibration,
        vadOk: Boolean = true,
    ): LocalWordOutcome {
        if (!vadOk) return unavailable("VAD_UNAVAILABLE")
        val targetIndex = calibration.labels.indexOf(targetId)
        val reference = references[targetId]
        if (targetIndex < 0 || targetId == "OTHER" || reference == null) return unavailable("TARGET_UNAVAILABLE")
        if (probabilities.size != calibration.labels.size || probabilities.any { !it.isFinite() } || probabilities.sum() <= 0f) {
            return unavailable("MODEL_OUTPUT_INVALID")
        }
        val similarity = cosine(embedding, reference) ?: return unavailable("REFERENCE_UNAVAILABLE")
        val normalized = probabilities.map { it / probabilities.sum() }
        val ordered = normalized.sorted()
        val margin = (ordered.last() - ordered[ordered.lastIndex - 1]).toDouble()
        val targetProbability = normalized[targetIndex].toDouble()
        val engineeringIndex = .7 * targetProbability + .3 * ((similarity + 1.0) / 2.0)
        val evidence = LocalWordOutcome(
            reason = "ADULT_ENGINEERING_UNCERTAIN",
            developmentResult = "DEV_UNCERTAIN",
            targetProbability = targetProbability,
            targetMargin = margin,
            referenceSimilarity = similarity,
            engineeringIndex = engineeringIndex,
        )
        if (margin < calibration.minimumMargin) return evidence.copy(reason = "LOW_MARGIN")
        if (
            normalized.indices.maxBy { normalized[it] } == targetIndex &&
            similarity >= calibration.minimumSimilarity &&
            engineeringIndex >= calibration.highThresholds.getValue(targetId)
        ) return evidence.copy(reason = "ADULT_ENGINEERING_MATCH", developmentResult = "DEV_MATCH")
        if (
            normalized.indices.maxBy { normalized[it] } != targetIndex ||
            engineeringIndex <= calibration.lowThresholds.getValue(targetId)
        ) return evidence.copy(reason = "ADULT_ENGINEERING_MISMATCH", developmentResult = "DEV_TRY_AGAIN")
        return evidence
    }

    private fun unavailable(reason: String) = LocalWordOutcome(reason = reason, developmentResult = "DEV_UNAVAILABLE")

    private fun cosine(left: FloatArray, right: FloatArray): Double? {
        if (left.size != right.size || left.isEmpty() || left.any { !it.isFinite() } || right.any { !it.isFinite() }) return null
        var dot = 0.0
        var leftSquare = 0.0
        var rightSquare = 0.0
        left.indices.forEach { index ->
            dot += left[index] * right[index]
            leftSquare += left[index] * left[index]
            rightSquare += right[index] * right[index]
        }
        if (leftSquare <= 1e-16 || rightSquare <= 1e-16) return null
        return dot / (sqrt(leftSquare) * sqrt(rightSquare))
    }
}
