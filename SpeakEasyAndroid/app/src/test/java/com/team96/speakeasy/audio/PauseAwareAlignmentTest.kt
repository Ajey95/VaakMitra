package com.team96.speakeasy.audio

import org.junit.Assert.*
import org.junit.Test

/** DEC071/PHN012: reference support remains diagnostic and preserves phonetic distinctions. */
class PauseAwareAlignmentTest {
    private val tokens=listOf("<blank>","a","aː","m","s","ʂ","[UNK]")
    private fun frames(vararg ids:Int)=Array(ids.size){i->FloatArray(tokens.size){j->if(j==ids[i]).994f else .001f}}
    @Test fun phn012StretchAndSilenceAlignWithoutInventingPhones(){
        val result=PauseAwareAlignment.align(frames(1,1,1,0,0,0,3,3,0,2,2),tokens,listOf("a","m","aː"))
        assertEquals("diagnostic_only",result.status)
        assertEquals(listOf("model_support","model_support","model_support"),result.phones.map{it.kind})
        assertEquals(6,result.phones[1].startFrame)
    }
    @Test fun phn012GeminatesAndLongVowelsAreRetained(){
        val result=PauseAwareAlignment.align(frames(1,0,3,0,3,0,2),tokens,listOf("a","m","m","aː"))
        assertEquals(listOf("a","m","m","aː"),result.phones.map{it.observed})
    }
    @Test fun phn012OmissionIsOnlyAnUnconfirmedHypothesis(){
        val result=PauseAwareAlignment.align(frames(1,1,0,2,2),tokens,listOf("a","m","aː"))
        assertEquals("m",result.phones.single{it.kind=="possible_omission"}.expected)
        assertFalse(result.phones.any{it.confirmed})
    }
    @Test fun phn012UnsupportedShAndSilentInputAbstain(){
        assertEquals("unsupported_reference",PauseAwareAlignment.align(frames(4,4),tokens,listOf("ʃ")).status)
        assertEquals("insufficient_evidence",PauseAwareAlignment.align(frames(0,0),tokens,listOf("m")).status)
    }
    @Test fun phn012MalformedProbabilitiesCannotProduceSupport(){
        assertEquals("invalid_evidence",PauseAwareAlignment.align(arrayOf(floatArrayOf(Float.NaN)),tokens,listOf("m")).status)
        assertEquals("invalid_evidence",PauseAwareAlignment.align(arrayOf(FloatArray(7){2f}),tokens,listOf("m")).status)
    }
    @Test fun coa002ToolViewContainsNoRecordingRepresentationOrUnqualifiedDifference(){
        val result=PauseAwareAlignment.align(frames(1,0,2),tokens,listOf("a","m","aː"))
        val tool=PracticeVoiceCoach.toolResult("TA_WORD_0001",result,PracticeCoachCue.QUIET)
        assertTrue(tool.localOnly)
        assertEquals("low_recording_level",tool.recordingCondition)
        assertTrue(tool.possibleDifferences.isEmpty())
        assertEquals("insufficient_evidence",tool.evidenceStatus)
        assertTrue(tool.forbiddenActions.contains("claim_child_error"))
    }
    @Test fun phn012OwnedFrameEvidenceIsErasedAfterAlignment(){
        val evidence=OwnedPosteriorEvidence.fromLogits(arrayOf(floatArrayOf(0f,5f,0f)),listOf("<blank>","a","m"))
        assertTrue(evidence.probabilities[0][1]>.9f)
        evidence.close()
        assertTrue(evidence.probabilities.all{row->row.all{it==0f}})
    }
    @Test fun phn012CompoundNativeUnitsCannotManufactureMissingSplitPhones(){
        val units=listOf("<blank>","k","a","j","aj")
        val p=Array(4){i->FloatArray(5){j->if(j==if(i<2)1 else 4).996f else .001f}}
        val result=PauseAwareAlignment.align(p,units,listOf("k","a","j"))
        assertEquals("insufficient_evidence",result.status);assertTrue(result.phones.isEmpty())
    }
    @Test fun phn012TiedOptimalAttributionsCannotNameAMissingSound(){
        val result=PauseAwareAlignment.align(frames(4),tokens,listOf("a","m"))
        assertEquals("ambiguous_alignment",result.status);assertTrue(result.phones.isEmpty())
    }
}
