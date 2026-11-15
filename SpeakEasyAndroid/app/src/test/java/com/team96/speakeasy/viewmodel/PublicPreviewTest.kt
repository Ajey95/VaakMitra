package com.team96.speakeasy.viewmodel
import com.team96.speakeasy.journey.summarizeSession
import kotlinx.coroutines.runBlocking
import org.junit.Assert.*
import org.junit.Test
/** DEC057 review R1: a fake writer proves gallery actions cannot replace real session history. */
class PublicPreviewTest {
 @Test fun publicPreviewCannotWriteAReport()=runBlocking{
  var writes=0;val vm=AppViewModel(preview=true,reportWriter={writes++})
  assertFalse(vm.savePracticeReport(summarizeSession("PUBLIC",0,0,emptyList())))
  assertEquals(0,writes)
 }
 @Test fun productionWritesTheOriginalReportOnce()=runBlocking{
  val report=summarizeSession("PUBLIC",0,0,emptyList());var writes=0
  val vm=AppViewModel(reportWriter={assertSame(report,it);writes++},identityProvider={"a"},verifiedIdentityProvider={"a"})
  assertTrue(vm.savePracticeReport(report));assertEquals(1,writes)
 }
}
