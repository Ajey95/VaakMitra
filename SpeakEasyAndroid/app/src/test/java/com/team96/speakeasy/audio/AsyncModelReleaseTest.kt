package com.team96.speakeasy.audio

import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test

/** DEC068/PHN009: leaving a session must not wait for a large native inference lock. */
class AsyncModelReleaseTest {
    private class Resource:AutoCloseable {var closes=0;override fun close(){closes++}}
    @Test fun ownerInvalidatesImmediatelyWhileActualNativeCloseCanRunOffMain()=runBlocking {
        val queued=mutableListOf<()->Unit>()
        val owner=AsyncResourceOwner<Resource>{queued.add(it)}
        val first=Resource();assertSame(first,owner.load{first})
        owner.close();owner.close()
        assertEquals(0,first.closes);assertEquals(1,queued.size)
        queued.removeAt(0).invoke();assertEquals(1,first.closes)
        val late=Resource();assertNull(owner.load{late})
        assertEquals(0,late.closes);assertEquals(1,queued.size)
        queued.removeAt(0).invoke();assertEquals(1,late.closes)
    }
}
