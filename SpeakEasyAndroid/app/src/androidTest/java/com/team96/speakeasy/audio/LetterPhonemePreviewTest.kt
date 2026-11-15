package com.team96.speakeasy.audio
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import org.junit.Assert.*
import org.junit.Test
import org.junit.Before
import org.junit.After
import androidx.test.core.app.ActivityScenario
import com.team96.speakeasy.MainActivity
import org.junit.runner.RunWith

/** DEC-056/PHN003: public fixture, same waveform/phones across letter metadata, no microphone. */
@RunWith(AndroidJUnit4::class)
class LetterPhonemePreviewTest {
    private var foreground:ActivityScenario<MainActivity>?=null
    /** Public inference needs a foreground owner on this phone's background-freezer policy. */
    @Before fun keepPublicInferenceForeground(){
        foreground=ActivityScenario.launch(MainActivity::class.java)
        foreground?.onActivity{it.window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)}
    }
    @After fun closePublicInferenceForeground(){foreground?.close();foreground=null}
    @Test fun letterPreviewIsUnscorableRejectsUnknownAndNeverForcesThePrompt() {
        val instrumentation=InstrumentationRegistry.getInstrumentation()
        val bytes=instrumentation.context.assets.open("phoneme-fixtures/adult-test.wav").use{it.readBytes()}
        var offset=12;var pcm=shortArrayOf()
        while(offset+8<=bytes.size){
            val length=(0..3).sumOf{(bytes[offset+4+it].toInt() and 255) shl (8*it)}
            if(String(bytes,offset,4,Charsets.US_ASCII)=="data"){
                pcm=ShortArray(length/2){i->((bytes[offset+8+2*i].toInt() and 255) or (bytes[offset+9+2*i].toInt() shl 8)).toShort()};break
            }
            offset+=8+length+length%2
        }
        bytes.fill(0)
        val recording=ShortArray(pcm.size+6400);pcm.copyInto(recording,3200)
        try{MobileWordPracticeEngine.create(instrumentation.targetContext,true).use{engine->
            val first=engine.assessLetter("TA_LETTER_UYIR_01",recording)
            val second=engine.assessLetter("TA_LETTER_UYIR_02",recording)
            assertEquals("UNSCORABLE",first.decision)
            assertEquals("PHONEME_TOKENS",first.reason)
            assertEquals(first.predictedPhonemes,second.predictedPhonemes)
            assertEquals("TARGET_UNAVAILABLE",engine.assessLetter("unknown",recording).reason)
        }}finally{pcm.fill(0);recording.fill(0)}
    }
}
