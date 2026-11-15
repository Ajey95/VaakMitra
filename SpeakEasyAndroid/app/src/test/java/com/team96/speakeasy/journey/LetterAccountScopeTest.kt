package com.team96.speakeasy.journey
import org.junit.Assert.*
import org.junit.Test
/** DEC053 review R6: missing authenticated identity must not fall back to a shared key. */
class LetterAccountScopeTest {
 @Test fun missingAccountHasNoScopeAndCannotClaimOfflineIdentity() {
  assertNull(verifiedLetterScope(null,"Friend",false));assertNull(verifiedLetterScope("  ","Friend",false))
  assertNull(verifiedLetterScope("Offline review","Friend",false))
  assertNotNull(verifiedLetterScope(null,"Friend",true))
 }
 @Test fun identifiedAccountAndExplicitOfflineModeStayIsolated() {
  assertNotEquals(verifiedLetterScope("a@example.com","Friend",false),verifiedLetterScope("b@example.com","Friend",false))
  assertNotEquals(verifiedLetterScope("a@example.com","Friend",false),verifiedLetterScope(null,"Friend",true))
  assertEquals(letterProfileScope("a@example.com","Friend"),verifiedLetterScope(" A@example.com ","Friend",false))
 }
}
