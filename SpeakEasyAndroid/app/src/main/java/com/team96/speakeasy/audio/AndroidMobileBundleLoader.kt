package com.team96.speakeasy.audio

import android.content.Context
import com.squareup.moshi.Json
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory

data class LoadedMobileBundle(
    val manifest: MobileBundleManifest,
    val modelBytes: ByteArray,
    val vadBytes: ByteArray,
    val references: Map<String, FloatArray>,
    val calibration: MobileEngineeringCalibration,
)

private data class ReferenceEntry(val centroid: List<Double>)
private data class ReferenceDocument(val references: Map<String, ReferenceEntry>)
private data class CalibrationDocument(
    @Json(name = "low_thresholds") val lowThresholds: Map<String, Double>,
    @Json(name = "high_thresholds") val highThresholds: Map<String, Double>,
    @Json(name = "minimum_margin") val minimumMargin: Double,
    @Json(name = "minimum_similarity") val minimumSimilarity: Double,
    @Json(name = "target_duration_samples") val targetDurationSamples: Map<String, Int> = emptyMap(),
)

/** DEC-028/MST-006: load a complete, hash-verified immutable asset set before inference. */
object AndroidMobileBundleLoader {
    const val ASSET_ROOT = "vaakmitra/mobile-student-ta19-v0"
    private val moshi = Moshi.Builder().add(KotlinJsonAdapterFactory()).build()

    fun load(context: Context, root: String = ASSET_ROOT): LoadedMobileBundle {
        fun bytes(name: String): ByteArray = context.assets.open("$root/$name").use { it.readBytes() }
        val manifest = parseManifest(bytes("bundle.json").decodeToString())
        if (manifest.releaseBuildEnabled) throw MobileBundleException("release_bundle_must_be_disabled")
        MobileBundleVerifier.verify(manifest, ::bytes)

        val references = parseReferences(bytes("reference_bank.json").decodeToString())
        val calibration = parseCalibration(
            bytes("adult_engineering_calibration.json").decodeToString(),
            manifest.labels,
        )
        val requiredTargets = manifest.labels.filterNot { it == "OTHER" }.toSet()
        if (!references.keys.containsAll(requiredTargets)) throw MobileBundleException("reference_coverage_incomplete")
        if (!calibration.lowThresholds.keys.containsAll(requiredTargets) ||
            !calibration.highThresholds.keys.containsAll(requiredTargets) ||
            !calibration.targetDurationSamples.keys.containsAll(requiredTargets)
        ) throw MobileBundleException("calibration_coverage_incomplete")

        return LoadedMobileBundle(
            manifest = manifest,
            modelBytes = bytes("mobile_word_student.int8.onnx"),
            vadBytes = bytes("silero_vad.onnx"),
            references = references,
            calibration = calibration,
        )
    }

    fun parseManifest(json: String): MobileBundleManifest =
        moshi.adapter(MobileBundleManifest::class.java).fromJson(json)
            ?: throw MobileBundleException("bundle_manifest_invalid")

    fun parseReferences(json: String): Map<String, FloatArray> {
        val document = moshi.adapter(ReferenceDocument::class.java).fromJson(json)
            ?: throw MobileBundleException("reference_bank_invalid")
        return document.references.mapValues { (_, entry) ->
            if (entry.centroid.isEmpty() || entry.centroid.any { !it.isFinite() }) {
                throw MobileBundleException("reference_centroid_invalid")
            }
            entry.centroid.map(Double::toFloat).toFloatArray()
        }
    }

    fun parseCalibration(json: String, labels: List<String>): MobileEngineeringCalibration {
        val document = moshi.adapter(CalibrationDocument::class.java).fromJson(json)
            ?: throw MobileBundleException("calibration_invalid")
        return MobileEngineeringCalibration(
            labels = labels,
            lowThresholds = document.lowThresholds,
            highThresholds = document.highThresholds,
            minimumMargin = document.minimumMargin,
            minimumSimilarity = document.minimumSimilarity,
            targetDurationSamples = document.targetDurationSamples,
        )
    }
}
