package com.team96.speakeasy.audio

import android.Manifest
import android.app.AlertDialog
import android.content.Context
import android.content.pm.PackageManager
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.util.Log
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import androidx.test.core.app.ActivityScenario
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.LifecycleRegistry
import androidx.lifecycle.LifecycleEventObserver
import com.team96.speakeasy.MainActivity
import java.nio.FloatBuffer
import java.util.concurrent.CountDownLatch
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicBoolean
import java.util.concurrent.atomic.AtomicReference
import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Assume.assumeTrue
import org.junit.Test
import org.junit.runner.RunWith

/** DEC-067: test assets only; instrumentation arguments cannot supply arbitrary paths. */
private fun diagnosticAssets(choice: String?): Pair<String, String> = when (choice) {
    null, "historical-tempo" -> "phoneme-live-diagnostic" to "tempo-candidate.fp32.onnx"
    "clean-anchor" -> "phoneme-live-anchor" to "anchor-candidate.fp32.onnx"
    else -> throw IllegalArgumentException("Unknown diagnostic probe")
}

/** DEC-051/067: one foreground lifetime; resuming never rearms a cancelled trial. */
internal class LifecycleRecordingGate(
    private val lifecycle: Lifecycle, private val cancelRecorder: () -> Unit,
) : LifecycleEventObserver, AutoCloseable {
    private val lifetime=CaptureLifetime(cancelRecorder)
    init {
        lifecycle.addObserver(this)
        if (lifecycle.currentState != Lifecycle.State.RESUMED) cancel()
    }
    fun cancel()=lifetime.cancel()
    override fun onStateChanged(source: LifecycleOwner, event: Lifecycle.Event) {
        if (event in setOf(Lifecycle.Event.ON_PAUSE, Lifecycle.Event.ON_STOP, Lifecycle.Event.ON_DESTROY)) cancel()
    }
    fun start(action: () -> Boolean): Boolean = lifetime.start(action)
    fun publish(action: () -> Unit): Boolean =
        if(lifecycle.currentState!=Lifecycle.State.RESUMED)false else lifetime.publish(action)
    override fun close() { cancel(); lifecycle.removeObserver(this) }
}

/** DEC-051: operator-only diagnostic; never an unattended microphone test. */
@RunWith(AndroidJUnit4::class)
class PhonemeLiveDiagnosticTest {
    private fun distance(reference: IntArray, heard: IntArray): Int {
        var row = IntArray(heard.size + 1) { it }
        reference.forEachIndexed { i, expected ->
            val next = IntArray(heard.size + 1)
            next[0] = i + 1
            heard.forEachIndexed { j, actual ->
                next[j + 1] = minOf(next[j] + 1, row[j + 1] + 1, row[j] + if (expected == actual) 0 else 1)
            }
            row = next
        }
        return row.last()
    }

    private fun <T> withErasedPcm(samples: ShortArray, body: (ShortArray) -> T): T =
        try { body(samples) } finally { samples.fill(0) }

    private fun processedAccepted(reason: String): Boolean =
        reason == "PHONEME_TOKENS" || reason == "PHONEME_EMPTY"

    private fun processedDistance(reason: String, reference: IntArray, heard: IntArray): Int =
        if (processedAccepted(reason)) distance(reference, heard) else -1

    /** DEC-051: time and erasure never wait for screen progress. */
    private fun <T> diagnosticCapture(
        start: () -> Boolean, stop: () -> ShortArray, cancel: () -> Unit,
        isCancelled: () -> Boolean, now: () -> Long, pause: () -> Unit,
        post: (() -> Unit) -> Unit, status: (String) -> Unit, operation: (ShortArray) -> T,
    ): T {
        val active = AtomicBoolean(true)
        fun notify(message: String) { post { if (active.get() && !isCancelled()) status(message) } }
        try {
            assumeTrue("Operator cancelled", !isCancelled())
            check(start()) { "Microphone did not start" }
            val end = now() + 2500
            notify("Listening — say the displayed word once now.")
            while (now() < end && !isCancelled()) pause()
            assumeTrue("Operator cancelled", !isCancelled())
            return withErasedPcm(stop()) { samples ->
                assumeTrue("Operator cancelled", !isCancelled())
                notify("Comparing in memory. No audio files are saved.")
                val result = operation(samples)
                assumeTrue("Operator cancelled during comparison", !isCancelled())
                result
            }
        } finally { active.set(false); cancel() }
    }

    private data class Prompt(val id: String, val roman: String, val tamil: String)
    private data class Counts(
        val samples: Int,
        val referencePhones: Int,
        val oldRaw: Int,
        val oldPipeline: Int,
        val candidateRaw: Int,
        val candidatePipeline: Int,
        val pipelineReason: String,
        val activeSamples: Int,
    )

    /** DEC-051/067: unqualified probes live only in the test APK, never the main app. */
    private class DiagnosticComparisonModel(
        context: Context, vocabularySize: Int,
        choice: String? = InstrumentationRegistry.getArguments().getString("comparison_model"),
    ) : AutoCloseable {
        private val environment = OrtEnvironment.getEnvironment()
        private val options: OrtSession.SessionOptions
        private val session: OrtSession
        private val decoder = PhonemeDecoderConfig("ctc_prefix_beam", 5, 8)
        private val size = vocabularySize
        val assetRoot: String
        val modelSha256: String
        val baselineSha256: String
        init {
            val (root, modelFile) = diagnosticAssets(choice)
            assetRoot = root
            val testAssets = InstrumentationRegistry.getInstrumentation().context.assets
            val metadata = JSONObject(testAssets.open("$root/manifest.json").bufferedReader().use { it.readText() })
            require(!metadata.getBoolean("qualified_for_app") && !metadata.getBoolean("production_ready") && !metadata.getBoolean("approved_for_child_scoring"))
            val deployed = JSONObject(context.assets.open("${OnnxMobilePhoneme.ROOT}/bundle.json").bufferedReader().use { it.readText() })
            modelSha256 = metadata.getString("model_sha256")
            baselineSha256 = metadata.getString("baseline_model_sha256")
            require(deployed.getString("model_sha256") == baselineSha256)
            require(deployed.getString("vocabulary_sha256") == metadata.getString("vocabulary_sha256"))
            require(metadata.getString("model_file") == modelFile)
            val rawDecoder = metadata.getJSONObject("decoder")
            require(PhonemeCtcDecoder.parseDecoder(deployed.getString("bundle_version"), true,
                rawDecoder.keys().asSequence().associateWith { rawDecoder.get(it) }, size) == decoder)
            if (root == "phoneme-live-anchor") {
                require(PhonemeAudio.exactInteger(metadata.get("input_samples")) == 48000)
                require(PhonemeAudio.exactInteger(metadata.get("output_frames")) == 75)
                require(PhonemeAudio.exactInteger(metadata.get("tokens")) == size)
            }
            val bytes = testAssets.open("$root/$modelFile").use { it.readBytes() }
            try {
                PhonemeCtcDecoder.verifySha(bytes, modelSha256)
                val createdOptions = OrtSession.SessionOptions()
                var createdSession: OrtSession? = null
                try {
                    createdOptions.setIntraOpNumThreads(2)
                    createdOptions.setInterOpNumThreads(1)
                    createdOptions.addConfigEntry("session.intra_op.allow_spinning", "0")
                    createdSession = environment.createSession(bytes, createdOptions)
                    require(createdSession.inputNames == setOf("waveform") && createdSession.outputNames == setOf("logits"))
                    session = createdSession
                    options = createdOptions
                } catch (error: Exception) {
                    createdSession?.close()
                    createdOptions.close()
                    throw error
                }
            } finally { bytes.fill(0) }
        }
        fun inferIds(pcm: ShortArray): IntArray {
            val waveform = PhonemeAudio.prepare(pcm)
            try {
                OnnxTensor.createTensor(environment, FloatBuffer.wrap(waveform), longArrayOf(1, 48000)).use { input ->
                    session.run(mapOf("waveform" to input)).use { result ->
                        @Suppress("UNCHECKED_CAST")
                        val output = result[0].value as Array<Array<FloatArray>>
                        require(output.size == 1 && output[0].size == 75 && output[0].all { it.size == size })
                        return PhonemeCtcDecoder.decode(output[0], size, decoder)
                    }
                }
            } finally { waveform.fill(0f) }
        }
        override fun close() { session.close(); options.close() }
    }

    private fun compare(
        pcm: ShortArray, prompt: Prompt, reference: IntArray, lookup: Map<String, Int>,
        original: OnnxMobilePhoneme, candidate: DiagnosticComparisonModel,
        engine: MobileWordPracticeEngine, vad: OnnxSpeechVad,
    ): Counts {
        var oldRaw = intArrayOf()
        var newRaw = intArrayOf()
        var oldProcessed = intArrayOf()
        var newProcessed = intArrayOf()
        var speech = shortArrayOf()
        var active = shortArrayOf()
        var candidateAccepted = false
        try {
            require(pcm.isNotEmpty() && pcm.size <= PhonemeAudio.SAMPLES)
            oldRaw = original.inferIds(pcm)
            newRaw = candidate.inferIds(pcm)
            val outcome = engine.assess(prompt.id, pcm)
            require(outcome.decision == "UNSCORABLE")
            if (processedAccepted(outcome.reason)) {
                oldProcessed = outcome.predictedPhonemes.orEmpty().map { lookup[it] ?: error("Vocabulary mismatch") }.toIntArray()
            }
            // Both processed views share the actual engine's capture rejection gate.
            if (processedAccepted(outcome.reason)) {
                val evidence = vad.analyze(pcm)
                if (evidence.hasEnoughSpeech) {
                speech = evidence.extractSpeech(pcm)
                active = MobilePcmPreprocessor.trimActiveWord(speech)
                    if (active.isNotEmpty() && active.size <= PhonemeAudio.SAMPLES) {
                        newProcessed = candidate.inferIds(active)
                        candidateAccepted = true
                    }
                }
            }
            // These are disagreements with the canonical PROMPT, not verified
            // acoustic ground truth or a pronunciation correctness score.
            return Counts(
                pcm.size, reference.size, distance(reference, oldRaw),
                processedDistance(outcome.reason, reference, oldProcessed),
                distance(reference, newRaw),
                processedDistance(if (candidateAccepted) "PHONEME_TOKENS" else "VAD_NO_SPEECH", reference, newProcessed),
                outcome.reason,
                active.size,
            )
        } finally {
            oldRaw.fill(0); newRaw.fill(0); oldProcessed.fill(0); newProcessed.fill(0)
            speech.fill(0); active.fill(0)
        }
    }

    private fun operatorTrial(
        scenario: ActivityScenario<MainActivity>, prompt: Prompt, ordinal: Int,
        operation: (ShortArray) -> Counts, publish: (Counts) -> Unit,
    ) {
        val start = CountDownLatch(1)
        val cancelled = AtomicBoolean(false)
        val dialog = AtomicReference<AlertDialog>()
        val recorder = WordPcmRecorder(maxSamples = 40000)
        val main = Handler(Looper.getMainLooper())
        val foreground = AtomicReference<LifecycleRecordingGate>()
        fun cancelTrial() {
            cancelled.set(true)
            start.countDown()
            RecordingCleanup.dispatch{recorder.cancel()}
        }
        try {
            scenario.onActivity { activity ->
                val gate = LifecycleRecordingGate(activity.lifecycle, ::cancelTrial)
                foreground.set(gate)
                val window = AlertDialog.Builder(activity)
                    .setTitle("${prompt.tamil} / ${prompt.roman} — $ordinal/15")
                    .setMessage("Adult experimental-model comparison, not a score. Use a quiet room. Tap Record, wait for Listening, then say this word once naturally. Audio stays in memory only.")
                    .setPositiveButton("Record 2.5 seconds", null)
                    .setNegativeButton("Stop / cancel all") { _, _ ->
                        gate.cancel()
                    }.create()
                window.setCanceledOnTouchOutside(false)
                window.setOnCancelListener {
                    gate.cancel()
                }
                window.setOnShowListener {
                    window.getButton(AlertDialog.BUTTON_POSITIVE).setOnClickListener {
                        it.isEnabled = false
                        window.setMessage("Starting microphone…")
                        start.countDown()
                    }
                }
                dialog.set(window)
                window.show()
            }
            check(start.await(120, TimeUnit.SECONDS)) { "Waiting for operator timed out" }
            assumeTrue("Operator cancelled", !cancelled.get())
            val result = diagnosticCapture(
                start = { foreground.get()?.start { if (cancelled.get()) false else recorder.start() } == true },
                stop = { recorder.stop() }, cancel = { recorder.cancel() },
                isCancelled = { cancelled.get() }, now = { SystemClock.elapsedRealtime() },
                pause = { Thread.sleep(25) }, post = { callback -> main.post { callback() }; Unit },
                status = { message -> dialog.get()?.setMessage(message) }, operation = operation,
            )
            var published = false
            scenario.onActivity { published = foreground.get()?.publish { publish(result) } == true }
            assumeTrue("Operator cancelled before result publication", published)
        } finally {
            foreground.get()?.cancel()
            recorder.cancel()
            main.post { foreground.getAndSet(null)?.close(); dialog.getAndSet(null)?.dismiss() }
        }
    }

    @Test fun diagnosticCountsAndErasureSurviveAnInferenceFailure() {
        assertEquals(0, distance(intArrayOf(1, 2, 2, 3), intArrayOf(1, 2, 2, 3)))
        assertEquals(1, distance(intArrayOf(1, 2, 2, 3), intArrayOf(1, 2, 3)))
        assertEquals(2, distance(intArrayOf(1, 2), intArrayOf()))
        val pcm = shortArrayOf(100, -200, 300)
        val failure = runCatching {
            withErasedPcm<Int>(pcm) { throw IllegalStateException("controlled inference failure") }
        }.exceptionOrNull()
        assertTrue(failure is IllegalStateException)
        assertTrue("PCM must be erased even when inference throws", pcm.all { it == 0.toShort() })
    }

    @Test fun dec067DiagnosticProbeUsesClosedAssetChoices() {
        assertEquals("phoneme-live-diagnostic" to "tempo-candidate.fp32.onnx", diagnosticAssets(null))
        assertEquals("phoneme-live-anchor" to "anchor-candidate.fp32.onnx", diagnosticAssets("clean-anchor"))
        assertTrue(runCatching { diagnosticAssets("../../main") }.isFailure)
        assertTrue(runCatching { diagnosticAssets("unknown") }.isFailure)
    }

    @Test fun dec067AnchoredProbeMatchesFrozenDesktopPublicFixture() {
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val assets = instrumentation.context.assets
        val metadata = JSONObject(assets.open("phoneme-live-anchor/manifest.json").bufferedReader().use { it.readText() })
        val wav = assets.open("phoneme-fixtures/adult-test.wav").use { it.readBytes() }
        var pcm = shortArrayOf()
        try {
            PhonemeCtcDecoder.verifySha(wav, metadata.getString("fixture_sha256"))
            var offset = 12
            while (offset + 8 <= wav.size) {
                val length = (0..3).sumOf { (wav[offset + 4 + it].toInt() and 255) shl (8 * it) }
                require(length >= 0 && offset + 8L + length <= wav.size)
                if (String(wav, offset, 4, Charsets.US_ASCII) == "data") {
                    require(length % 2 == 0)
                    pcm = ShortArray(length / 2) { i ->
                        ((wav[offset + 8 + i * 2].toInt() and 255) or (wav[offset + 9 + i * 2].toInt() shl 8)).toShort()
                    }
                    break
                }
                offset += 8 + length + length % 2
            }
            require(pcm.isNotEmpty())
            val expected = metadata.getJSONArray("fixture_prediction")
            val wanted = IntArray(expected.length()) { expected.getInt(it) }
            DiagnosticComparisonModel(instrumentation.targetContext, 61, "clean-anchor").use { model ->
                val actual = model.inferIds(pcm)
                try { assertArrayEquals(wanted, actual) } finally { actual.fill(0) }
            }
            wanted.fill(0)
        } finally { pcm.fill(0); wav.fill(0) }
    }

    @Test fun dec051StalledUiDoesNotExtendCaptureOrRetainPcm() {
        var clock = 0L
        var stopped = false
        var cancelled = false
        val queued = mutableListOf<() -> Unit>()
        val pcm = shortArrayOf(1200, -1200)
        val result = diagnosticCapture(
            start = { true }, stop = { stopped = true; pcm }, cancel = { cancelled = true },
            isCancelled = { false }, now = { clock }, pause = { clock += 25 },
            post = { queued.add(it) }, status = { error("UI is stalled; must not be awaited") },
        ) { samples -> assertTrue(stopped); assertEquals(2500L, clock); samples.size }
        assertEquals(2, result)
        assertTrue(cancelled)
        assertTrue(pcm.all { it == 0.toShort() })
        queued.forEach { it() }
    }

    @Test fun dec067BackgroundCancelsFakeRecorderAndBlocksQueuedStartsAndPublication() {
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            class Owner : LifecycleOwner {
                val registry = LifecycleRegistry(this)
                override val lifecycle: Lifecycle get() = registry
            }
            for (startBeforePause in listOf(false, true)) {
                val owner = Owner()
                owner.registry.handleLifecycleEvent(Lifecycle.Event.ON_CREATE)
                owner.registry.handleLifecycleEvent(Lifecycle.Event.ON_START)
                owner.registry.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
                var starts = 0; var cancels = 0; var recording = false; var published = false
                val gate = LifecycleRecordingGate(owner.lifecycle) { cancels++; recording = false }
                if (startBeforePause) assertTrue(gate.start { starts++; recording = true; true })
                owner.registry.handleLifecycleEvent(Lifecycle.Event.ON_PAUSE)
                assertFalse(recording)
                assertEquals(1, cancels)
                assertFalse(gate.start { starts++; true })
                assertFalse(gate.publish { published = true })
                assertFalse(published)
                assertEquals(if (startBeforePause) 1 else 0, starts)
                owner.registry.handleLifecycleEvent(Lifecycle.Event.ON_RESUME)
                assertFalse("Cancelled trials never restart on resume", gate.start { starts++; true })
                gate.close()
            }
        }
    }

    @Test fun dec067CancellationDuringComparisonErasesPcmAndDiscardsResult() {
        var clock = 0L; var cancelled = false; var released = false
        val pcm = shortArrayOf(1200, -1200)
        val failure = runCatching {
            diagnosticCapture(
                start = { true }, stop = { pcm }, cancel = { released = true },
                isCancelled = { cancelled }, now = { clock }, pause = { clock += 25 },
                post = { it() }, status = {},
            ) { cancelled = true; "must not publish" }
        }.exceptionOrNull()
        assertTrue(failure is org.junit.AssumptionViolatedException)
        assertTrue(released)
        assertTrue(pcm.all { it == 0.toShort() })
    }

    @Test fun dec067RealActivityResumeAllowsFakeForegroundTrial() {
        val ready = CountDownLatch(1)
        val gate = AtomicReference<LifecycleRecordingGate>()
        var cancels = 0
        ActivityScenario.launch(MainActivity::class.java).use { scenario ->
            try {
                scenario.onActivity { activity ->
                    Log.i("VaakMitraLifecycleProbe", "initial=${activity.lifecycle.currentState}")
                    activity.lifecycle.addObserver(LifecycleEventObserver { _, event ->
                        Log.i("VaakMitraLifecycleProbe", "event=$event state=${activity.lifecycle.currentState}")
                        if (event == Lifecycle.Event.ON_RESUME) ready.countDown()
                    })
                    gate.set(LifecycleRecordingGate(activity.lifecycle) { cancels++ })
                    if (activity.lifecycle.currentState == Lifecycle.State.RESUMED) ready.countDown()
                }
                assertTrue("Real activity must become resumed", ready.await(10, TimeUnit.SECONDS))
                scenario.onActivity { activity ->
                    Log.i("VaakMitraLifecycleProbe", "ready=${activity.lifecycle.currentState} cancels=$cancels")
                    assertTrue("A resumed real activity must allow a fake recorder", gate.get().start { true })
                    assertTrue(gate.get().publish {})
                }
            } finally { scenario.onActivity { gate.getAndSet(null)?.close() } }
        }
    }

    @Test fun dec051RejectedCaptureAndValidEmptyHaveCommonSemantics() {
        assertEquals(-1, processedDistance("CLIPPED", intArrayOf(1, 2), intArrayOf()))
        assertEquals(-1, processedDistance("TOO_SHORT", intArrayOf(1, 2), intArrayOf()))
        assertEquals(2, processedDistance("PHONEME_EMPTY", intArrayOf(1, 2), intArrayOf()))
        assertEquals(2, processedDistance("PHONEME_TOKENS", intArrayOf(1, 2), intArrayOf()))
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        MobileWordPracticeEngine.create(context, enabled = true).use { engine ->
            val outcome = engine.assess("TA_WORD_0001", ShortArray(16000) { Short.MAX_VALUE })
            assertEquals("CLIPPED", outcome.reason)
            assertFalse(processedAccepted(outcome.reason))
        }
    }

    @Test fun operatorRunsMemoryOnlyPipelineComparison() {
        assumeTrue("Requires explicit adult operator opt-in", InstrumentationRegistry.getArguments().getString("operator_memory_opt_in") == "true")
        val instrumentation = InstrumentationRegistry.getInstrumentation()
        val context = instrumentation.targetContext
        check(context.checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) { "Grant microphone permission in the app first" }
        val bytes = context.assets.open("${OnnxMobilePhoneme.ROOT}/vocabulary.json").use { it.readBytes() }
        val vocabulary = try { JSONObject(String(bytes, Charsets.UTF_8)) } finally { bytes.fill(0) }
        val tokens = vocabulary.getJSONArray("tokens")
        val lookup = (0 until tokens.length()).associate { tokens.getString(it) to it }
        val prompts = listOf(
            Prompt("TA_WORD_0001", "Amma", "அம்மா"), Prompt("TA_WORD_0002", "Appa", "அப்பா"),
            Prompt("TA_WORD_0012", "Unavu", "உணவு"), Prompt("TA_WORD_0013", "Vendum", "வேண்டும்"),
            Prompt("TA_WORD_0100", "Serndhu", "சேர்ந்து"),
        )
        val bundle = AndroidMobileBundleLoader.load(context)
        try {
            ActivityScenario.launch(MainActivity::class.java).use { scenario ->
                OnnxMobilePhoneme(context).use { original ->
                    DiagnosticComparisonModel(context, tokens.length()).use { candidate ->
                        Log.i("VaakMitraLiveDiag", "begin probe=${candidate.assetRoot} modelSha256=${candidate.modelSha256} baselineSha256=${candidate.baselineSha256} qualifiedForApp=false")
                        OnnxSpeechVad(bundle.vadBytes, bundle.manifest.vad).use { vad ->
                            MobileWordPracticeEngine.create(context, enabled = true).use { engine ->
                                var ordinal = 0
                                for (prompt in prompts) repeat(3) {
                                    ordinal++
                                    val expected = vocabulary.getJSONObject("expected").getJSONArray(prompt.id)
                                    val reference = IntArray(expected.length()) { i -> checkNotNull(lookup[expected.getString(i)]) }
                                    operatorTrial(scenario, prompt, ordinal,
                                        operation = { pcm -> compare(pcm, prompt, reference, lookup, original, candidate, engine, vad) },
                                        publish = { result ->
                                            Log.i("VaakMitraLiveDiag", "trial=$ordinal prompt=${prompt.id} samples=${result.samples} activeSamples=${result.activeSamples} referencePhones=${result.referencePhones} oldRawEdits=${result.oldRaw} oldPipelineEdits=${result.oldPipeline} candidateRawEdits=${result.candidateRaw} candidatePipelineEdits=${result.candidatePipeline} reason=${result.pipelineReason} bufferErased=true")
                                            instrumentation.sendStatus(0, Bundle().apply { putString("stream", "\nMemory-only diagnostic $ordinal/15 completed\n") })
                                        })
                                }
                                Log.i("VaakMitraLiveDiag", "complete trials=15 noAudioFiles=true noPredictedLabelsLogged=true canonicalPromptOnly=true")
                            }
                        }
                    }
                }
            }
        } finally {
            bundle.modelBytes.fill(0); bundle.vadBytes.fill(0)
            bundle.references.values.forEach { it.fill(0f) }
        }
    }
}
