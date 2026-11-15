package com.team96.speakeasy.audio

import android.os.SystemClock
import android.util.Log
import androidx.test.core.app.ActivityScenario
import androidx.test.core.app.ApplicationProvider
import androidx.test.platform.app.InstrumentationRegistry
import com.team96.speakeasy.MainActivity
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Test

/** Public calibration PCM only. Every VAD abstention is counted; no microphone is opened. */
class BackboneCaptureInstrumentedTest {
    private val assets get()=InstrumentationRegistry.getInstrumentation().context.assets
    private data class Stats(var cases:Int=0,var paired:Int=0,var phones:Int=0,var oldEdits:Int=0,var newEdits:Int=0,
        var oldUnavailable:Int=0,var newUnavailable:Int=0,var modelErrors:Int=0)
    private fun pcm(entry:JSONObject):ShortArray {
        val bytes=assets.open("backbone-capture-fixtures/${entry.getString("file")}").use{it.readBytes()}
        try {
            PhonemeCtcDecoder.verifySha(bytes,entry.getString("sha256"));var offset=12
            while(offset+8<=bytes.size) {
                val length=(0..3).sumOf{(bytes[offset+4+it].toInt() and 255) shl (8*it)}
                require(length>=0 && offset+8L+length<=bytes.size)
                if(String(bytes,offset,4,Charsets.US_ASCII)=="data")return ShortArray(length/2){i->
                    ((bytes[offset+8+i*2].toInt() and 255) or (bytes[offset+9+i*2].toInt() shl 8)).toShort()}
                offset+=8+length+length%2
            }
            error("Public PCM chunk missing")
        } finally {bytes.fill(0)}
    }
    private fun distance(a:List<String>,b:List<String>):Int {
        var row=IntArray(b.size+1){it}
        for((i,x)in a.withIndex()) {
            val next=IntArray(b.size+1);next[0]=i+1
            for((j,y)in b.withIndex())next[j+1]=minOf(next[j]+1,row[j+1]+1,row[j]+if(x==y)0 else 1)
            row=next
        }
        return row.last()
    }
    @Test fun all25WordsKeepPairedCoverageAndImproveQuietEndingsWithoutCleanRegression() {
        org.junit.Assume.assumeTrue("Rejected profile experiment is opt-in",InstrumentationRegistry.getArguments().getString("run_capture_window_experiment")=="true")
        val evidence=JSONObject(assets.open("backbone-capture-fixtures/manifest.json").bufferedReader().use{it.readText()})
        assertTrue(evidence.getBoolean("calibration_only"));assertFalse(evidence.getBoolean("private_audio"))
        val cases=evidence.getJSONArray("cases");assertEquals(256,cases.length())
        val stats=mapOf("clean" to Stats(),"quiet_last150ms" to Stats());val started=SystemClock.elapsedRealtime()
        val context=ApplicationProvider.getApplicationContext<android.content.Context>()
        ActivityScenario.launch(MainActivity::class.java).use{scenario->
            scenario.onActivity{it.window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)}
            MobileWordPracticeEngine.createForBackboneValidation(context).use{engine->
                repeat(cases.length()){index->
                    val entry=cases.getJSONObject(index);assertEquals("calibration",entry.getString("source_split"))
                    val values=pcm(entry)
                    try {
                        val reference=entry.getJSONArray("reference").let{array->List(array.length()){array.getString(it)}}
                        val old=engine.assessBackboneWindowForValidation(entry.getString("word_id"),values,BackboneCaptureProfile.LEGACY)
                        val next=engine.assessBackboneWindowForValidation(entry.getString("word_id"),values,BackboneCaptureProfile.CONSERVATIVE_V1)
                        assertEquals("UNSCORABLE",old.decision);assertEquals("UNSCORABLE",next.decision)
                        fun operational(value:LocalWordOutcome)=value.reason in setOf("PHONEME_TOKENS","PHONEME_EMPTY")
                        val group=stats.getValue(entry.getString("kind"));group.cases++
                        if(!operational(old))group.oldUnavailable++
                        if(!operational(next))group.newUnavailable++
                        if(old.reason=="MODEL_UNAVAILABLE" || next.reason=="MODEL_UNAVAILABLE")group.modelErrors++
                        if(operational(old) && operational(next)) {
                            group.paired++;group.phones+=reference.size
                            group.oldEdits+=distance(reference,old.predictedPhonemes.orEmpty())
                            group.newEdits+=distance(reference,next.predictedPhonemes.orEmpty())
                        }
                    } finally {values.fill(0)}
                    if(index%16==0)Log.i("VaakMitraCaptureWindow","public completed=${index+1} total=256 elapsedMs=${SystemClock.elapsedRealtime()-started}")
                }
            }
        }
        for((kind,s)in stats) {
            Log.i("VaakMitraCaptureWindow","summary kind=$kind cases=${s.cases} paired=${s.paired} phones=${s.phones} legacyEdits=${s.oldEdits} conservativeEdits=${s.newEdits} legacyUnavailable=${s.oldUnavailable} conservativeUnavailable=${s.newUnavailable} modelErrors=${s.modelErrors} calibrationOnly=true")
            assertEquals(128,s.cases);assertTrue(s.paired>0);assertEquals(0,s.modelErrors)
            assertTrue("Capture coverage regressed for $kind",s.newUnavailable<=s.oldUnavailable)
        }
        assertTrue("Clean paired phones regressed",stats.getValue("clean").newEdits<=stats.getValue("clean").oldEdits)
        assertTrue("Quiet-ending paired phones did not improve",stats.getValue("quiet_last150ms").newEdits<stats.getValue("quiet_last150ms").oldEdits)
    }
}
