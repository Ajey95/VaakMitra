package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test

/** DEC068/PHN009: no token comparison becomes a verified child defect or score. */
class PhoneticSupportTest {
    @org.junit.Test fun previewWithoutCalibratedAcousticConfidenceStaysGeneric() {
        val help=PhoneticSupportPolicy.fromPreview(listOf("a","m","aː"),listOf("a","m","m","aː"),setOf("a","m","aː"))
        org.junit.Assert.assertEquals("generic_help",help.basis)
        org.junit.Assert.assertTrue(help.candidatePatterns.isEmpty())
        org.junit.Assert.assertEquals("UNSCORABLE",help.decision)
    }
    private val known=setOf("a","aː","m","p","n","i","iː")
    private fun choose(heard:List<String>,reference:List<String>)=
        PhoneticSupportPolicy.choose(heard,reference,known,evidenceValid=true,modelQualified=true)
    @Test fun normalGeminatesAndLongVowelsArePreserved() {
        val result=choose(listOf("a","m","m","aː"),listOf("a","m","m","aː"))
        assertTrue(result.candidatePatterns.isEmpty());assertEquals("none",result.action)
        assertEquals("UNSCORABLE",result.decision)
        assertEquals(listOf("possible_substitution"),choose(listOf("a"),listOf("aː")).candidatePatterns)
    }
    @Test fun localSequenceDifferencesAreOnlyPossiblePatterns() {
        assertEquals(listOf("possible_repetition"),choose(listOf("a","m","m","m","aː"),listOf("a","m","m","aː")).candidatePatterns)
        assertEquals(listOf("possible_omission"),choose(listOf("a","m","aː"),listOf("a","m","m","aː")).candidatePatterns)
        assertEquals(listOf("possible_substitution"),choose(listOf("p"),listOf("m")).candidatePatterns)
    }
    @Test fun ambiguityAndEarlierUnsupportedInsertionsStayGeneric() {
        for((heard,target)in listOf(listOf("m","a")to listOf("a","m"),listOf("a","m","m","n")to listOf("n"),listOf("[UNK]")to listOf("a"))) {
            val result=choose(heard,target);assertTrue(result.candidatePatterns.isEmpty());assertEquals("adult_example",result.action)
        }
    }
    @Test fun unsupportedModelAndCaptureEvidenceNeverInventAssessment() {
        val result=PhoneticSupportPolicy.choose(listOf("p"),listOf("m"),known,evidenceValid=false,modelQualified=false)
        assertTrue(result.candidatePatterns.isEmpty());assertEquals("UNSCORABLE",result.decision)
    }
    @Test fun stopBreakAndAllowedActionsOverrideAcousticHypotheses() {
        assertEquals("safe_end",PhoneticSupportPolicy.choose(listOf("a"),listOf("m"),known,stopRequested=true).action)
        assertEquals("break",PhoneticSupportPolicy.choose(listOf("a"),listOf("m"),known,breakRequested=true).action)
        assertEquals("none",PhoneticSupportPolicy.choose(listOf("a"),listOf("m"),known,allowedActions=emptySet()).action)
        assertEquals("picture",PhoneticSupportPolicy.choose(listOf("a"),listOf("m"),known,allowedActions=setOf("picture")).action)
    }
}
