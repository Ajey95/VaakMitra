package com.team96.speakeasy.journey

import com.team96.speakeasy.data.Lesson

/** DEC-056: presentation metadata only; the letter ID never becomes a word-class ID. */
fun letterVoiceLesson(id: String): Lesson? = TamilAlphabet.find(id)?.let { letter ->
    Lesson(
        id = 0, type = "letter", symbol = letter.symbol, english = letter.romanization,
        phoneme = "Listen · Look · Trace · Speak",
        tip = "Listen if you wish, then practise at your pace. You can also look or trace. Tap Practice complete when ready.",
        difficulty = 1,
    )
}

/** DEC-053/056: use global level order, including category boundaries, and never skip a lock. */
fun nextLetterVoiceTarget(id: String, progress: LetterProgress): TamilLetter? {
    val index=TamilAlphabet.all.indexOfFirst{it.id==id}
    if(index<0 || !progress.isPractised(id))return null
    return TamilAlphabet.all.getOrNull(index+1)?.takeIf{progress.canOpen(it.id)}
}
