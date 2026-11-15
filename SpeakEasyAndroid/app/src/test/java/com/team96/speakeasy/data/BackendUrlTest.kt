package com.team96.speakeasy.data

import org.junit.Assert.assertEquals
import org.junit.Test

class BackendUrlTest {
    @Test fun debugMayUseLocalHttp() {
        assertEquals("http://10.0.2.2:8000/", BackendUrl.validate("http://10.0.2.2:8000", release = false))
    }

    @Test(expected = IllegalArgumentException::class)
    fun releaseRejectsHttp() {
        BackendUrl.validate("http://example.com", release = true)
    }
}
