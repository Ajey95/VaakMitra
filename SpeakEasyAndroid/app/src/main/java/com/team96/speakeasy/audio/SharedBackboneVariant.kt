package com.team96.speakeasy.audio

import android.content.Context
import android.system.Os
import com.team96.speakeasy.BuildConfig
import java.io.File
import java.io.FileOutputStream
import java.security.MessageDigest
import org.json.JSONObject
import org.json.JSONArray

/** PHN016: local model bytes only; no recording, networking or session navigation. */
object SharedBackboneVariant {
    private const val ROOT="vaakmitra/phoneme-ta-backbone-v1/variants"
    private val lock=Any()
    fun prepare(context:Context,baseFile:File,base:BackboneBundleContract,allowCalibrationOnly:Boolean=false,baseIdentityVerified:Boolean=false):BackboneVariantChoice? =
        runCatching{synchronized(lock){
            val assets=context.applicationContext.assets
            val header=assets.open("$ROOT/variant.json").bufferedReader().use{it.readText()}
            require(header.length<=65536)
            val contract=SharedBackboneVariantContract.parse(fields(JSONObject(header)),base,BuildConfig.DEBUG && allowCalibrationOnly)
            require(baseFile.isFile && baseFile.length()==base.modelBytes)
            require(baseIdentityVerified || hash(baseFile)==base.modelSha256)
            val directory=File(baseFile.parentFile,"variants/${contract.modelSha256}").apply{check(mkdirs() || isDirectory)}
            val shared=File(directory,"shared").apply{check(mkdirs() || isDirectory)}
            val alias=File(shared,"phoneme.fp32.onnx")
            if(!alias.exists())Os.link(baseFile.absolutePath,alias.absolutePath)
            val actual=Os.stat(alias.absolutePath);val original=Os.stat(baseFile.absolutePath)
            require(actual.st_dev==original.st_dev && actual.st_ino==original.st_ino){"shared_base_link_identity"}
            val destination=File(directory,contract.modelFile)
            if(!verified(destination,contract)){
                require(!destination.exists()){"shared_immutable_cache_corrupt"}
                val partial=File.createTempFile("shared-",".partial",directory)
                try{
                    assets.open("$ROOT/${contract.modelFile}").use{input->FileOutputStream(partial).use{output->
                        val block=ByteArray(65536);var total=0L
                        while(true){val count=input.read(block);if(count<0)break;total+=count;require(total<=contract.modelBytes);output.write(block,0,count)}
                        output.fd.sync();require(total==contract.modelBytes)
                    }}
                    require(verified(partial,contract));check(partial.renameTo(destination))
                }finally{if(partial.exists())partial.delete()}
            }
            BackboneVariantChoice(destination,contract.modelSha256)
        }}.getOrNull()
    private fun verified(file:File,contract:SharedBackboneVariantContract)=file.isFile && file.length()==contract.modelBytes && hash(file)==contract.modelSha256
    private fun hash(file:File):String {
        val digest=MessageDigest.getInstance("SHA-256")
        file.inputStream().buffered().use{input->val block=ByteArray(1024*1024);while(true){val count=input.read(block);if(count<0)break;digest.update(block,0,count)}}
        return digest.digest().joinToString(""){"%02x".format(it)}
    }
    private fun convert(value:Any?):Any? = when(value){
        is JSONObject->fields(value)
        is JSONArray->List(value.length()){convert(value.get(it))}
        JSONObject.NULL->null
        else->value
    }
    private fun fields(value:JSONObject):Map<String,Any?> = value.keys().asSequence().associateWith{convert(value.get(it))}
}
