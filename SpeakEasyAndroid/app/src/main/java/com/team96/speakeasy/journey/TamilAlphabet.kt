package com.team96.speakeasy.journey

/** DEC-052/016: traditional Tamil letters are learning items, not word-scoring targets. */
enum class LetterGroup(val tamil: String, val title: String, val description: String) {
    UYIR("உயிரெழுத்து", "Uyir", "12 vowels"),
    MEI("மெய்யெழுத்து", "Mei", "18 consonants"),
    AYTHAM("ஆய்த எழுத்து", "Aytham", "1 special letter"),
    UYIRMEI("உயிர்மெய் எழுத்து", "Uyirmei", "216 combinations · 18 families"),
}

data class TamilLetter(
    val id: String,
    val symbol: String,
    val romanization: String,
    val group: LetterGroup,
    val meiId: String? = null,
    val uyirId: String? = null,
)

object TamilAlphabet {
    private val vowels = listOf("அ", "ஆ", "இ", "ஈ", "உ", "ஊ", "எ", "ஏ", "ஐ", "ஒ", "ஓ", "ஔ")
    private val vowelReadings = listOf("a", "ā", "i", "ī", "u", "ū", "e", "ē", "ai", "o", "ō", "au")
    private val consonants = listOf("க", "ங", "ச", "ஞ", "ட", "ண", "த", "ந", "ப", "ம", "ய", "ர", "ல", "வ", "ழ", "ள", "ற", "ன")
    private val consonantReadings = listOf("k", "ṅ", "c", "ñ", "ṭ", "ṇ", "t", "n", "p", "m", "y", "r", "l", "v", "ḻ", "ḷ", "ṟ", "ṉ")
    private val vowelSigns = listOf("", "ா", "ி", "ீ", "ு", "ூ", "ெ", "ே", "ை", "ொ", "ோ", "ௌ")
    private fun number(index: Int) = (index + 1).toString().padStart(2, '0')
    private val uyir = vowels.mapIndexed { i, symbol ->
        TamilLetter("TA_LETTER_UYIR_${number(i)}", symbol, vowelReadings[i], LetterGroup.UYIR)
    }
    private val mei = consonants.mapIndexed { i, symbol ->
        TamilLetter("TA_LETTER_MEI_${number(i)}", symbol + "்", consonantReadings[i], LetterGroup.MEI)
    }
    private val compounds = consonants.flatMapIndexed { c, base ->
        vowels.indices.map { v ->
            TamilLetter(
                "TA_LETTER_UYIRMEI_${number(c)}_${number(v)}",
                base + vowelSigns[v], consonantReadings[c] + vowelReadings[v], LetterGroup.UYIRMEI,
                meiId = mei[c].id, uyirId = uyir[v].id,
            )
        }
    }
    val all: List<TamilLetter> = uyir + mei +
        listOf(TamilLetter("TA_LETTER_AYTHAM_01", "ஃ", "Aytham", LetterGroup.AYTHAM)) + compounds
    private val byId = all.associateBy { it.id }
    fun find(id: String): TamilLetter? = byId[id]
    fun inGroup(group: LetterGroup): List<TamilLetter> = all.filter { it.group == group }
    fun next(id: String): TamilLetter? = adjacent(id, 1)
    fun previous(id: String): TamilLetter? = adjacent(id, -1)
    private fun adjacent(id: String, step: Int): TamilLetter? {
        val current = find(id) ?: return null
        val siblings = inGroup(current.group)
        return siblings.getOrNull(siblings.indexOf(current) + step)
    }
}
