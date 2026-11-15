package com.team96.speakeasy.audio

import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import java.util.concurrent.atomic.AtomicBoolean

/** AU-002/003: one microphone source provides mono 16-kHz PCM16 samples. */
interface PcmSource {
    fun start(): Boolean
    fun read(samples: ShortArray): Int
    fun stop()
    fun release()
}

internal class AndroidPcmSource : PcmSource {
    private var record: AudioRecord? = null

    override fun start(): Boolean {
        val minimum = AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT)
        if (minimum <= 0) return false
        val audio = AudioRecord.Builder()
            .setAudioSource(MediaRecorder.AudioSource.MIC)
            .setAudioFormat(AudioFormat.Builder()
                .setEncoding(AudioFormat.ENCODING_PCM_16BIT)
                .setSampleRate(16000)
                .setChannelMask(AudioFormat.CHANNEL_IN_MONO)
                .build())
            .setBufferSizeInBytes(maxOf(minimum, 4096))
            .build()
        if (audio.state != AudioRecord.STATE_INITIALIZED) {
            audio.release()
            return false
        }
        record = audio
        audio.startRecording()
        return audio.recordingState == AudioRecord.RECORDSTATE_RECORDING
    }

    override fun read(samples: ShortArray): Int = record?.read(samples, 0, samples.size, AudioRecord.READ_BLOCKING) ?: -1

    override fun stop() {
        record?.let { if (it.recordingState == AudioRecord.RECORDSTATE_RECORDING) it.stop() }
    }

    override fun release() {
        record?.release()
        record = null
    }
}

/** PRV-001: capture never leaves memory; stop/cancel release the microphone. */
class WordPcmRecorder(
    private val maxSamples: Int = 128000,
    private val sourceFactory: () -> PcmSource = { AndroidPcmSource() },
) {
    init { require(maxSamples in 1..128000) }
    private class Session(val source: PcmSource, maxSamples: Int) {
        val running = AtomicBoolean(true)
        val closed = AtomicBoolean(false)
        val buffer = BoundedPcmBuffer(maxSamples)
        var reader: Thread? = null

        fun close() {
            if (closed.compareAndSet(false, true)) {
                try { source.stop() } catch (_: Exception) { }
                try { source.release() } catch (_: Exception) { }
            }
        }
    }

    private val lock = Any()
    private var session: Session? = null

    fun start(): Boolean = synchronized(lock) {
        if (session != null) return false
        val source = try { sourceFactory() } catch (_: Exception) { return false }
        val started = try { source.start() } catch (_: Exception) { false }
        if (!started) {
            try { source.release() } catch (_: Exception) { }
            return false
        }
        val current = Session(source, maxSamples)
        session = current
        current.reader = Thread({
            val chunk = ShortArray(2048)
            try {
                while (current.running.get() && !current.buffer.isFull) {
                    val count = source.read(chunk)
                    if (count <= 0) break
                    current.buffer.append(chunk, count)
                }
            } catch (_: Exception) {
                // A stopped AudioRecord can end a blocking read with an error.
            } finally {
                chunk.fill(0)
                current.running.set(false)
                current.close()
            }
        }, "vaakmitra-word-pcm").also { it.isDaemon = true; it.start() }
        true
    }

    fun stop(): ShortArray = finish(dropAudio = false)

    fun cancel() { finish(dropAudio = true) }

    private fun finish(dropAudio: Boolean): ShortArray {
        val current = synchronized(lock) { session.also { session = null } } ?: return ShortArray(0)
        current.running.set(false)
        current.close()
        current.reader?.join(1000)
        if (dropAudio || current.reader?.isAlive == true) {
            current.buffer.clear()
            return ShortArray(0)
        }
        return current.buffer.takeAndClear()
    }
}
