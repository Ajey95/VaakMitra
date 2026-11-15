package com.team96.speakeasy.audio

data class AdultPromptTrial(val wordId:String,val baselineEdits:Int,val candidateEdits:Int,val referencePhones:Int,
    val baselineOperational:Boolean,val candidateOperational:Boolean)
data class AdultPromptResult(val qualified:Boolean,val inconclusive:Boolean,val pairedTrials:Int,val exact:Int,
    val candidateEdits:Int,val baselineEdits:Int,val referencePhones:Int,val eachWord:Boolean)

/** Provisional adult prompt agreement only; unavailable inference is never a phonetic deletion. */
object AdultPromptGate {
    fun evaluate(trials:List<AdultPromptTrial>):AdultPromptResult {
        require(trials.all{it.referencePhones>0 && (!it.baselineOperational || it.baselineEdits>=0) && (!it.candidateOperational || it.candidateEdits>=0)})
        val paired=trials.filter{it.baselineOperational && it.candidateOperational}
        val words=trials.groupBy{it.wordId}
        val incomplete=trials.size!=15 || words.size!=5 || words.values.any{it.size!=3} || paired.size!=15
        val exact=paired.count{it.candidateEdits==0};val edits=paired.sumOf{it.candidateEdits}
        val baseline=paired.sumOf{it.baselineEdits};val phones=paired.sumOf{it.referencePhones}
        val eachWord=words.size==5 && words.values.all{group->group.any{it.candidateOperational && it.candidateEdits==0}}
        val passed=!incomplete && exact>=10 && phones>0 && edits.toDouble()/phones<=.20 && edits<baseline && eachWord
        return AdultPromptResult(passed,incomplete,paired.size,exact,edits,baseline,phones,eachWord)
    }
}
