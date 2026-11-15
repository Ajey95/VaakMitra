package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test

/** DEC075/PHN016: unverified candidate cannot replace the normal verified preview. */
class SharedBackboneVariantContractTest {
    private val base=BackboneBundleContract("phoneme.fp32.onnx","a".repeat(64),1_000_000L,"c".repeat(64),true)
    private fun fields():MutableMap<String,Any?> = mutableMapOf(
        "schema" to "vaakmitra.shared_backbone.v1","model_file" to "phoneme.shared.onnx","model_sha256" to "b".repeat(64),"model_bytes" to 12345,
        "base_sha256" to base.modelSha256,"base_bytes" to base.modelBytes,"vocabulary_sha256" to base.vocabularySha256,
        "relative_base" to "shared/phoneme.fp32.onnx","raw_preview_qualified" to true,"desktop_verified" to true,"android_verified" to false,
        "sound_corrections_qualified" to false,"approved_for_child_scoring" to false,"clinical_assessment" to false,
        "max_external_tensors" to 423,"external_ranges" to listOf(listOf(100,400),listOf(600,200)),
    )
    @Test fun phn016DefaultRejectsCandidateButExplicitValidationAccepts(){
        assertThrows(IllegalArgumentException::class.java){SharedBackboneVariantContract.parse(fields(),base)}
        val value=SharedBackboneVariantContract.parse(fields(),base,true)
        assertFalse(value.androidVerified);assertEquals("b".repeat(64),value.modelSha256)
    }
    @Test fun phn016NormalPreviewRequiresActualAndroidVerification(){
        val data=fields();data["android_verified"]=true
        assertTrue(SharedBackboneVariantContract.parse(data,base).androidVerified)
    }
    @Test fun phn016BaseAndVocabularyMismatchFailClosed(){
        for(key in listOf("base_sha256","vocabulary_sha256")){
            val data=fields();data[key]="d".repeat(64)
            assertThrows(IllegalArgumentException::class.java){SharedBackboneVariantContract.parse(data,base,true)}
        }
    }
    @Test fun phn016ClinicalOrCorrectionFlagsCannotBeSmuggledThroughPreview(){
        for(key in listOf("sound_corrections_qualified","approved_for_child_scoring","clinical_assessment")){
            val data=fields();data[key]=true
            assertThrows(IllegalArgumentException::class.java){SharedBackboneVariantContract.parse(data,base,true)}
        }
    }
    @Test fun phn016PathsAndOversizedGraphRejected(){
        for(key in listOf("relative_base","model_file")){
            val data=fields();data[key]="../other.onnx"
            assertThrows(IllegalArgumentException::class.java){SharedBackboneVariantContract.parse(data,base,true)}
        }
        val data=fields();data["model_bytes"]=49*1024*1024
        assertThrows(IllegalArgumentException::class.java){SharedBackboneVariantContract.parse(data,base,true)}
    }
    @Test fun phn016ExternalSlicesMustBePositiveInBoundsAndNotDuplicated(){
        for(ranges in listOf(listOf(listOf(-1,4)),listOf(listOf(999999,4)),listOf(listOf(0,0)),listOf(listOf(0,4),listOf(0,4)))){
            val data=fields();data["external_ranges"]=ranges
            assertThrows(IllegalArgumentException::class.java){SharedBackboneVariantContract.parse(data,base,true)}
        }
    }
    @Test fun phn016FailedCandidateLoadsBaselineAndReportsItsActualIdentity(){
        val baseFile=java.io.File("base");val variantFile=java.io.File("variant");val attempts=mutableListOf<String>()
        val selected=openBackboneWithFallback(baseFile,base.modelSha256,BackboneVariantChoice(variantFile,"b".repeat(64))){file->
            attempts+=file.name;if(file==variantFile)throw IllegalStateException("invalid graph");"baseline-session"
        }
        assertEquals(listOf("variant","base"),attempts);assertEquals(base.modelSha256,selected.second)
    }
    @Test fun phn016SuccessfulCandidateReportsNewFingerprint(){
        val choice=BackboneVariantChoice(java.io.File("variant"),"b".repeat(64))
        val selected=openBackboneWithFallback(java.io.File("base"),base.modelSha256,choice){it.name}
        assertEquals("variant",selected.first);assertEquals(choice.modelSha256,selected.second)
    }
}
