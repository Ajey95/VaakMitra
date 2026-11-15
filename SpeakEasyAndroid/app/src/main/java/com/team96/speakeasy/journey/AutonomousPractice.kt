package com.team96.speakeasy.journey

/** DEC070/PHN011: session-only practice signals; agreement is not child correctness. */
data class WordCycleSignal(val usable:Boolean,val sequenceAgreement:Boolean,val requestedHelp:Boolean=false)
data class AutonomousPracticeState(
    val words:List<Int>,val focused:Boolean,val focusMinutes:Int,val tier:Int,
    val position:Int=0,val cyclesOnSet:Int=0,val settledCycles:Int=0,val completedCycles:Int=0,
    val signals:List<WordCycleSignal> = emptyList(),val setChanges:Int=0,
) {
    val currentLessonId:Int? get()=words.getOrNull(position)
}
data class CycleAdvance(val state:AutonomousPracticeState,val nextLessonId:Int?,val cycleFinished:Boolean,val reason:String)

object AutonomousPracticePolicy {
    private fun allowed(focused:Boolean):List<Int> = if(focused)StarterWords.focusedLessonIds
        else (StarterWords.focusedLessonIds+(1..StarterWords.all.size)).distinct()
    private fun chooseSet(tier:Int,focused:Boolean,rotation:Int,seed:Int?,focus:String?,references:Map<String,List<String>>):List<Int> {
        val pool=allowed(focused).filter{StarterWords.byNumericLessonId(it)!!.difficulty<=tier}
            .sortedWith(compareBy<Int>{if(StarterWords.byNumericLessonId(it)!!.difficulty==tier)0 else 1}
                .thenBy{if(focus!=null && focus in references[StarterWords.byNumericLessonId(it)!!.id].orEmpty())0 else 1})
        if(pool.isEmpty())return emptyList()
        fun rotate(values:List<Int>):List<Int> {
            if(values.isEmpty())return values
            val offset=Math.floorMod(rotation,values.size)
            return values.drop(offset)+values.take(offset)
        }
        val sameSound=if(focus==null)emptyList()else pool.filter{focus in references[StarterWords.byNumericLessonId(it)!!.id].orEmpty()}
        // Keep support membership while changing context; whole-pool rotation could lose the sound.
        val rotated=if(sameSound.isEmpty())rotate(pool)else rotate(sameSound)+rotate(pool.filter{it !in sameSound})
        return (listOfNotNull(seed?.takeIf{it in pool})+rotated).distinct().take(3)
    }
    fun start(current:Int,focused:Boolean,focusMinutes:Int):AutonomousPracticeState? {
        if(current !in allowed(focused))return null
        val word=StarterWords.byNumericLessonId(current)?:return null
        val minutes=focusMinutes.coerceIn(2,8)
        return AutonomousPracticeState(chooseSet(word.difficulty,focused,0,current,null,emptyMap()),focused,minutes,word.difficulty)
    }
    private fun independentTaskProgress(pictures:Map<String,PictureProgress>):Boolean =
        pictures.values.filter{it.valid()}.let{rows->rows.sumOf{it.noExtraHintMatches}>=2 || rows.count{it.matches>=2 && it.recentErrors==0}>=2}
    fun guidanceSteps(state:AutonomousPracticeState,needsSupport:Boolean,pictures:Map<String,PictureProgress>):List<Int> = when {
        needsSupport || !independentTaskProgress(pictures) -> listOf(0,1,2)
        state.settledCycles>=2 -> listOf(2)
        state.settledCycles>=1 -> listOf(1,2)
        else -> listOf(0,1,2)
    }
    fun advance(state:AutonomousPracticeState,signal:WordCycleSignal,pictures:Map<String,PictureProgress>,
        focus:String?,references:Map<String,List<String>>):CycleAdvance {
        if(state.currentLessonId==null)return CycleAdvance(state,null,false,"unavailable")
        val signals=(state.signals+signal).takeLast(3)
        if(state.position+1<state.words.size){
            val next=state.copy(position=state.position+1,signals=signals)
            return CycleAdvance(next,next.currentLessonId,false,"next_word")
        }
        val cycles=state.cyclesOnSet+1
        val settled=if(focus==null && signals.all{it.usable&&it.sequenceAgreement&&!it.requestedHelp})state.settledCycles+1 else 0
        val total=state.completedCycles+1
        val consistencyWindow=if(state.focusMinutes<=2)2 else 3
        val sameSetBudget=(state.focusMinutes+1).coerceIn(3,6)
        val canOfferChallenge=settled>=consistencyWindow && independentTaskProgress(pictures) && state.tier<3
        if(!canOfferChallenge && cycles<sameSetBudget){
            val next=state.copy(position=0,cyclesOnSet=cycles,settledCycles=settled,completedCycles=total,signals=emptyList())
            return CycleAdvance(next,next.currentLessonId,true,"repeat_set")
        }
        val needsSupport=focus!=null || signals.any{!it.usable || !it.sequenceAgreement || it.requestedHelp}
        val tier=when{canOfferChallenge->state.tier+1;needsSupport->(state.tier-1).coerceAtLeast(1);else->state.tier}
        val rotation=if(tier<state.tier)0 else (state.setChanges+1)*3
        var words=chooseSet(tier,state.focused,rotation,null,focus,references)
        if(words==state.words)words=chooseSet(tier,state.focused,rotation+1,null,focus,references)
        val next=state.copy(words=words,position=0,tier=tier,cyclesOnSet=0,settledCycles=0,
            completedCycles=total,signals=emptyList(),setChanges=state.setChanges+1)
        return CycleAdvance(next,next.currentLessonId,true,when{canOfferChallenge->"bounded_challenge";needsSupport->"different_support_set";else->"similar_set"})
    }
}
