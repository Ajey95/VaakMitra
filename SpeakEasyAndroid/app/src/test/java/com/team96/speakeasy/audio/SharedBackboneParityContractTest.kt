package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test
import java.security.MessageDigest

/** PHN016: a parity PASS needs all three frozen public CPU fixtures. */
class SharedBackboneParityContractTest {
    private val sha="7103c31f472593f5bf9b50bf4ee6c29736cd2abe353f1113380a5ab03be9ae16"
    private val ids=listOf("mswc-ta-62298757f74a1b7bce74bf5c","mswc-ta-8cf15be71e9089a21001b097","mswc-ta-ca7bfca77348594ad88eee93")
    private fun row(i:Int)=mutableMapOf<String,Any?>(
        "index" to i,"source_id" to ids[i],"samples" to 16000,"frames" to 49,"units" to 39,
        "values_file" to "values-$i.f32","logp_file" to "logp-$i.f32",
        "values_sha256" to "a".repeat(64),"logp_sha256" to "b".repeat(64),
        "phones" to listOf("a","m"))
    private fun fields()=mutableMapOf<String,Any?>(
        "schema" to "PHN016-explicit-native-parity","model_sha256" to sha,
        "reference" to "CPU PyTorch exact merged weights","no_recording" to true,
        "cases" to (0..2).map(::row))
    @Test fun allThreeFrozenFixturesRequired(){
        assertEquals(3,SharedBackboneParityContract.parse(fields(),sha).size)
        for(cases in listOf(emptyList(),listOf(row(0)),listOf(row(0),row(0),row(2)))){
            val f=fields();f["cases"]=cases
            assertThrows(IllegalArgumentException::class.java){SharedBackboneParityContract.parse(f,sha)}
        }
    }
    @Test fun identityAndGraphCannotBeSubstituted(){
        for(key in listOf("model_sha256","reference","schema")){
            val f=fields();f[key]="other"
            assertThrows(IllegalArgumentException::class.java){SharedBackboneParityContract.parse(f,sha)}
        }
        val f=fields();val cases=(0..2).map(::row);cases[1]["source_id"]=ids[0];f["cases"]=cases
        assertThrows(IllegalArgumentException::class.java){SharedBackboneParityContract.parse(f,sha)}
    }
    @Test fun exactDimensionsAndSafeFilesRequired(){
        for((key,value)in listOf("samples" to 0,"frames" to 0,"units" to 1,"values_file" to "../other","logp_sha256" to "not-a-digest")){
            val f=fields();val cases=(0..2).map(::row);cases[0][key]=value;f["cases"]=cases
            assertThrows(IllegalArgumentException::class.java){SharedBackboneParityContract.parse(f,sha)}
        }
    }
    @Test fun byteIdentityAndLengthAreBothRequired(){
        val data=byteArrayOf(1,2,3,4);val digest=MessageDigest.getInstance("SHA-256").digest(data).joinToString(""){"%02x".format(it)}
        SharedBackboneParityContract.verifyBytes(data,4,digest)
        assertThrows(IllegalArgumentException::class.java){SharedBackboneParityContract.verifyBytes(data,8,digest)}
        assertThrows(IllegalArgumentException::class.java){SharedBackboneParityContract.verifyBytes(data,4,"f".repeat(64))}
    }
    @Test fun outputMustBeFiniteAndExactlySized(){
        SharedBackboneParityContract.verifyOutput(arrayOf(FloatArray(39)),1,39)
        for(output in listOf(emptyArray(),arrayOf(FloatArray(38)),arrayOf(FloatArray(39){Float.NaN}),arrayOf(FloatArray(39){Float.POSITIVE_INFINITY}))){
            assertThrows(IllegalArgumentException::class.java){SharedBackboneParityContract.verifyOutput(output,1,39)}
        }
    }
}

