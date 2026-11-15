package com.team96.speakeasy.audio
import org.junit.Assert.*
import org.junit.Test

class AdultPromptGateTest {
    private fun trials()=List(15){i->AdultPromptTrial("word${i/3}",1,0,4,true,true)}
    @Test fun baselineFailuresAreInconclusiveInsteadOfInventedDeletions() {
        val failed=trials().map{it.copy(baselineEdits=-1,baselineOperational=false)}
        val result=AdultPromptGate.evaluate(failed)
        assertTrue(result.inconclusive);assertFalse(result.qualified);assertEquals(0,result.pairedTrials)
    }
    @Test fun validPairsCanPassButMissingCandidateOrTrialsCannot() {
        assertTrue(AdultPromptGate.evaluate(trials()).qualified)
        assertFalse(AdultPromptGate.evaluate(trials().dropLast(1)).qualified)
        assertTrue(AdultPromptGate.evaluate(trials().map{it.copy(candidateOperational=false,candidateEdits=-1)}).inconclusive)
    }
}
