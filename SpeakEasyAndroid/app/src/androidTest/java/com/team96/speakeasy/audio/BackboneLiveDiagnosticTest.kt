package com.team96.speakeasy.audio

import android.Manifest
import android.app.AlertDialog
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import androidx.test.core.app.ActivityScenario
import androidx.test.platform.app.InstrumentationRegistry
import com.team96.speakeasy.MainActivity
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test

/** Adult operator comparison only. Record taps are mandatory; no audio/phones are saved or logged. */
class BackboneLiveDiagnosticTest {
    private data class Prompt(val id:String,val tamil:String,val roman:String)
    private data class Counts(val oldEdits:Int,val candidateEdits:Int,val phones:Int,val baselineAccepted:Boolean,val candidateAccepted:Boolean,
        val candidatePhones:Int=-1,val initialMatch:Int=-1,val finalMatch:Int=-1)
    private fun distance(a:List<String>,b:List<String>):Int {
        var row=IntArray(b.size+1){it}
        for((i,x)in a.withIndex()) {
            val next=IntArray(b.size+1);next[0]=i+1
            for((j,y)in b.withIndex())next[j+1]=minOf(next[j]+1,row[j+1]+1,row[j]+if(x==y)0 else 1)
            row=next
        }
        return row.last()
    }
    private fun accepted(outcome:LocalWordOutcome)=outcome.reason in setOf("PHONEME_TOKENS","PHONEME_EMPTY")

    private fun <T> memoryCapture(start:()->Boolean,stop:()->ShortArray,cancel:()->Unit,isCancelled:()->Boolean,
        now:()->Long,pause:()->Unit,status:(String)->Unit,operation:(ShortArray)->T):T {
        try {
            assumeTrue(!isCancelled());check(start()){"Microphone did not start"}
            val end=now()+2500;status("Listening — say the displayed word once now.")
            while(now()<end && !isCancelled())pause()
            assumeTrue(!isCancelled())
            val samples=stop()
            try {
                assumeTrue(!isCancelled());status("Comparing in memory. Audio is erased after this comparison.")
                val result=operation(samples);assumeTrue(!isCancelled());return result
            } finally {samples.fill(0)}
        } finally {cancel()}
    }

    private fun trial(scenario:ActivityScenario<MainActivity>,prompt:Prompt,ordinal:Int,total:Int=15,compare:(ShortArray)->Counts):Counts {
        val start=CountDownLatch(1);val cancelled=AtomicBoolean(false)
        val recorder=WordPcmRecorder(maxSamples=40000);val main=Handler(Looper.getMainLooper())
        val gate=AtomicReference<LifecycleRecordingGate>();val window=AtomicReference<AlertDialog>()
        fun cancel(){cancelled.set(true);start.countDown();RecordingCleanup.dispatch{recorder.cancel()}}
        try {
            scenario.onActivity{activity->
                val control=LifecycleRecordingGate(activity.lifecycle,::cancel);gate.set(control)
                val dialog=AlertDialog.Builder(activity)
                    .setTitle("${prompt.tamil} / ${prompt.roman} — $ordinal/$total")
                    .setMessage("Adult model comparison. Tap Record, wait for Listening, then say this word once naturally. Audio stays in memory and is erased after this comparison. No child score.")
                    .setPositiveButton("Record 2.5 seconds",null)
                    .setNegativeButton("Stop / cancel all"){_,_->control.cancel()}.create()
                dialog.setCanceledOnTouchOutside(false);dialog.setOnCancelListener{control.cancel()}
                dialog.setOnShowListener{dialog.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener{
                    it.isEnabled=false;dialog.setMessage("Starting microphone…");start.countDown()
                }}
                window.set(dialog);dialog.show()
            }
            check(start.await(120,TimeUnit.SECONDS)){"Operator wait timed out"}
            assumeTrue(!cancelled.get())
            val result=memoryCapture(
                start={gate.get()?.start{if(cancelled.get())false else recorder.start()}==true},
                stop=recorder::stop,cancel=recorder::cancel,isCancelled=cancelled::get,
                now=SystemClock::elapsedRealtime,pause={Thread.sleep(25)},
                status={message->main.post{if(!cancelled.get())window.get()?.setMessage(message)}},operation=compare,
            )
            var published=false
            scenario.onActivity{published=gate.get()?.publish{}==true}
            assumeTrue("Foreground comparison was cancelled",published)
            return result
        } finally {
            recorder.cancel()
            scenario.onActivity{gate.getAndSet(null)?.close();window.getAndSet(null)?.dismiss()}
        }
    }

    @Test fun memoryCaptureErasesPcmWhenComparisonFails() {
        var tick=0L;var released=false;val pcm=shortArrayOf(100,-200)
        val result=runCatching{memoryCapture<Int>({true},{pcm},{released=true},{false},{tick},{tick+=25},{},
            operation={throw IllegalStateException("controlled comparison failure")})}
        assertTrue(result.exceptionOrNull() is IllegalStateException)
        assertEquals(2500L,tick);assertTrue(released);assertTrue(pcm.all{it==0.toShort()})
    }

    @Test fun operatorRecords15AdultPromptsWithoutSavingAudio() {
        assumeTrue("Operator-only voice test requires explicit opt-in",InstrumentationRegistry.getArguments().getString("operator_voice_test")=="true")
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        check(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)
        val document=JSONObject(context.assets.open("vaakmitra/practice-words-v1/references.json").bufferedReader().use{it.readText()})
        val references=document.getJSONObject("expected")
        val prompts=listOf(Prompt("TA_WORD_0001","அம்மா","Amma"),Prompt("TA_WORD_0002","அப்பா","Appa"),
            Prompt("TA_WORD_0012","உணவு","Unavu"),Prompt("TA_WORD_0013","வேண்டும்","Vendum"),Prompt("TA_WORD_0100","சேர்ந்து","Serndhu"))
        val results=mutableListOf<AdultPromptTrial>()
        ActivityScenario.launch(MainActivity::class.java).use{scenario->
            scenario.onActivity{it.window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)}
            MobileWordPracticeEngine.createRetainedForComparison(context).use{old->
                MobileWordPracticeEngine.createForBackboneValidation(context).use{candidate->
                    for(prompt in prompts)repeat(3){
                        val expected=references.getJSONArray(prompt.id).let{array->List(array.length()){array.getString(it)}}
                        val counts=trial(scenario,prompt,results.size+1){samples->
                            val before=old.assess(prompt.id,samples);val after=candidate.assess(prompt.id,samples)
                            Counts(if(accepted(before))distance(expected,before.predictedPhonemes.orEmpty())else -1,
                                if(accepted(after))distance(expected,after.predictedPhonemes.orEmpty())else -1,
                                expected.size,accepted(before),accepted(after),after.predictedPhonemes.orEmpty().size,
                                if(after.predictedPhonemes?.firstOrNull()==expected.first())1 else 0,
                                if(after.predictedPhonemes?.lastOrNull()==expected.last())1 else 0)
                        }
                        results.add(AdultPromptTrial(prompt.id,counts.oldEdits,counts.candidateEdits,counts.phones,counts.baselineAccepted,counts.candidateAccepted))
                        Log.i("VaakMitraBackboneLive","trial=${results.size} referencePhones=${counts.phones} baselineEdits=${counts.oldEdits} candidateEdits=${counts.candidateEdits} candidatePhoneCount=${counts.candidatePhones} initialSoundMatch=${counts.initialMatch} finalSoundMatch=${counts.finalMatch} baselineOperational=${counts.baselineAccepted} candidateOperational=${counts.candidateAccepted} bufferErased=true")
                    }
                }
            }
        }
        val result=AdultPromptGate.evaluate(results)
        Log.i("VaakMitraBackboneLive","complete trials=${results.size} paired=${result.pairedTrials} exact=${result.exact} candidateEdits=${result.candidateEdits} referencePhones=${result.referencePhones} baselineEdits=${result.baselineEdits} eachWord=${result.eachWord} inconclusive=${result.inconclusive} engineeringPromptAgreement=${result.qualified} clinicalValidation=false")
        assertTrue("Adult comparison inconclusive or engineering gate failed; retain prior model",result.qualified)
    }

    @Test fun operatorChecksSoftSAndChWithoutChangingTheRecognizer() {
        assumeTrue("Operator-only voice test requires explicit opt-in",InstrumentationRegistry.getArguments().getString("operator_voice_test")=="true")
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        check(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)
        val refs=JSONObject(context.assets.open("vaakmitra/practice-words-v1/references.json").bufferedReader().use{it.readText()}).getJSONObject("expected")
        val array=refs.getJSONArray("TA_WORD_0100");val canonical=List(array.length()){array.getString(it)}
        require(canonical.first()=="t͡ʃ")
        ActivityScenario.launch(MainActivity::class.java).use{scenario->
            scenario.onActivity{it.window.addFlags(android.view.WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)}
            MobileWordPracticeEngine.createRetainedForComparison(context).use{old->
                MobileWordPracticeEngine.createForBackboneValidation(context).use{candidate->
                    repeat(4){i->
                        val soft=i%2==0
                        // These describe the sound explicitly requested BEFORE capture, never a decoder hint.
                        val expected=if(soft)listOf("s")+canonical.drop(1) else canonical
                        val prompt=Prompt("TA_WORD_0100","சேர்ந்து",if(soft) "Serndhu — soft s as in sun" else "Cherndhu — ch as in chair")
                        var initialMatch=0;var remainingMatch=0
                        val result=trial(scenario,prompt,i+1,4){samples->
                            val baseline=old.assess(prompt.id,samples);val observed=candidate.assess(prompt.id,samples)
                            val heard=observed.predictedPhonemes.orEmpty()
                            initialMatch=if(heard.firstOrNull()==expected.first())1 else 0
                            remainingMatch=if(heard.drop(1)==expected.drop(1))1 else 0
                            Counts(if(accepted(baseline))distance(expected,baseline.predictedPhonemes.orEmpty())else -1,
                                if(accepted(observed))distance(expected,heard)else -1,expected.size,accepted(baseline),accepted(observed))
                        }
                        Log.i("VaakMitraBackboneVariants","trial=${i+1} softVariant=${if(soft)1 else 0} referencePhones=${result.phones} candidateEdits=${result.candidateEdits} initialSoundMatch=$initialMatch remainingSoundsMatch=$remainingMatch operational=${result.candidateAccepted} bufferErased=true exploratory=true")
                        assertTrue("Exploratory capture unavailable",result.candidateAccepted)
                    }
                }
            }
        }
    }
}
