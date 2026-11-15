package com.team96.speakeasy.audio

import android.util.Log
import android.os.SystemClock
import androidx.test.core.app.ApplicationProvider
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import com.team96.speakeasy.MainActivity
import org.junit.Before
import org.junit.After
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** DEC068/PHN008: public calibration fixtures only; no microphone or user state. */
class BackboneInstrumentedTest {
    private var foreground:ActivityScenario<MainActivity>?=null
    @Before fun keepPublicInferenceForeground(){
        foreground=ActivityScenario.launch(MainActivity::class.java)
        foreground?.onActivity{it.window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)}
    }
    @After fun closePublicActivity(){foreground?.close();foreground=null}
    private val testAssets get()=InstrumentationRegistry.getInstrumentation().context.assets
    private fun manifest()=JSONObject(testAssets.open("backbone-fixtures/manifest.json").bufferedReader().use{it.readText()})
    private fun pcm(entry:JSONObject):ShortArray {
        val bytes=testAssets.open("backbone-fixtures/${entry.getString("file")}").use{it.readBytes()}
        try {
            PhonemeCtcDecoder.verifySha(bytes,entry.getString("sha256"))
            var offset=12
            while(offset+8<=bytes.size) {
                val length=(0..3).sumOf{(bytes[offset+4+it].toInt() and 255) shl (8*it)}
                if(String(bytes,offset,4,Charsets.US_ASCII)=="data")return ShortArray(length/2){i->
                    ((bytes[offset+8+i*2].toInt() and 255) or (bytes[offset+9+i*2].toInt() shl 8)).toShort()}
                offset+=8+length+length%2
            }
            error("Missing public PCM chunk")
        } finally {bytes.fill(0)}
    }
    @Test fun all53PublicClipsMatchDesktopPhonemePredictionsAtTheirActualLengths() {
        val context=ApplicationProvider.getApplicationContext<android.content.Context>()
        val evidence=manifest();assertTrue(evidence.getBoolean("calibration_only"));assertTrue(evidence.getBoolean("prediction_is_not_reference_truth"))
        val cases=evidence.getJSONArray("cases");assertEquals(53,cases.length())
        val times=mutableListOf<Long>()
        val loadStarted=SystemClock.elapsedRealtime()
        val published=JSONObject(context.assets.open("${OnnxBackbonePhoneme.ROOT}/bundle.json").bufferedReader().use{it.readText()}).getBoolean("native_verified")
        OnnxBackbonePhoneme(context,allowCalibrationOnly=!published).use{model->
            Log.i("VaakMitraBackbone","public modelLoadMs=${SystemClock.elapsedRealtime()-loadStarted}")
            assertEquals(evidence.getString("model_sha256"),model.modelSha256)
            repeat(cases.length()){i->
                val entry=cases.getJSONObject(i);assertEquals("calibration",entry.getString("source_split"))
                val samples=pcm(entry)
                try {
                    val tick=SystemClock.elapsedRealtime();val observation=model.inferObservation(samples)
                    times.add(SystemClock.elapsedRealtime()-tick)
                    Log.i("VaakMitraBackbone","publicCase=$i samples=${samples.size} inferenceMs=${times.last()}")
                    val expected=entry.getJSONArray("expected_prediction").let{array->List(array.length()){array.getString(it)}}
                    assertEquals("Public fixture$i",expected,observation.phones)
                    assertEquals(entry.getInt("valid_frames"),observation.validFrames)
                } finally {samples.fill(0)}
            }
        }
        val sorted=times.sorted();Log.i("VaakMitraBackbone","public cases=${times.size} medianMs=${sorted[sorted.size/2]} maxMs=${sorted.last()}")
    }
    @Test fun candidateCapturePipelineNeverUsesTheRequestedWordToCorrectPhones() {
        val context=ApplicationProvider.getApplicationContext<android.content.Context>()
        val cases=manifest().getJSONArray("cases");var accepted=false
        val published=JSONObject(context.assets.open("${OnnxBackbonePhoneme.ROOT}/bundle.json").bufferedReader().use{it.readText()}).getBoolean("native_verified")
        val loaded=if(published)MobileWordPracticeEngine.create(context,enabled=true)else MobileWordPracticeEngine.createForBackboneValidation(context)
        loaded.use{engine->
            for(index in 0 until cases.length()) {
                val source=pcm(cases.getJSONObject(index));val recording=ShortArray(source.size+6400)
                source.copyInto(recording,3200)
                try {
                    val baseline=engine.assess("TA_WORD_0001",recording)
                    if(baseline.reason!="PHONEME_TOKENS")continue
                    for(id in listOf("TA_WORD_0002","TA_WORD_0101","TA_WORD_0102","TA_WORD_0103","TA_WORD_0104","TA_WORD_0084","TA_WORD_0061")) {
                        val outcome=engine.assess(id,recording)
                        assertEquals("UNSCORABLE",outcome.decision);assertEquals(baseline.predictedPhonemes,outcome.predictedPhonemes)
                    }
                    accepted=true;break
                } finally {source.fill(0);recording.fill(0)}
            }
        }
        assertTrue("At least one public fixture must pass the existing VAD capture pipeline",accepted)
    }
}
