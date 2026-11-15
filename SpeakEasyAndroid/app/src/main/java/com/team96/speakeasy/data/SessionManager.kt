package com.team96.speakeasy.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.longPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.team96.speakeasy.journey.CarePlan
import com.team96.speakeasy.journey.LocalSessionReport
import com.team96.speakeasy.journey.normalizeCarePlan
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.runBlocking

private val Context.dataStore by preferencesDataStore(name = "speakeasy_session")

/**
 * Holds the JWT in memory (for the OkHttp interceptor) and persists only its
 * Keystore-encrypted representation to DataStore.
 */
object SessionManager {
    private const val OFFLINE_DEMO_TOKEN = "local-review-demo"
    @Volatile var token: String? = null
        private set
    @Volatile var childName: String? = null
    @Volatile var fullName: String? = null
    @Volatile var email: String? = null
    @Volatile var carePlan: CarePlan = CarePlan()
        private set
    private data class StoredReport(val owner:String?,val report:LocalSessionReport?)
    @Volatile private var reportRecord=StoredReport(null,null)
    val lastReport:LocalSessionReport? get(){val record=reportRecord;return com.team96.speakeasy.journey.reportForProfile(record.report,record.owner,reportScope())}
    private fun reportScope()=com.team96.speakeasy.journey.verifiedLetterScope(email,carePlan.childAlias,isOfflineReview)
    @Volatile var carePlanConfigured: Boolean = false
        private set

    private val TOKEN_KEY = stringPreferencesKey("token")
    private val CHILD_KEY = stringPreferencesKey("child")
    private val NAME_KEY = stringPreferencesKey("name")
    private val EMAIL_KEY = stringPreferencesKey("email")
    private val AGE_KEY = intPreferencesKey("care_age")
    private val SESSION_MINUTES_KEY = intPreferencesKey("care_session_minutes")
    private val FOCUS_MINUTES_KEY = intPreferencesKey("care_focus_minutes")
    private val INTEREST_KEY = stringPreferencesKey("care_interest")
    private val CARE_CONFIGURED_KEY = booleanPreferencesKey("care_configured")
    private val REPORT_ID_KEY = stringPreferencesKey("report_id")
    private val REPORT_START_KEY = longPreferencesKey("report_started")
    private val REPORT_END_KEY = longPreferencesKey("report_ended")
    private val REPORT_ATTEMPTS_KEY = intPreferencesKey("report_attempts")
    private val REPORT_WORDS_KEY = intPreferencesKey("report_words")
    private val REPORT_BREAKS_KEY = intPreferencesKey("report_breaks")
    private val REPORT_SCOPE_KEY=stringPreferencesKey("report_scope")
    private val REPORT_PICTURE_CHOICES_KEY=intPreferencesKey("report_picture_choices")
    private val REPORT_PICTURE_MATCHES_KEY=intPreferencesKey("report_picture_matches")
    private val REPORT_PICTURE_HINT_FREE_KEY=intPreferencesKey("report_picture_hint_free")
    private val REPORT_PICTURE_HELP_KEY=intPreferencesKey("report_picture_help")
    private val REPORT_CONTEXT_KEY=intPreferencesKey("report_context_turns")

    private lateinit var appContext: Context

    fun init(context: Context) {
        appContext = context.applicationContext
        runBlocking {
            val prefs = appContext.dataStore.data.first()
            token = prefs[TOKEN_KEY]?.let { encrypted -> runCatching { TokenCipher.decrypt(encrypted) }.getOrNull() }
            childName = prefs[CHILD_KEY]
            fullName = prefs[NAME_KEY]
            email = prefs[EMAIL_KEY]
            carePlan = normalizeCarePlan(CarePlan(
                childAlias = prefs[CHILD_KEY] ?: "Friend",
                age = prefs[AGE_KEY] ?: 7,
                sessionMinutes = prefs[SESSION_MINUTES_KEY] ?: 10,
                focusMinutes = prefs[FOCUS_MINUTES_KEY] ?: 4,
                interest = prefs[INTEREST_KEY] ?: "stories",
            ))
            carePlanConfigured = prefs[CARE_CONFIGURED_KEY] ?: false
            val reportId = prefs[REPORT_ID_KEY]
            val reportOwner=prefs[REPORT_SCOPE_KEY]
            val loadedReport = if (reportId == null) null else LocalSessionReport(
                sessionId = reportId,
                startedAtEpochMillis = prefs[REPORT_START_KEY] ?: 0L,
                endedAtEpochMillis = prefs[REPORT_END_KEY] ?: 0L,
                durationSeconds = ((prefs[REPORT_END_KEY] ?: 0L) - (prefs[REPORT_START_KEY] ?: 0L)).coerceAtLeast(0L) / 1_000L,
                attemptCount = prefs[REPORT_ATTEMPTS_KEY] ?: 0,
                uniqueWordCount = prefs[REPORT_WORDS_KEY] ?: 0,
                breakCount = prefs[REPORT_BREAKS_KEY] ?: 0,
                unscorableCount = prefs[REPORT_ATTEMPTS_KEY] ?: 0,
                activityChoices=(prefs[REPORT_PICTURE_CHOICES_KEY]?:0).coerceIn(0,10000),
                activityMatches=(prefs[REPORT_PICTURE_MATCHES_KEY]?:0).coerceIn(0,(prefs[REPORT_PICTURE_CHOICES_KEY]?:0).coerceIn(0,10000)),
                activityWithoutExtraHint=(prefs[REPORT_PICTURE_HINT_FREE_KEY]?:0).coerceIn(0,(prefs[REPORT_PICTURE_MATCHES_KEY]?:0).coerceIn(0,10000)),
                activityHelpRequests=(prefs[REPORT_PICTURE_HELP_KEY]?:0).coerceIn(0,10000),
                activityContextTurns=(prefs[REPORT_CONTEXT_KEY]?:0).coerceIn(0,10000),
            )
            reportRecord=StoredReport(reportOwner,loadedReport)
        }
    }

    /** DEC-013: debug review path stays local and is visibly distinct from authenticated use. */
    suspend fun startOfflineReview() {
        save(
            OFFLINE_DEMO_TOKEN,
            User(email = "Offline review", fullName = "Caregiver", childName = carePlan.childAlias, childAge = carePlan.age, language = "Tamil"),
        )
    }

    suspend fun saveCarePlan(value: CarePlan) {
        val plan = normalizeCarePlan(value)
        appContext.dataStore.edit { prefs ->
            prefs[CHILD_KEY] = plan.childAlias
            prefs[AGE_KEY] = plan.age
            prefs[SESSION_MINUTES_KEY] = plan.sessionMinutes
            prefs[FOCUS_MINUTES_KEY] = plan.focusMinutes
            prefs[INTEREST_KEY] = plan.interest
            prefs[CARE_CONFIGURED_KEY] = true
        }
        carePlan = plan
        childName = plan.childAlias
        carePlanConfigured = true
    }

    /** DEC-014/021: stores only bounded counters and timestamps, never capture contents. */
    suspend fun saveReport(report: LocalSessionReport,origin:String?=reportScope()) {
        val owner=requireNotNull(origin){"Report identity unavailable"}
        require(owner==reportScope()){"Report identity changed"}
        appContext.dataStore.edit { prefs ->
            require(owner==reportScope()){"Report identity changed"}
            prefs[REPORT_SCOPE_KEY]=owner
            prefs[REPORT_ID_KEY] = report.sessionId
            prefs[REPORT_START_KEY] = report.startedAtEpochMillis
            prefs[REPORT_END_KEY] = report.endedAtEpochMillis
            prefs[REPORT_ATTEMPTS_KEY] = report.attemptCount
            prefs[REPORT_WORDS_KEY] = report.uniqueWordCount
            prefs[REPORT_BREAKS_KEY] = report.breakCount
            prefs[REPORT_PICTURE_CHOICES_KEY]=report.activityChoices.coerceIn(0,10000)
            prefs[REPORT_PICTURE_MATCHES_KEY]=report.activityMatches.coerceIn(0,report.activityChoices.coerceIn(0,10000))
            prefs[REPORT_PICTURE_HINT_FREE_KEY]=report.activityWithoutExtraHint.coerceIn(0,report.activityMatches.coerceIn(0,10000))
            prefs[REPORT_PICTURE_HELP_KEY]=report.activityHelpRequests.coerceIn(0,10000)
            prefs[REPORT_CONTEXT_KEY]=report.activityContextTurns.coerceIn(0,10000)
        }
        if(owner==reportScope())reportRecord=StoredReport(owner,report)
    }

    suspend fun save(token: String, user: User?) {
        this.token = token
        this.childName = user?.childName
        this.fullName = user?.fullName
        this.email = user?.email
        appContext.dataStore.edit { prefs ->
            prefs[TOKEN_KEY] = TokenCipher.encrypt(token)
            user?.childName?.let { prefs[CHILD_KEY] = it }
            user?.fullName?.let { prefs[NAME_KEY] = it }
            // DEC053 review R6: an unidentified new account cannot inherit the prior email after restart.
            if(user?.email.isNullOrBlank())prefs.remove(EMAIL_KEY) else prefs[EMAIL_KEY]=user!!.email!!
        }
    }

    suspend fun clear() {
        token = null
        childName = null
        fullName = null
        email = null
        carePlan = CarePlan()
        reportRecord=StoredReport(null,null)
        carePlanConfigured = false
        appContext.dataStore.edit { it.clear() }
    }

    val isLoggedIn: Boolean get() = !token.isNullOrBlank()
    val isOfflineReview: Boolean get() = token == OFFLINE_DEMO_TOKEN
}
