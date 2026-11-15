package com.team96.speakeasy.journey

/** DEC-013: small, versioned, on-device starter path for the review APK. */
data class StarterWord(
    val id: String,
    val tamil: String,
    val transliteration: String,
    val meaning: String,
    val category: String,
    val difficulty: Int,
)

object StarterWords {
    val all = listOf(
        StarterWord("TA_WORD_0001", "அம்மா", "Amma", "Mother", "Family", 1),
        StarterWord("TA_WORD_0002", "அப்பா", "Appa", "Father", "Family", 1),
        StarterWord("TA_WORD_0012", "உணவு", "Unavu", "Food", "Needs", 2),
        StarterWord("TA_WORD_0013", "வேண்டும்", "Vendum", "Want / need", "Needs", 3),
        StarterWord("TA_WORD_0014", "வேண்டாம்", "Vendaam", "Do not want", "Needs", 3),
        StarterWord("TA_WORD_0015", "இன்னும்", "Innum", "More", "Needs", 2),
        StarterWord("TA_WORD_0016", "போதும்", "Podhum", "Enough", "Needs", 2),
        StarterWord("TA_WORD_0017", "உதவி", "Udhavi", "Help", "Needs", 2),
        StarterWord("TA_WORD_0049", "சொல்", "Sol", "Say / tell", "Actions", 1),
        StarterWord("TA_WORD_0050", "படி", "Padi", "Read", "Actions", 1),
        StarterWord("TA_WORD_0072", "படம்", "Padam", "Picture", "Objects", 2),
        StarterWord("TA_WORD_0082", "இல்லை", "Illai", "No / not", "Safety", 2),
        StarterWord("TA_WORD_0083", "ஆம்", "Aam", "Yes", "Safety", 1),
        StarterWord("TA_WORD_0086", "தலை", "Thalai", "Head", "Body", 2),
        StarterWord("TA_WORD_0090", "பாதுகாப்பு", "Paadhukaappu", "Safety", "Safety", 3),
        StarterWord("TA_WORD_0096", "மீண்டும்", "Meendum", "Again", "Session", 3),
        StarterWord("TA_WORD_0098", "இங்கே", "Inge", "Here", "Session", 2),
        StarterWord("TA_WORD_0099", "அங்கே", "Ange", "There", "Session", 2),
        StarterWord("TA_WORD_0100", "சேர்ந்து", "Serndhu", "Together", "Session", 3),
        StarterWord("TA_WORD_0101", "என்ன", "Enna", "What", "Communication", 1),
        StarterWord("TA_WORD_0102", "நான்", "Naan", "I / me", "Communication", 1),
        StarterWord("TA_WORD_0103", "இது", "Ithu", "This", "Communication", 1),
        StarterWord("TA_WORD_0104", "எனக்கு", "Enakku", "For me / to me", "Needs", 2),
        StarterWord("TA_WORD_0084", "கை", "Kai", "Hand", "Body", 1),
        StarterWord("TA_WORD_0061", "வீடு", "Veedu", "Home", "Places", 2),
    )

    /** DEC-058: an itinerary only; these IDs never condition phoneme decoding. */
    val focusedLessonIds = listOf(1, 2, 13, 12, 6, 7, 4, 5, 8, 3, 11, 10, 20, 21, 22, 23, 24, 25)

    fun byNumericLessonId(id: Int): StarterWord? = all.getOrNull(id - 1)
}

/** MST-009: a development match may continue the demo but never records child correctness. */
fun nextStarterLessonId(currentId: Int, focused: Boolean = false): Int? {
    val itinerary = if (focused) StarterWords.focusedLessonIds else (1..StarterWords.all.size).toList()
    val index = itinerary.indexOf(currentId)
    return if (index < 0) null else itinerary.getOrNull(index + 1)
}

/** DEC-025: the avatar voice surface is a closed catalogue, never free-form dialogue. */
object LocalPromptLibrary {
    fun wordExample(target: String): String? = StarterWords.all.firstOrNull { it.tamil == target }?.tamil
    /** DEC-056: unverified system example; Aytham is read by name, never a fabricated phone. */
    fun letterExample(id: String): String? = TamilAlphabet.find(id)?.let {
        if (it.group == LetterGroup.AYTHAM) "ஆய்தம்" else it.symbol
    }
}

data class CarePlan(
    val childAlias: String = "Friend",
    val age: Int = 7,
    val sessionMinutes: Int = 10,
    val focusMinutes: Int = 4,
    val interest: String = "stories",
)

/** DEC-020: parent settings create pacing bounds, never attention or diagnosis labels. */
fun normalizeCarePlan(value: CarePlan): CarePlan {
    val session = value.sessionMinutes.coerceIn(5, 20)
    return value.copy(
        childAlias = value.childAlias.trim().take(30).ifBlank { "Friend" },
        age = value.age.coerceIn(7, 14),
        sessionMinutes = session,
        focusMinutes = value.focusMinutes.coerceIn(2, minOf(8, session - 1)),
        interest = value.interest.trim().take(40).ifBlank { "stories" },
    )
}

enum class CheckupState { THERAPIST_UNASSIGNED, SCHEDULE_UNESTABLISHED, SCHEDULED, DUE_SOON, OVERDUE }

data class CheckupStatus(val state: CheckupState, val dueEpochMillis: Long?)

/** CHK-001/003: derive the reminder only from known authoritative timestamps. */
fun checkupStatus(
    nowEpochMillis: Long,
    therapistAssigned: Boolean,
    assignmentEpochMillis: Long?,
    lastCompletedEpochMillis: Long?,
): CheckupStatus {
    if (!therapistAssigned) return CheckupStatus(CheckupState.THERAPIST_UNASSIGNED, null)
    val authority = listOfNotNull(assignmentEpochMillis, lastCompletedEpochMillis).maxOrNull()
        ?: return CheckupStatus(CheckupState.SCHEDULE_UNESTABLISHED, null)
    val day = 86_400_000L
    val due = authority + (14 * day)
    val state = when {
        nowEpochMillis > due -> CheckupState.OVERDUE
        due - nowEpochMillis <= 7 * day -> CheckupState.DUE_SOON
        else -> CheckupState.SCHEDULED
    }
    return CheckupStatus(state, due)
}

sealed interface SessionEvent {
    data class Attempt(val wordId: String, val reason: String) : SessionEvent
    data class PictureChoice(val wordId:String,val matched:Boolean,val withoutExtraHint:Boolean):SessionEvent
    data class PictureHelp(val wordId:String):SessionEvent
    data class ContextTurn(val wordId:String):SessionEvent
    data object Break : SessionEvent
}

data class LocalSessionReport(
    val sessionId: String,
    val startedAtEpochMillis: Long,
    val endedAtEpochMillis: Long,
    val durationSeconds: Long,
    val attemptCount: Int,
    val uniqueWordCount: Int,
    val breakCount: Int,
    val unscorableCount: Int,
    val accuracyPercent: Int? = null,
    val activityChoices:Int=0,
    val activityMatches:Int=0,
    val activityWithoutExtraHint:Int=0,
    val activityHelpRequests:Int=0,
    val activityContextTurns:Int=0,
)

/** ILR007/008: older unowned reports cannot be attributed to a different child. */
fun reportForProfile(report:LocalSessionReport?,owner:String?,current:String?):LocalSessionReport? =
    report.takeIf{owner!=null && owner.isNotBlank() && owner==current}

/** DEC-014/021: event-only summary; no raw audio, transcript, embedding or invented score. */
fun summarizeSession(
    sessionId: String,
    startedAtEpochMillis: Long,
    endedAtEpochMillis: Long,
    events: List<SessionEvent>,
): LocalSessionReport {
    val attempts = events.filterIsInstance<SessionEvent.Attempt>()
    return LocalSessionReport(
        sessionId = sessionId,
        startedAtEpochMillis = startedAtEpochMillis,
        endedAtEpochMillis = endedAtEpochMillis,
        durationSeconds = ((endedAtEpochMillis - startedAtEpochMillis).coerceAtLeast(0L) / 1_000L),
        attemptCount = attempts.size,
        uniqueWordCount = attempts.map { it.wordId }.distinct().size,
        breakCount = events.count { it is SessionEvent.Break },
        unscorableCount = attempts.size,
        activityChoices = events.filterIsInstance<SessionEvent.PictureChoice>().count{WordActivityCatalog.isMatch(it.wordId)},
        activityMatches = events.filterIsInstance<SessionEvent.PictureChoice>().count{WordActivityCatalog.isMatch(it.wordId) && it.matched},
        activityWithoutExtraHint = events.filterIsInstance<SessionEvent.PictureChoice>().count{WordActivityCatalog.isMatch(it.wordId) && it.matched && it.withoutExtraHint},
        activityHelpRequests = events.count{it is SessionEvent.PictureHelp},
        activityContextTurns = events.filterIsInstance<SessionEvent.ContextTurn>().count{e->StarterWords.all.any{it.id==e.wordId} && !WordActivityCatalog.isMatch(e.wordId)}.coerceAtMost(10000),
    )
}
