package com.team96.speakeasy.journey

import java.text.Normalizer
import org.junit.Assert.*
import org.junit.Test

/** DEC-052/016: independent expected traditional Tamil inventories, no scoring. */
class TamilAlphabetTest {
    @Test fun dec052All247AreUniqueNormalizedAndClosed() {
        assertEquals(247, TamilAlphabet.all.size)
        assertEquals(247, TamilAlphabet.all.map { it.symbol }.distinct().size)
        assertEquals(247, TamilAlphabet.all.map { it.id }.distinct().size)
        TamilAlphabet.all.forEach {
            assertTrue(it.id.matches(Regex("[A-Z0-9_]+")))
            assertTrue(Normalizer.isNormalized(it.symbol, Normalizer.Form.NFC))
            assertEquals(it, TamilAlphabet.find(it.id))
        }
        assertNull(TamilAlphabet.find("missing"))
        assertNull(TamilAlphabet.find("TA_WORD_0001"))
    }
    @Test fun dec052ExactVowelsConsonantsAndAytham() {
        assertEquals("அ ஆ இ ஈ உ ஊ எ ஏ ஐ ஒ ஓ ஔ".split(" "), TamilAlphabet.inGroup(LetterGroup.UYIR).map { it.symbol })
        assertEquals("க் ங் ச் ஞ் ட் ண் த் ந் ப் ம் ய் ர் ல் வ் ழ் ள் ற் ன்".split(" "), TamilAlphabet.inGroup(LetterGroup.MEI).map { it.symbol })
        assertEquals(listOf("ஃ"), TamilAlphabet.inGroup(LetterGroup.AYTHAM).map { it.symbol })
    }
    @Test fun dec052CompoundFamiliesHaveAllTwelveForms() {
        val compounds = TamilAlphabet.inGroup(LetterGroup.UYIRMEI)
        assertEquals(216, compounds.size)
        val mei = TamilAlphabet.inGroup(LetterGroup.MEI)
        mei.forEach { base ->
            val family = compounds.filter { it.meiId == base.id }
            assertEquals(12, family.size)
            assertEquals(TamilAlphabet.inGroup(LetterGroup.UYIR).map { it.id }, family.map { it.uyirId })
        }
        assertEquals("க கா கி கீ கு கூ கெ கே கை கொ கோ கௌ".split(" "), compounds.take(12).map { it.symbol })
        assertEquals("ன னா னி னீ னு னூ னெ னே னை னொ னோ னௌ".split(" "), compounds.takeLast(12).map { it.symbol })
        assertEquals("TA_LETTER_UYIR_01", TamilAlphabet.all.first().id)
        assertEquals("TA_LETTER_UYIRMEI_18_12", compounds.last().id)
    }
    @Test fun dec052NavigationNeverWrapsOrFallsBackToWord() {
        val vowels = TamilAlphabet.inGroup(LetterGroup.UYIR)
        assertNull(TamilAlphabet.previous(vowels.first().id))
        assertNull(TamilAlphabet.next(vowels.last().id))
        assertEquals(vowels[1], TamilAlphabet.next(vowels.first().id))
        assertNull(TamilAlphabet.next("bad"))
        assertEquals(25, StarterWords.all.size) // DEC-058 appends words without moving letter or old word routes.
        assertEquals("TA_WORD_0001", StarterWords.byNumericLessonId(1)?.id)
        assertEquals("TA_WORD_0100", StarterWords.byNumericLessonId(19)?.id)
        assertEquals("TA_WORD_0101", StarterWords.byNumericLessonId(20)?.id)
        assertNull(StarterWords.byNumericLessonId(26))
    }
}
