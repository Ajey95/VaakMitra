package com.team96.speakeasy.audio
import kotlinx.coroutines.*
import org.junit.Assert.*
import org.junit.Test
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicInteger
/** DEC-056 review R5: fake late native resource, no microphone/model or rendered frame. */
class AsyncResourceOwnerTest {
 private class Resource:AutoCloseable {val closes=AtomicInteger();override fun close(){closes.incrementAndGet()}}
 @Test fun cancelledFactoryClosesItsLateResourceExactlyOnce()=runBlocking {
  val owner=AsyncResourceOwner<Resource>();val entered=CountDownLatch(1);val release=CountDownLatch(1);val value=Resource()
  val job=launch {owner.load {entered.countDown();check(release.await(5,TimeUnit.SECONDS));value}}
  withContext(Dispatchers.IO){check(entered.await(5,TimeUnit.SECONDS))}
  job.cancel();release.countDown();job.join();owner.close()
  assertEquals(1,value.closes.get())
 }
 @Test fun disposedOwnerClosesFactoryResultEvenWithoutCoroutineCancellation()=runBlocking {
  val owner=AsyncResourceOwner<Resource>();val entered=CountDownLatch(1);val release=CountDownLatch(1);val value=Resource()
  val job=async {owner.load {entered.countDown();check(release.await(5,TimeUnit.SECONDS));value}}
  withContext(Dispatchers.IO){check(entered.await(5,TimeUnit.SECONDS))}
  owner.close();release.countDown();assertNull(job.await());assertEquals(1,value.closes.get())
 }
 @Test fun adoptedResourceClosesWithoutWaitingForAComposition()=runBlocking {
  val owner=AsyncResourceOwner<Resource>();val value=Resource()
  assertSame(value,owner.load {value});owner.close();owner.close();assertEquals(1,value.closes.get())
 }
}
