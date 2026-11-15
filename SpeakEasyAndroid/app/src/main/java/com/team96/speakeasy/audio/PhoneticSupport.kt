package com.team96.speakeasy.audio

/** DEC068/PHN009: no raw phones, diagnosis or child correctness is retained. */
data class PhoneticSupportChoice(
    val action:String,val candidatePatterns:List<String> = emptyList(),
    val decision:String="UNSCORABLE",val basis:String="generic_help",
)

object PhoneticSupportPolicy {
    /** Known vocabulary does not provide calibrated acoustic confidence for child speech. */
    fun fromPreview(heard:List<String>,reference:List<String>,knownTokens:Set<String>)=
        choose(heard,reference,knownTokens,evidenceValid=false,modelQualified=true)
    private data class Cell(val cost:Int,val signatures:Set<Set<String>>)
    private fun extend(cell:Cell,extra:String?)=Cell(cell.cost+if(extra==null)0 else 1,
        cell.signatures.map{if(extra==null)it else it+extra}.toSet())
    private fun patterns(heard:List<String>,reference:List<String>):List<String> {
        var previous=List(reference.size+1){j->Cell(j,setOf(if(j==0)emptySet() else setOf("possible_omission")))}
        for((index,phone)in heard.withIndex()) {
            val i=index+1
            val repeated=(index>0 && heard[index-1]==phone)||(i<heard.size && heard[i]==phone)
            val inserted=if(repeated) "possible_repetition" else "unsupported_insertion"
            val row=mutableListOf(Cell(i,previous[0].signatures.map{it+inserted}.toSet()))
            for((targetIndex,target)in reference.withIndex()) {
                val j=targetIndex+1
                val options=listOf(extend(previous[j],inserted),extend(row[j-1],"possible_omission"),
                    extend(previous[j-1],if(phone==target) null else "possible_substitution"))
                val best=options.minOf{it.cost}
                row.add(Cell(best,options.filter{it.cost==best}.flatMap{it.signatures}.toSet()))
            }
            previous=row
        }
        val signatures=previous.last().signatures
        if(signatures.size!=1)return emptyList()
        val signature=signatures.single()
        return if("unsupported_insertion" in signature) emptyList() else signature.sorted()
    }
    fun choose(heard:List<String>,reference:List<String>,knownTokens:Set<String>,
        evidenceValid:Boolean=false,modelQualified:Boolean=false,
        allowedActions:Set<String> = setOf("adult_example","picture","repeat","break"),
        stopRequested:Boolean=false,breakRequested:Boolean=false,attemptCount:Int=0,maxRetries:Int=2,
    ):PhoneticSupportChoice {
        if(stopRequested)return PhoneticSupportChoice("safe_end",basis="stop_requested")
        val allowed=allowedActions.intersect(setOf("adult_example","picture","repeat","break","safe_end"))
        if(breakRequested || attemptCount>=maxRetries)return PhoneticSupportChoice(if("break" in allowed) "break" else "safe_end",basis="session_limit")
        val action=listOf("adult_example","picture","repeat").firstOrNull{it in allowed}?:"none"
        fun valid(phones:List<String>)=phones.size in 1..64 && phones.all{it in knownTokens && it !in setOf("<blank>","[PAD]","[UNK]","|","்")}
        if(!evidenceValid || !modelQualified || !valid(heard) || !valid(reference))return PhoneticSupportChoice(action)
        if(heard==reference)return PhoneticSupportChoice("none",basis="sequence_agreement_only")
        val found=patterns(heard,reference)
        return PhoneticSupportChoice(action,found,basis=if(found.isEmpty()) "generic_help" else "unvalidated_sequence_hypothesis")
    }
}
