package com.team96.speakeasy.viewmodel

import android.content.Context
import com.team96.speakeasy.journey.LetterJourneySnapshot
import com.team96.speakeasy.journey.LetterJourneyStore
import com.team96.speakeasy.journey.LetterPracticeSettings
import com.team96.speakeasy.journey.verifiedLetterScope
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.team96.speakeasy.data.Api
import com.team96.speakeasy.data.Lesson
import com.team96.speakeasy.data.SessionManager
import com.team96.speakeasy.journey.StarterWords
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch

data class HomeStats(
    val stars: Int? = null,
    val sessions: Int = 0,
    val childName: String = "Friend",
    val completedLessons: Int = 0,
)

class AppViewModel(private val preview:Boolean=false,private val reportWriter:(suspend (com.team96.speakeasy.journey.LocalSessionReport)->Unit)?=null,private val previewStars:Int?=0,private val previewInterest:String="stories",private val identityProvider:(()->String?)?=null,private val verifiedIdentityProvider:(()->String?)?=null) : ViewModel() {
    val isPublicPreview:Boolean get()=preview
    /** PRS003: name is read for local speech only; only the verified opaque scope is persisted. */
    val praiseName:String get()=if(preview)"Sample learner" else SessionManager.childName?.takeIf{it.isNotBlank()}?:practiceCarePlan.childAlias
    val praiseScope:String? get()=if(preview)null else currentLetterScope()
    private val praiseMailbox=com.team96.speakeasy.journey.PraiseMailbox()
    private var summaryPraise:String?=null
    private val praisePreferences=com.team96.speakeasy.journey.PraisePreferenceCache()
    fun issuePraise(origin:String?):String?=praiseMailbox.issueFor(origin,wordIdentity())
    fun claimPraise(ticket:String):Boolean=praiseMailbox.claim(wordIdentity(),ticket)
    fun isPraiseCurrent(ticket:String):Boolean=praiseMailbox.isCurrent(wordIdentity(),ticket)
    fun cancelPraise(ticket:String?){praiseMailbox.cancel(ticket)}
    fun invalidatePraiseForBackground(){praiseMailbox.clear()}
    fun loadPraiseSettings(context:Context)=praisePreferences.load(wordIdentity()){
        if(preview)com.team96.speakeasy.journey.PraiseSettings()else com.team96.speakeasy.journey.EncouragementStore(context,praiseScope){praiseScope}.load()
    }
    fun savePraiseSettings(context:Context,origin:String?,value:com.team96.speakeasy.journey.PraiseSettings):Boolean=
        praisePreferences.save(origin,wordIdentity(),value,{if(preview)com.team96.speakeasy.journey.PraiseSettings()else com.team96.speakeasy.journey.EncouragementStore(context,praiseScope){praiseScope}.load()}){
            if(preview||praiseScope==null)true else com.team96.speakeasy.journey.EncouragementStore(context,praiseScope){praiseScope}.save(it)
        }
    fun summaryPraiseTicket(reportId:String):String?=summaryPraise.takeIf{currentSessionSummary?.report?.sessionId==reportId}
    val guideScope:String? get()=if(preview)"public-gallery" else SessionManager.childName
    val practiceCarePlan:com.team96.speakeasy.journey.CarePlan get()=if(preview)com.team96.speakeasy.journey.CarePlan(childAlias="Sample learner",interest=previewInterest) else SessionManager.carePlan
    fun guidePreference(context:Context):com.team96.speakeasy.avatar.AvatarPreference = if(preview)com.team96.speakeasy.avatar.AvatarPreference() else com.team96.speakeasy.avatar.AvatarPreferenceStore.load(context,guideScope)
    /** DEC057 review R1: even navigation-only previews cannot replace the learner's last report. */
    private var summary:com.team96.speakeasy.journey.SessionReportHandoff?=null
    val currentSessionSummary get()=summary?.visible(wordIdentity())
    suspend fun savePracticeReport(report:com.team96.speakeasy.journey.LocalSessionReport,origin:String?=wordIdentity(),praiseTicket:String?=null):Boolean {
        if(origin!=wordIdentity())return false
        val allowed=!preview && com.team96.speakeasy.journey.reportWriteAllowed(origin,wordIdentity(),currentLetterScope()==origin)
        val saved=allowed && runCatching{if(reportWriter!=null)reportWriter.invoke(report)else SessionManager.saveReport(report,origin);true}.getOrDefault(false)
        if(origin==wordIdentity()){
            summary=com.team96.speakeasy.journey.SessionReportHandoff(origin,report,saved,allowed&&!saved)
            summaryPraise=praiseTicket?.takeIf{com.team96.speakeasy.journey.hasPraiseParticipation(report)&&isPraiseCurrent(it)}
        }
        return saved && origin==wordIdentity()
    }

    @Volatile private var wordStore:com.team96.speakeasy.journey.WordLearningStore?=null
    @Volatile private var wordScope:String?=null
    @Volatile private var wordEpisode:String?=null
    private val _wordProgress=MutableStateFlow<Map<String,com.team96.speakeasy.journey.PictureProgress>>(emptyMap())
    val wordProgress:StateFlow<Map<String,com.team96.speakeasy.journey.PictureProgress>> =_wordProgress
    private val wordBinding=com.team96.speakeasy.journey.ScopedPictureBinding{wordIdentity()}
    private val wordLock=Any()
    private val _wordReady=MutableStateFlow(preview)
    val wordReady:StateFlow<Boolean> =_wordReady
    fun wordReadyForCurrent()=wordBinding.isReady(wordIdentity())
    init{if(preview)wordBinding.begin("public-gallery",false)}
    fun wordIdentity():String?=identityProvider?.invoke() ?: if(preview)"public-gallery" else currentLetterScope() ?: "session-only:"+com.team96.speakeasy.journey.letterProfileScope("unverified-session",SessionManager.carePlan.childAlias)
    val wordHistoryPersistent:Boolean get()=!preview && wordScope!=null && wordScope==currentLetterScope() && wordStore!=null
    val canShowWordHistory:Boolean get()=preview || if(wordStore!=null)wordHistoryPersistent else wordEpisode==wordIdentity()
    fun loadWordLearning(context:Context):Unit=synchronized(wordLock){
        if(preview)return
        val scope=currentLetterScope()
        if(wordScope==scope && wordStore!=null)return
        val origin=wordIdentity()
        wordStore=null;wordScope=null;_wordProgress.value=emptyMap();wordEpisode=origin;_wordReady.value=false
        wordBinding.begin(origin,scope!=null)
        if(scope==null){_wordReady.value=true;return}
        val store=com.team96.speakeasy.journey.WordLearningStore(context,scope){
            verifiedLetterScope(SessionManager.email,SessionManager.carePlan.childAlias,SessionManager.isOfflineReview)==scope
        }
        runCatching{store.load()}.onSuccess{if(currentLetterScope()==scope && wordBinding.loaded(origin,it)){wordStore=store;wordScope=scope;_wordProgress.value=it;_wordReady.value=true}}
    }
    /** ILR007: previews/unidentified sessions stay in memory; a stale bound profile cannot write. */
    fun choosePicture(id:String,selected:String,options:List<String>,day:Long,origin:String?=wordIdentity()):Boolean=runCatching{
        val current=_wordProgress.value[id]?:com.team96.speakeasy.journey.PictureProgress()
        val response=com.team96.speakeasy.journey.pictureSelection(id,selected,options,current,day)
        recordWordProgress(origin,id,response.progress)
    }.getOrDefault(false)
    fun requestPictureHelp(id:String,day:Long,origin:String?=wordIdentity()):Boolean =
        recordWordProgress(origin,id,(_wordProgress.value[id]?:com.team96.speakeasy.journey.PictureProgress()).requestedHelp(day))
    fun recordWordProgress(origin:String?,id:String,next:com.team96.speakeasy.journey.PictureProgress):Boolean=synchronized(wordLock){
        if(origin!=wordIdentity() || !wordBinding.isReady(origin))return false
        val ok=runCatching{wordBinding.update(origin,id,next){p->if(preview || currentLetterScope()==null)true else wordHistoryPersistent && checkNotNull(wordStore).put(id,p)}}.getOrDefault(false)
        if(ok)_wordProgress.value=wordBinding.load()
        ok
    }

    private var letterStore: LetterJourneyStore? = null
    private val _letterJourney = MutableStateFlow(LetterJourneySnapshot())
    val letterJourney: StateFlow<LetterJourneySnapshot> = _letterJourney
    private val _letterReady = MutableStateFlow(false)
    val letterReady: StateFlow<Boolean> = _letterReady
    private val _letterScope=MutableStateFlow<String?>(null)
    val letterScope:StateFlow<String?> = _letterScope
    private fun currentLetterScope()=if(verifiedIdentityProvider!=null)verifiedIdentityProvider.invoke()else verifiedLetterScope(SessionManager.email,SessionManager.carePlan.childAlias,SessionManager.isOfflineReview)
    fun letterIdentityIsCurrent():Boolean = if(preview)_letterReady.value else _letterReady.value && _letterScope.value!=null && _letterScope.value==currentLetterScope()
    private fun clearLetterBinding(){
        _letterReady.value=false;_letterScope.value=null;letterStore=null;_letterJourney.value=LetterJourneySnapshot()
    }
    fun loadLetterJourney(context: Context) {
        if(preview){_letterJourney.value=LetterJourneySnapshot();_letterScope.value="public-gallery";_letterReady.value=true;return}
        val scope=currentLetterScope() ?: run{clearLetterBinding();return}
        if(letterStore?.scope!=scope){_letterReady.value=false;letterStore=LetterJourneyStore(context,scope)}
        runCatching{checkNotNull(letterStore).load()}.onSuccess{
            _letterJourney.value=it;_letterScope.value=scope;_letterReady.value=true
        }.onFailure{clearLetterBinding()}
    }
    fun completeLetter(id:String):Boolean {
        if(preview)return false
        val store=letterStore ?: return false
        if(store.scope!=currentLetterScope()){clearLetterBinding();return false}
        return runCatching{
            val before=_letterJourney.value.progress.completedCount
            _letterJourney.value=store.complete(id)
            _letterJourney.value.progress.completedCount>before
        }.getOrDefault(false)
    }
    fun saveLetterSettings(settings:LetterPracticeSettings):Boolean {
        if(preview)return false
        val store=letterStore ?: return false
        if(store.scope!=currentLetterScope()){clearLetterBinding();return false}
        return runCatching{_letterJourney.value=store.saveSettings(settings);true}.getOrDefault(false)
    }

    private val localLessons = StarterWords.all.mapIndexed { index, word ->
        Lesson(
            id = index + 1, type = "word", symbol = word.tamil, english = word.transliteration,
            phoneme = word.meaning, tip = "${word.transliteration} means ${word.meaning.lowercase()}.", difficulty = word.difficulty,
        )
    }
    // DEC-052: the installed word model uses these stable local numeric routes.
    val localWordLessons: List<Lesson> get() = localLessons

    private val _lessons = MutableStateFlow(localLessons)
    val lessons: StateFlow<List<Lesson>> = _lessons

    private val _loading = MutableStateFlow(false)
    val loading: StateFlow<Boolean> = _loading

    private val _stats = MutableStateFlow(HomeStats())
    val stats: StateFlow<HomeStats> = _stats

    fun loadHome() {
        if(preview){_stats.value=HomeStats(stars=previewStars,childName="Sample learner");_lessons.value=localLessons;return}
        viewModelScope.launch {
            _loading.value = true
            val localReport = SessionManager.lastReport
            _stats.value = HomeStats(
                stars = null,
                sessions = if (localReport == null) 0 else 1,
                childName = SessionManager.carePlan.childAlias,
                completedLessons = localReport?.uniqueWordCount ?: 0,
            )
            if (SessionManager.isOfflineReview) {
                _lessons.value = localLessons
                _loading.value = false
                return@launch
            }
            try {
                val me = Api.service.me()
                _stats.value = _stats.value.copy(
                    stars = com.team96.speakeasy.journey.confirmedAccountStars(me.totalStars),
                    sessions = me.totalSessions ?: 0,
                    childName = me.childName?.takeIf { it.isNotBlank() } ?: "Friend",
                    completedLessons = 0,
                )
            } catch (_: Exception) {
            }
            try {
                val remote = Api.service.lessons()
                acceptRemoteLessons(remote)
            } catch (_: Exception) {
                _lessons.value = localLessons
            }
            _loading.value = false
        }
    }

    /** Remote catalogue state remains available, but cannot redefine installed practice IDs. */
    internal fun acceptRemoteLessons(remote: List<Lesson>) {
        if(remote.isNotEmpty())_lessons.value=remote
    }

    fun lessonById(id: Int): Lesson? = localLessons.firstOrNull { it.id == id }
}
