package com.team96.speakeasy.journey

/** DEC060 / ILR011: save bounded counters and known IDs, never voice contents. */
data class SessionTally(
    val attempts:Int=0,val words:Set<String> = emptySet(),val breaks:Int=0,
    val choices:Int=0,val matches:Int=0,val hintFree:Int=0,val helps:Int=0,val contextTurns:Int=0,
) {
    fun record(event:SessionEvent):SessionTally=when(event){
        is SessionEvent.Attempt->copy(attempts=(attempts+1).coerceAtMost(10000),words=(words+event.wordId).intersect(StarterWords.all.map{it.id}.toSet()))
        SessionEvent.Break->copy(breaks=(breaks+1).coerceAtMost(10000))
        is SessionEvent.PictureHelp->copy(helps=(helps+1).coerceAtMost(10000))
        is SessionEvent.ContextTurn->if(StarterWords.all.any{it.id==event.wordId} && !WordActivityCatalog.isMatch(event.wordId))copy(contextTurns=(contextTurns+1).coerceAtMost(10000))else this
        is SessionEvent.PictureChoice->if(choices>=10000 || !WordActivityCatalog.isMatch(event.wordId))this else copy(choices=choices+1,matches=matches+if(event.matched)1 else 0,hintFree=hintFree+if(event.matched&&event.withoutExtraHint)1 else 0)
    }
    fun report(id:String,start:Long,end:Long)=LocalSessionReport(id,start,end,(end-start).coerceAtLeast(0)/1000,attempts,words.size,breaks,attempts,activityChoices=choices,activityMatches=matches,activityWithoutExtraHint=hintFree,activityHelpRequests=helps,activityContextTurns=contextTurns)
    fun encode()=listOf(attempts,breaks,choices,matches,hintFree,helps,contextTurns).joinToString(",")+";"+words.sorted().joinToString(",")
    companion object{
        fun decode(value:String):SessionTally=runCatching{
            require(value.length<2048);val p=value.split(';');require(p.size==2)
            val n=p[0].split(',').map{it.toInt()};require(n.size in 6..7 && n.all{it in 0..10000} && n[4]<=n[3] && n[3]<=n[2])
            val ids=p[1].split(',').filter{it.isNotEmpty()}.toSet();require(ids.size<=25 && ids.all{id->StarterWords.all.any{it.id==id}})
            SessionTally(n[0],ids,n[1],n[2],n[3],n[4],n[5],n.getOrElse(6){0})
        }.getOrDefault(SessionTally())
    }
}

/** Loading is not ephemeral. Every completion and action retains its initiating owner. */
class ScopedPictureBinding(private val currentOwner:()->String?) {
    private var owner:String?=null
    private var ready=false
    private var records:Map<String,PictureProgress> = emptyMap()
    @Synchronized fun begin(expected:String?,persistent:Boolean){owner=expected;ready=!persistent;records=emptyMap()}
    @Synchronized fun loaded(expected:String?,initial:Map<String,PictureProgress>):Boolean{
        if(owner!=expected || currentOwner()!=expected)return false
        records=WordProgressCodec.decode(WordProgressCodec.encode(initial));ready=true;return true
    }
    @Synchronized fun isReady(expected:String?)=ready && owner==expected && currentOwner()==expected
    @Synchronized fun load():Map<String,PictureProgress> = if(currentOwner()==owner)records.toMap() else emptyMap()
    @Synchronized fun update(expected:String?,id:String,next:PictureProgress,persist:(PictureProgress)->Boolean):Boolean{
        if(!isReady(expected) || !next.validFor(id))return false
        if(!persist(next) || !isReady(expected))return false
        records=records+(id to next);return true
    }
}

data class SessionReportHandoff(val owner:String?,val report:LocalSessionReport,val saved:Boolean,val saveFailed:Boolean=false){
    fun visible(current:String?)=takeIf{owner!=null && owner==current}
    val status:String get()=if(saved)"Saved on this device" else if(saveFailed)"Save failed · this session is shown here only" else "Session only · not saved on this device"
}
fun reportWriteAllowed(origin:String?,current:String?,verified:Boolean)=verified && origin!=null && origin==current
