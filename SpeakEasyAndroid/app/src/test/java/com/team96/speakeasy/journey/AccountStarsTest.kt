package com.team96.speakeasy.journey
import org.junit.Assert.*
import org.junit.Test
/** DEC057 review R5: remote absence cannot erase a learner's unknown earned state. */
class AccountStarsTest {
 @Test fun unavailableAndInvalidTotalsRemainUnknown(){assertNull(confirmedAccountStars(null));assertNull(confirmedAccountStars(-1))}
 @Test fun confirmedZeroAndPositiveTotalsRemainExact(){assertEquals(0,confirmedAccountStars(0));assertEquals(35,confirmedAccountStars(35))}
}
