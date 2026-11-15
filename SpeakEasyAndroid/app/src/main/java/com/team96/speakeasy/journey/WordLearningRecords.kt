package com.team96.speakeasy.journey

/** ILR007: bounded IDs/counters/day only; no audio, phones, free text or child identity. */
object WordProgressCodec {
    private val known get()=StarterWords.all.map{it.id}.toSet()
    fun encode(records:Map<String,PictureProgress>):String=buildString {
        append("word-learning-2")
        for((id,p)in records.toSortedMap())if(id in known && p.validFor(id)){
            append('\n');append(id);append('|')
            append(listOf(p.choices.toLong(),p.matches.toLong(),p.noExtraHintMatches.toLong(),p.helps.toLong(),p.recentMatches.toLong(),p.recentErrors.toLong(),p.help.ordinal.toLong(),p.lastDay).joinToString("|"))
        }
    }
    fun decode(value:String):Map<String,PictureProgress> {
        if(value.length>16384)return emptyMap()
        val lines=value.lines();if(lines.firstOrNull()!="word-learning-2" || lines.size>26)return emptyMap()
        val result=mutableMapOf<String,PictureProgress>()
        for(line in lines.drop(1)){
            val fields=line.split('|');if(fields.size!=9 || fields[0] !in known || fields[0] in result)continue
            val n=fields.drop(1).map{it.toLongOrNull()};if(n.any{it==null})continue
            val values=n.map{it!!};if(values.take(6).any{it !in 0..10000L} || values[6] !in 0L..2L)continue
            val p=PictureProgress(values[0].toInt(),values[1].toInt(),values[2].toInt(),values[3].toInt(),values[4].toInt(),values[5].toInt(),PromptHelp.entries[values[6].toInt()],values[7])
            if(p.validFor(fields[0]))result[fields[0]]=p
        }
        return result.toMap()
    }
}

/** Last confirmed state remains authoritative after a failed SharedPreferences commit. */
class ConfirmedWordLearningWrites(
    initial:Map<String,PictureProgress>,private val persist:(Map<String,PictureProgress>)->Boolean,
    private val stillOwner:()->Boolean,
) {
    private var state=WordProgressCodec.decode(WordProgressCodec.encode(initial))
    fun load():Map<String,PictureProgress> = if(stillOwner())state.toMap()else emptyMap()
    private fun update(id:String,next:()->PictureProgress):Boolean {
        if(!stillOwner() || StarterWords.all.none{it.id==id})return false
        val candidate=state+(id to next())
        if(!persist(candidate) || !stillOwner())return false
        state=candidate;return true
    }
    fun choose(id:String,selected:String,options:List<String>,day:Long):Boolean =
        update(id){pictureSelection(id,selected,options,state[id]?:PictureProgress(),day).progress}
    fun help(id:String,day:Long):Boolean =update(id){(state[id]?:PictureProgress()).requestedHelp(day)}
    fun put(id:String,progress:PictureProgress):Boolean {
        if(!progress.validFor(id))return false
        return update(id){progress}
    }
}
