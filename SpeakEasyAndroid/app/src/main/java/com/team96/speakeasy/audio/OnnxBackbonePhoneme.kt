package com.team96.speakeasy.audio

import android.content.Context
import ai.onnxruntime.*
import java.io.File
import java.io.FileOutputStream
import java.nio.FloatBuffer
import java.nio.LongBuffer
import java.security.MessageDigest
import org.json.JSONObject

data class BackboneObservation(val phones:List<String>,val validFrames:Int,val modelSha256:String,val supported:Boolean,
    val frameEvidence:OwnedPosteriorEvidence?=null)

/** Waveform-only inference. Expected words never enter this adapter or its decoder. */
class OnnxBackbonePhoneme(context:Context,allowCalibrationOnly:Boolean=false,allowSharedCandidate:Boolean=false):AutoCloseable {
    private val environment=OrtEnvironment.getEnvironment()
    private val options=OrtSession.SessionOptions().apply {
        setIntraOpNumThreads(2);setInterOpNumThreads(1)
        setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
        setMemoryPatternOptimization(false);setCPUArenaAllocator(false)
        addConfigEntry("session.intra_op.allow_spinning","0");addConfigEntry("session.inter_op.allow_spinning","0")
    }
    private val session:OrtSession
    private val tokens:List<String>
    val knownTokens:Set<String>
    val modelSha256:String
    private var closed=false
    init {
        var loaded:OrtSession?=null
        try {
            val assets=context.applicationContext.assets
            val header=JSONObject(assets.open("$ROOT/bundle.json").bufferedReader().use{it.readText()})
            val fields=header.keys().asSequence().associateWith{key->
                val value=header.get(key)
                if(value is JSONObject)value.keys().asSequence().associateWith{value.get(it)} else value
            }
            val contract=BackboneBundleContract.parse(fields,allowCalibrationOnly)
            val vocabulary=assets.open("$ROOT/vocabulary.json").use{it.readBytes()}
            try {
                PhonemeCtcDecoder.verifySha(vocabulary,contract.vocabularySha256)
                val payload=JSONObject(String(vocabulary,Charsets.UTF_8))
                val array=payload.getJSONArray("tokens")
                tokens=List(array.length()){array.getString(it)}
                require(tokens.size==39 && tokens.distinct().size==39 && tokens.first()=="<blank>" && tokens.all{it.isNotEmpty()})
                require(PhonemeAudio.exactInteger(payload.get("frame_shift_ms"))==20)
            } finally {vocabulary.fill(0)}
            knownTokens=BackbonePhones.known(tokens)
            val file=synchronized(cacheLock) {
                val directory=File(context.noBackupFilesDir,"phoneme-models").apply{check(mkdirs() || isDirectory)}
                val destination=File(directory,"${contract.modelSha256}.onnx")
                if(!verified(destination,contract)) {
                    val partial=File.createTempFile("backbone-",".partial",directory)
                    try {
                        assets.open("$ROOT/${contract.modelFile}").use{source->
                            FileOutputStream(partial).use{output->source.copyTo(output);output.fd.sync()}
                        }
                        require(verified(partial,contract)){"backbone_model_identity"}
                        check(partial.renameTo(destination)){"backbone_model_cache_publish"}
                    } finally {if(partial.exists())check(partial.delete())}
                }
                destination
            }
            val candidate=SharedBackboneVariant.prepare(context,file,contract,allowCalibrationOnly && allowSharedCandidate,baseIdentityVerified=true)
            val active=openBackboneWithFallback(file,contract.modelSha256,candidate,::checkedSession)
            loaded=active.first;modelSha256=active.second;session=active.first
        } catch(error:Throwable) {runCatching{loaded?.close()};options.close();throw error}
    }
    private fun checkedSession(file:File):OrtSession {
        val loaded=environment.createSession(file.absolutePath,options)
        try{
            require(loaded.inputNames==setOf("waveform","attention_mask") && loaded.outputNames==setOf("logits"))
            for((name,type)in mapOf("waveform" to OnnxJavaType.FLOAT,"attention_mask" to OnnxJavaType.INT64)){
                val info=loaded.inputInfo.getValue(name).info as TensorInfo
                require(info.type==type && info.shape.contentEquals(longArrayOf(1,-1)))
            }
            val output=loaded.outputInfo.getValue("logits").info as TensorInfo
            require(output.type==OnnxJavaType.FLOAT && output.shape.size==3 && output.shape[0] in longArrayOf(1,-1) && output.shape[1]==-1L && output.shape[2]==39L)
            return loaded
        }catch(error:Throwable){loaded.close();throw error}
    }
    @Synchronized fun inferObservation(samples:ShortArray,includeFrames:Boolean=false):BackboneObservation {
        check(!closed)
        val prepared=BackboneAudio.prepare(samples)
        try {
            OnnxTensor.createTensor(environment,FloatBuffer.wrap(prepared.waveform),longArrayOf(1,samples.size.toLong())).use{wave->
                OnnxTensor.createTensor(environment,LongBuffer.wrap(prepared.mask),longArrayOf(1,samples.size.toLong())).use{mask->
                    session.run(mapOf("waveform" to wave,"attention_mask" to mask)).use{result->
                        @Suppress("UNCHECKED_CAST") val output=result[0].value as Array<Array<FloatArray>>
                        try {
                            require(output.size==1 && output[0].size==prepared.validFrames)
                            val phones=BackbonePhones.decode(output[0],tokens)
                            val frames=if(includeFrames)OwnedPosteriorEvidence.fromLogits(output[0],tokens)else null
                            return BackboneObservation(phones,prepared.validFrames,modelSha256,BackbonePhones.supported(phones),frames)
                        } finally {output.forEach{batch->batch.forEach{it.fill(0f)}}}
                    }
                }
            }
        } finally {prepared.erase()}
    }
    @Synchronized override fun close(){if(!closed){closed=true;try{session.close()}finally{options.close()}}}
    companion object {
        const val ROOT="vaakmitra/phoneme-ta-backbone-v1"
        private val cacheLock=Any()
        private fun verified(file:File,contract:BackboneBundleContract):Boolean {
            if(!file.isFile || file.length()!=contract.modelBytes)return false
            val digest=MessageDigest.getInstance("SHA-256")
            file.inputStream().buffered().use{input->val block=ByteArray(1024*1024);while(true){val n=input.read(block);if(n<0)break;digest.update(block,0,n)}}
            return digest.digest().joinToString(""){"%02x".format(it)}==contract.modelSha256
        }
    }
}
