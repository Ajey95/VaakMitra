package com.team96.speakeasy.audio

import androidx.test.core.app.ApplicationProvider
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import android.util.Log
import org.json.JSONObject
import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class PhonemeInstrumentedTest {
    @Test fun dec058InstalledProvisionalReferencesCover25WordsWithoutChangingModelInputs() {
        val assets=ApplicationProvider.getApplicationContext<android.content.Context>().assets
        val root="vaakmitra/practice-words-v1"
        val bundle=JSONObject(assets.open("$root/bundle.json").bufferedReader().use{it.readText()})
        assertEquals("references.json",bundle.getString("references_file"))
        val bytes=assets.open("$root/references.json").use{it.readBytes()}
        PhonemeCtcDecoder.verifySha(bytes,bundle.getString("references_sha256"))
        val references=JSONObject(String(bytes,Charsets.UTF_8));bytes.fill(0)
        val vocabulary=JSONObject(assets.open("${OnnxMobilePhoneme.ROOT}/vocabulary.json").bufferedReader().use{it.readText()})
        val tokens=references.getJSONArray("tokens")
        assertEquals(vocabulary.getJSONArray("tokens").toString(),tokens.toString())
        assertFalse(references.getBoolean("expert_approved"));assertFalse(references.getBoolean("production_ready"));assertFalse(references.getBoolean("approved_for_child_scoring"))
        val expected=references.getJSONObject("expected")
        val words=com.team96.speakeasy.journey.StarterWords.all
        assertEquals(words.map{it.id}.toSet(),expected.keys().asSequence().toSet())
        val inventory=(0 until tokens.length()).map{tokens.getString(it)}.toSet()
        for(word in words){val phones=expected.getJSONArray(word.id);assertTrue(phones.length()>0);repeat(phones.length()){assertTrue(phones.getString(it)in inventory)}}
    }
    @Test fun dec058NewWordIdsNeverConditionOrForceThePhonemePrediction() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val (pcm, _) = fixture()
        val recording = ShortArray(pcm.size + 6400); pcm.copyInto(recording, 3200)
        try {
            MobileWordPracticeEngine.create(context, enabled = true).use { engine ->
                val baseline = engine.assess("TA_WORD_0001", recording)
                assertEquals("PHONEME_TOKENS", baseline.reason)
                for (id in listOf("TA_WORD_0101", "TA_WORD_0102", "TA_WORD_0103", "TA_WORD_0104", "TA_WORD_0084", "TA_WORD_0061")) {
                    val result = engine.assess(id, recording)
                    assertEquals("UNSCORABLE", result.decision)
                    assertEquals("PHONEME_TOKENS", result.reason)
                    assertEquals(baseline.predictedPhonemes, result.predictedPhonemes)
                }
            }
        } finally { pcm.fill(0); recording.fill(0) }
    }
    private fun fixture(name: String = "adult-test.wav", digest: String? = null): Pair<ShortArray, JSONObject> {
        val assets = InstrumentationRegistry.getInstrumentation().context.assets
        val root = "phoneme-fixtures"
        val evidence = JSONObject(assets.open("$root/adult-test.json").bufferedReader().use { it.readText() })
        val wav = assets.open("$root/$name").use { it.readBytes() }
        PhonemeCtcDecoder.verifySha(wav, digest ?: evidence.getString("fixture_sha256"))
        // The delivered fixture is PCM16 mono WAV; parse chunks instead of assuming 44 bytes.
        var offset = 12
        var pcm = ShortArray(0)
        while (offset + 8 <= wav.size) {
            val length = (0..3).sumOf { (wav[offset + 4 + it].toInt() and 255) shl (8 * it) }
            if (String(wav, offset, 4, Charsets.US_ASCII) == "data") {
                pcm = ShortArray(length / 2) { i ->
                    ((wav[offset + 8 + i * 2].toInt() and 255) or (wav[offset + 9 + i * 2].toInt() shl 8)).toShort()
                }
                break
            }
            offset += 8 + length + length % 2
        }
        assertTrue(pcm.isNotEmpty())
        wav.fill(0)
        return pcm to evidence
    }

    @Test fun adultFixtureMatchesDesktopDecodedTokensOffline() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val (pcm, evidence) = fixture()
        OnnxMobilePhoneme(context).use { model ->
            val expected = evidence.getJSONArray("expected_prediction")
            val wanted = IntArray(expected.length()) { expected.getInt(it) }
            repeat(3) { assertArrayEquals(wanted, model.inferIds(pcm)) }
            val latencies = mutableListOf<Double>()
            repeat(30) {
                val started = System.nanoTime()
                assertArrayEquals(wanted, model.inferIds(pcm))
                latencies.add((System.nanoTime() - started) / 1_000_000.0)
            }
            val sorted = latencies.sorted()
            val medianMs = (sorted[14] + sorted[15]) / 2.0
            Log.i("VaakMitraPhonemeEvidence", "public_adult_fixture repetitions=30 median_ms=$medianMs p95_ms=${sorted[28]}")
        }
        pcm.fill(0)
    }

    @Test fun adultFixtureRunsThroughActualPracticeVadAndTrimming() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val (pcm, evidence) = fixture()
        val recording = ShortArray(pcm.size + 6400)
        pcm.copyInto(recording, 3200)
        val started = System.nanoTime()
        val outcome = MobileWordPracticeEngine.create(context, enabled = true).use {
            it.assess(evidence.getString("word_id"), recording)
        }
        val elapsed = (System.nanoTime() - started) / 1_000_000
        assertEquals("UNSCORABLE", outcome.decision)
        assertEquals("PHONEME_TOKENS", outcome.reason)
        val predicted = outcome.predictedPhonemes.orEmpty()
        assertTrue(predicted.isNotEmpty())
        val vocabulary = evidence.getJSONArray("tokens")
        val target = evidence.getJSONArray("reference_token_ids")
        val reference = List(target.length()) { vocabulary.getString(target.getInt(it)) }
        // PHN-006: pin this source fixture's verified post-trim result independently
        // of the direct decoder golden; nonempty but incorrect phones must fail.
        assertEquals("PHN-006 frozen post-trim phone sequence changed", reference, predicted)
        var row = IntArray(predicted.size + 1) { it }
        reference.forEachIndexed { i, phone ->
            val next = IntArray(predicted.size + 1); next[0] = i + 1
            predicted.forEachIndexed { j, value ->
                next[j + 1] = minOf(next[j] + 1, row[j + 1] + 1, row[j] + if (phone == value) 0 else 1)
            }
            row = next
        }
        val per = row.last().toDouble() / reference.size
        Log.i("VaakMitraPhonemeEvidence", "public_adult_fixture pipeline_ms=$elapsed reference_phones=${reference.size} predicted_phones=${predicted.size} per=$per")
        pcm.fill(0); recording.fill(0)
    }

    @Test fun syntheticAdultVariantsExercisePracticePipelineSafely() {
        val context = ApplicationProvider.getApplicationContext<android.content.Context>()
        val assets = InstrumentationRegistry.getInstrumentation().context.assets
        val variants = JSONArray(assets.open("phoneme-fixtures/variants.json").bufferedReader().use { it.readText() })
        MobileWordPracticeEngine.create(context, enabled = true).use { engine ->
            repeat(variants.length()) { index ->
                val variant = variants.getJSONObject(index)
                val (pcm, evidence) = fixture(variant.getString("file"), variant.getString("sha256"))
                val recording = ShortArray(pcm.size + 6400); pcm.copyInto(recording, 3200)
                val started = System.nanoTime()
                val outcome = engine.assess(evidence.getString("word_id"), recording)
                assertEquals("UNSCORABLE", outcome.decision)
                assertTrue("Model errors must be visible", outcome.reason != "MODEL_UNAVAILABLE")
                Log.i("VaakMitraPhonemeEvidence", "public_adult_synthetic kind=${variant.getString("kind")} reason=${outcome.reason} predicted_phones=${outcome.predictedPhonemes?.size ?: 0} pipeline_ms=${(System.nanoTime()-started)/1_000_000}")
                pcm.fill(0); recording.fill(0)
            }
        }
    }
}
