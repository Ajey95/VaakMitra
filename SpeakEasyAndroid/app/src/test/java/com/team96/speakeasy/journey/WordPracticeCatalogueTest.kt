package com.team96.speakeasy.journey

import com.team96.speakeasy.data.Lesson
import com.team96.speakeasy.viewmodel.AppViewModel
import org.junit.Assert.*
import org.junit.Test

/** DEC-052/055: a remote numeric ID must never relabel the installed word-model target. */
class WordPracticeCatalogueTest {
    @Test fun remoteLetterAndExtraWordCannotReplaceLocalPracticeTargets() {
        val vm=AppViewModel()
        vm.acceptRemoteLessons(listOf(
            Lesson(1,"letter","அ","A","a","remote letter",1),
            Lesson(26,"word","நான்","Naan","I","remote-only word",1),
        ))
        assertEquals("அ",vm.lessons.value.first().symbol)
        assertEquals("அம்மா",vm.lessonById(1)?.symbol)
        assertEquals("சேர்ந்து",vm.lessonById(19)?.symbol)
        assertEquals("என்ன",vm.lessonById(20)?.symbol) // DEC-058: stable local append, never remote relabelling.
        assertNull(vm.lessonById(26))
    }
}
