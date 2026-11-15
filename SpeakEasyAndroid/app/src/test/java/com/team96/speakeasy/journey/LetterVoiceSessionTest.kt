package com.team96.speakeasy.journey
import org.junit.Assert.*
import org.junit.Test

/** DEC-056: all closed letter targets can enter the shared session, never word classes. */
class LetterVoiceSessionTest {
    @Test fun all247ResolveToTheirOwnLetterAndClosedSystemExample() {
        TamilAlphabet.all.forEach { letter ->
            val lesson=letterVoiceLesson(letter.id)
            assertEquals("letter",lesson?.type)
            assertEquals(letter.symbol,lesson?.symbol)
            assertEquals(letter.romanization,lesson?.english)
            assertNotNull(LocalPromptLibrary.letterExample(letter.id))
        }
        assertNull(letterVoiceLesson("TA_WORD_0001"))
        assertNull(letterVoiceLesson("unknown"))
        assertNull(LocalPromptLibrary.letterExample("arbitrary text"))
    }
    @Test fun aythamExampleNamesTheLetterWithoutInventingAPhone() {
        assertEquals("ஆய்தம்",LocalPromptLibrary.letterExample("TA_LETTER_AYTHAM_01"))
        assertEquals("அ",LocalPromptLibrary.letterExample("TA_LETTER_UYIR_01"))
        assertEquals("கௌ",LocalPromptLibrary.letterExample("TA_LETTER_UYIRMEI_01_12"))
        assertEquals("அம்மா",LocalPromptLibrary.wordExample("அம்மா"))
    }
    @Test fun sharedSessionCrossesCategoriesInOrderAndReplayStaysLocal() {
        for(index in 0 until 246) {
            val current=TamilAlphabet.all[index]
            val progress=LetterProgress.restore(index+1)
            assertEquals(TamilAlphabet.all[index+1],nextLetterVoiceTarget(current.id,progress))
        }
        assertEquals(TamilAlphabet.all[1],nextLetterVoiceTarget(TamilAlphabet.all[0].id,LetterProgress.restore(30)))
        assertNull(nextLetterVoiceTarget(TamilAlphabet.all[0].id,LetterProgress.restore(0)))
        assertNull(nextLetterVoiceTarget(TamilAlphabet.all.last().id,LetterProgress.restore(247)))
        assertNull(nextLetterVoiceTarget("unknown",LetterProgress.restore(247)))
    }

}
