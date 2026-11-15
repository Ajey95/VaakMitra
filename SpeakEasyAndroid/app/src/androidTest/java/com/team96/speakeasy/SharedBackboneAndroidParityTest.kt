package com.team96.speakeasy

import ai.onnxruntime.*
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.team96.speakeasy.audio.*
import org.json.JSONObject
import org.json.JSONArray
import org.junit.Assert.*
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.nio.LongBuffer
import kotlin.math.ln
import kotlin.math.abs

/** PHN016: explicit pinned public-fixture check; no Activity or microphone. */
@RunWith(AndroidJUnit4::class)
class SharedBackboneAndroidParityTest {
    private fun convert(value:Any?):Any? = when(value){
        is JSONObject->value.keys().asSequence().associateWith{convert(value.get(it))}
        is JSONArray->List(value.length()){convert(value.get(it))}
        JSONObject.NULL->null
        else->value
    }
    private fun fields(value:JSONObject):Map<String,Any?> = value.keys().asSequence().associateWith{convert(value.get(it))}
    private fun floats(bytes:ByteArray,count:Int,sha:String):FloatArray {
        try{
            SharedBackboneParityContract.verifyBytes(bytes,count*4,sha)
            return FloatArray(count).also{
                ByteBuffer.wrap(bytes).order(ByteOrder.LITTLE_ENDIAN).asFloatBuffer().get(it)
                require(it.all(Float::isFinite))
            }
        }finally{bytes.fill(0)}
    }
    @Test fun sharedCandidateMatchesCpuReferenceWithoutRecording(){
        val context=InstrumentationRegistry.getInstrumentation().targetContext
        val root=OnnxBackbonePhoneme.ROOT;val assets=context.assets
        val header=JSONObject(assets.open("$root/bundle.json").bufferedReader().use{it.readText()})
        val base=BackboneBundleContract.parse(fields(header),true)
        val source=File(context.noBackupFilesDir,"phoneme-models/${base.modelSha256}.onnx")
        assertTrue("Provision the pinned original base before this explicit test",source.isFile)
        val candidate=checkNotNull(SharedBackboneVariant.prepare(context,source,base,allowCalibrationOnly=true))
        assertEquals(SharedBackboneParityContract.SELECTED_MODEL,candidate.modelSha256)
        val fixtureRoot="$root/variants/parity"
        val manifest=assets.open("$fixtureRoot/manifest.json").use{it.readBytes()}
        val cases=try{
            SharedBackboneParityContract.verifyBytes(manifest,manifest.size,"5574a883794459b3a71d2f387679392cd49a2f114021e998a4168713aca2d7e9")
            SharedBackboneParityContract.parse(fields(JSONObject(String(manifest,Charsets.UTF_8))),candidate.modelSha256)
        }finally{manifest.fill(0)}
        val vocabulary=JSONObject(assets.open("$root/vocabulary.json").bufferedReader().use{it.readText()}).getJSONArray("tokens")
        val tokens=List(vocabulary.length()){vocabulary.getString(it)}
        assertEquals(39,tokens.size)
        val environment=OrtEnvironment.getEnvironment();var completed=0
        OrtSession.SessionOptions().use{options->
            options.setIntraOpNumThreads(2);options.setInterOpNumThreads(1)
            options.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
            options.setMemoryPatternOptimization(false);options.setCPUArenaAllocator(false)
            environment.createSession(candidate.file.absolutePath,options).use{session->
                for(row in cases){
                    var values=FloatArray(0);var expected=FloatArray(0);var mask=LongArray(0)
                    try{
                        values=floats(assets.open("$fixtureRoot/${row.valuesFile}").use{it.readBytes()},row.samples,row.valuesSha256)
                        expected=floats(assets.open("$fixtureRoot/${row.logpFile}").use{it.readBytes()},row.frames*row.units,row.logpSha256)
                        mask=LongArray(values.size){1L}
                        OnnxTensor.createTensor(environment,FloatBuffer.wrap(values),longArrayOf(1,values.size.toLong())).use{wave->
                            OnnxTensor.createTensor(environment,LongBuffer.wrap(mask),longArrayOf(1,values.size.toLong())).use{attention->
                                session.run(mapOf("waveform" to wave,"attention_mask" to attention)).use{result->
                                    @Suppress("UNCHECKED_CAST") val output=result[0].value as Array<Array<FloatArray>>
                                    try{
                                        assertEquals(1,output.size)
                                        val frames=output[0]
                                        SharedBackboneParityContract.verifyOutput(frames,row.frames,row.units)
                                        assertEquals(row.phones,BackbonePhones.decode(frames,tokens))
                                        val evidence=OwnedPosteriorEvidence.fromLogits(frames,tokens)
                                        try{
                                            var error=0.0
                                            evidence.probabilities.forEachIndexed{f,p->p.forEachIndexed{j,value->error=maxOf(error,abs(ln(value.toDouble())-expected[f*tokens.size+j]))}}
                                            assertTrue("CPU/native log-probability drift: $error",error.isFinite() && error<.02)
                                        }finally{evidence.close()}
                                        completed++
                                    }finally{output.forEach{batch->batch.forEach{it.fill(0f)}}}
                                }
                            }
                        }
                    }finally{values.fill(0f);expected.fill(0f);mask.fill(0)}
                }
            }
        }
        assertEquals("Every pinned fixture must complete",3,completed)
    }
}

